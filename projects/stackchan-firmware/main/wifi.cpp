#include "wifi.h"

#include <cstdio>
#include <cstring>

#include "esp_event.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "nvs_flash.h"
#include "wifi_retry.h"

namespace {

// ⚠️ Every address below is a value the driver owns. The only thing this file
//    does with them is print them — nothing is routed, and no line is read
//    back over the radio.
bool g_started = false;

// ⛔ **2026-10-21、切れた接続は切れたままでいた。** このファイルは
//    `WIFI_EVENT_STA_START` で一度だけ `esp_wifi_connect()` を呼び、以後
//    `WIFI_EVENT_STA_DISCONNECTED` は理由を印刷して返っていた。その日、板は
//    電源が入って `bench pos` に答え、画面は暗く、`not associated, no ip` のまま
//    12 分そこにいた——dial は 18 回、接続は 0。
//    ⇒ **切れた状態は、この体が留まってよい状態ではない。**
//
// ⚠️ The retry waits, and the wait is `wifi_retry`'s rule, not a number here.
//    The wake is a binary semaphore given by the disconnect handler; the task
//    sleeps in slices so that an association that lands early ends the wait
//    instead of sitting out the whole backoff.
SemaphoreHandle_t g_dropped = nullptr;
volatile bool g_have_ip = false;
volatile uint32_t g_retries = 0;   // attempts since boot
volatile int g_last_reason = 0;    // the reason the last drop carried

//: The granularity at which the wait can be cut short. ⚠️ Chosen, not measured:
//: small enough that an association is noticed within a blink of the delay it
//: incurred, large enough that the loop is not a scheduler exercise.
constexpr uint32_t kSliceMs = 250;

// The SSID the driver is holding, if any. Kept because `report()` has to answer
// with a name, and `esp_wifi_get_config` copies it out each time anyway.
void CopySsid(char* out, size_t size, const wifi_config_t& conf) {
  size_t i = 0;
  for (; i + 1 < size && conf.sta.ssid[i] != 0; ++i) {
    out[i] = static_cast<char>(conf.sta.ssid[i]);
  }
  out[i] = 0;
}

// ⚠️ The reason is printed as a number *and* a word, because the number is what
//    the measurement holds and the word is what a reader can use. Only the ones
//    this unit has reason to expect are named; anything else is the bare code.
const char* ReasonName(int reason) {
  switch (reason) {
    case WIFI_REASON_NO_AP_FOUND: return "no ap found";
    case WIFI_REASON_AUTH_FAIL: return "auth fail";
    case WIFI_REASON_ASSOC_FAIL: return "assoc fail";
    case WIFI_REASON_HANDSHAKE_TIMEOUT: return "handshake timeout";
    case WIFI_REASON_4WAY_HANDSHAKE_TIMEOUT: return "4-way handshake timeout";
    case WIFI_REASON_CONNECTION_FAIL: return "connection fail";
    case WIFI_REASON_BEACON_TIMEOUT: return "beacon timeout";
    case WIFI_REASON_AUTH_EXPIRE: return "auth expire";
    default: return "unnamed";
  }
}

void OnWifi(void*, esp_event_base_t base, int32_t id, void* data) {
  if (base != WIFI_EVENT) {
    return;
  }
  if (id == WIFI_EVENT_STA_START) {
    esp_wifi_connect();
  } else if (id == WIFI_EVENT_STA_CONNECTED) {
    printf("wifi: associated — waiting for an address\n");
  } else if (id == WIFI_EVENT_STA_DISCONNECTED) {
    const auto* e = static_cast<const wifi_event_sta_disconnected_t*>(data);
    // ⛔ Only the number and the name. The frame that carried the reason can
    //    carry an SSID, and an SSID is not a secret but a neighbour's is.
    // ⚠️ A disconnect is also what `bench wifi join` causes, on purpose. The
    //    line is printed either way, because a line that only appears for
    //    unintended drops cannot be read to tell the two apart.
    printf("wifi: not connected — reason %d (%s)\n", e->reason,
           ReasonName(e->reason));
    // ⛔ This line is the fix of 2026-10-21. The reason is printed here, the
    //    retry happens there — so the first reason is the first thing on the
    //    console and stays there, and the retries ration their own lines.
    g_have_ip = false;
    g_last_reason = e->reason;
    if (g_dropped != nullptr) {
      xSemaphoreGive(g_dropped);
    }
  }
}

// The one thing this body does about a drop.
void RetryTask(void*) {
  for (;;) {
    if (xSemaphoreTake(g_dropped, portMAX_DELAY) != pdTRUE) {
      continue;
    }
    uint32_t waited = wifi_retry::kMinMs;
    uint32_t attempt = 0;
    while (!g_have_ip) {
      for (uint32_t slept = 0; slept < waited && !g_have_ip; slept += kSliceMs) {
        vTaskDelay(pdMS_TO_TICKS(kSliceMs));
      }
      if (g_have_ip) {
        break;
      }
      ++attempt;
      // ⚠️ Not `++`: `g_retries` is volatile so the task and `report()` see the
      //    same number, and the compiler warns on a volatile increment.
      g_retries = g_retries + 1;
      if (wifi_retry::worth_printing(attempt)) {
        printf("wifi: asking again — attempt %u, waited %u ms\n",
               static_cast<unsigned>(attempt), static_cast<unsigned>(waited));
      }
      esp_wifi_connect();
      waited = wifi_retry::next(waited);
    }
    if (attempt > 0) {
      printf("wifi: associated after %u attempt(s)\n",
             static_cast<unsigned>(attempt));
    }
  }
}

void OnGotIp(void*, esp_event_base_t, int32_t, void* data) {
  // ⛔ The address is read out of the event, not asked for. The first version
  //    called `esp_netif_get_ip_info` here, and that is an IPC round trip into
  //    the tcpip task — deep enough to overflow this handler's stack, which is
  //    `CONFIG_ESP_SYSTEM_EVENT_TASK_STACK_SIZE` = 2304 by default. Measured
  //    2026-10-21: every boot panicked about a second after this line was
  //    printed, and the coredump named `vApplicationStackOverflowHook` with
  //    `esp_netif_lwip_ipc_call_get_netif` interrupted — the event loop task's
  //    own stack, not the heap it had already smeared.
  // ⚠️ The event carries the interface and its addresses. Nothing has to be
  //    fetched, and a handler that fetches pays for a second task's frame.
  const auto* got = static_cast<const ip_event_got_ip_t*>(data);
  if (got == nullptr) {
    printf("wifi: got an address, but the event carried none\n");
    return;
  }
  // ⚠️ Set before the line, so the retry task stops waiting on the fact and
  //    not on the printing — a console that blocks must not hold a retry open.
  g_have_ip = true;
  char address[16] = {0};
  esp_ip4addr_ntoa(&got->ip_info.ip, address, sizeof(address));
  printf("wifi: connected ip=%s\n", address);
}

}  // namespace

void wifi_probe::begin() {
  // ⚠️ The same house rule `zeros.cpp` follows: init, and never erase. A blob
  //    that cannot be read is a board with no credentials, not a board to wipe
  //    — the vendor's setup wizard writes here too.
  const esp_err_t nvs = nvs_flash_init();
  if (nvs != ESP_OK && nvs != ESP_ERR_NVS_NO_FREE_PAGES) {
    printf("wifi: nvs init failed (%d) — no radio\n", static_cast<int>(nvs));
    return;
  }

  if (esp_netif_init() != ESP_OK || esp_event_loop_create_default() != ESP_OK) {
    printf("wifi: the netif or the event loop did not come up — no radio\n");
    return;
  }

  esp_netif_t* netif = esp_netif_create_default_wifi_sta();
  if (netif != nullptr) {
    // ⚠️ A name on the network so that, if this ever does answer on it, the
    //    board can be found without an IP scan.
    esp_netif_set_hostname(netif, "stackchan");
  }

  const wifi_init_config_t config = WIFI_INIT_CONFIG_DEFAULT();
  if (esp_wifi_init(&config) != ESP_OK) {
    printf("wifi: the driver did not initialise — no radio\n");
    return;
  }

  esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &OnWifi, nullptr);
  esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &OnGotIp, nullptr);

  // ⚠️ The semaphore and the task exist before `esp_wifi_start()`, because the
  //    first disconnect can follow the start within a second and a handler
  //    that finds `g_dropped` null would drop a wake on the floor.
  g_dropped = xSemaphoreCreateBinary();
  if (g_dropped == nullptr) {
    printf("wifi: no retry task — a drop will not be retried\n");
  } else if (xTaskCreate(&RetryTask, "wifi_retry", 3072, nullptr, 4, nullptr) !=
             pdPASS) {
    printf("wifi: the retry task did not start — a drop will not be retried\n");
  }

  esp_wifi_set_mode(WIFI_MODE_STA);
  // ⚠️ Anything `join` writes goes to NVS, so it survives the reset that this
  //    board keeps needing. It is the vendor's own storage setting.
  esp_wifi_set_storage(WIFI_STORAGE_FLASH);

  wifi_config_t conf;
  std::memset(&conf, 0, sizeof(conf));
  const bool stored =
      esp_wifi_get_config(WIFI_IF_STA, &conf) == ESP_OK && conf.sta.ssid[0] != 0;
  if (stored) {
    char ssid[33] = {0};
    CopySsid(ssid, sizeof(ssid), conf);
    printf("wifi: nvs holds \"%s\" — connecting\n", ssid);
  } else {
    printf("wifi: nvs holds no ssid — `bench wifi join <ssid> <psk>`\n");
  }

  if (esp_wifi_start() != ESP_OK) {
    printf("wifi: the driver did not start — no radio\n");
    return;
  }
  g_started = true;

  //: ⛔ **2026-10-21、省電力を切る。** かつて既定のままにして、こう書いた——
  //: 「12 ping で 12、切っても 12、どちらも 0 answered」。⚠️ **それは「届くか」の
  //: 測定であり、「速さ」ではなかった。** 同じ日、音を流すと基板は **約13 KB/s**
  //: しか読めず（512 バイトに 36 ms、`dial: link read`）、24 kHz・16ビットの
  //: 48 KB/s に届かなかった。⇒ **眠る無線は、届いても遅い。** ここで切って測る。
  //: ⚠️ 電池で動く日には、これは電力と引き換えの数になる。
  esp_wifi_set_ps(WIFI_PS_NONE);
  printf("wifi: power save off (WIFI_PS_NONE)\n" );

  if (!stored) {
    // ⛔ Nothing to connect to. The radio is up and can scan, and the boot
    //    banner says so rather than waiting for a timeout that will not come.
    printf("wifi: up, unconfigured\n");
  }
}

void wifi_probe::scan() {
  if (!g_started) {
    printf("wifi: the radio is not up\n");
    return;
  }
  // ⚠️ A scan blocks the caller for seconds. That is the same contract the
  //    other bench verbs have — the console stops until the machine answers.
  const esp_err_t started = esp_wifi_scan_start(nullptr, true);
  if (started != ESP_OK) {
    printf("wifi: scan did not start (%d)\n", static_cast<int>(started));
    return;
  }

  constexpr uint16_t kMax = 20;
  static wifi_ap_record_t records[kMax];
  uint16_t count = kMax;
  if (esp_wifi_scan_get_ap_records(&count, records) != ESP_OK) {
    printf("wifi: scan finished but the records did not read back\n");
    return;
  }

  printf("wifi: %u access point(s)\n", static_cast<unsigned>(count));
  for (uint16_t i = 0; i < count; ++i) {
    // ⛔ The BSSID is not printed: it names a neighbour's hardware, and it is
    //    not what this probe is asking.
    printf("wifi:   \"%s\" ch %u rssi %d auth %d\n",
           reinterpret_cast<const char*>(records[i].ssid),
           static_cast<unsigned>(records[i].primary), records[i].rssi,
           static_cast<int>(records[i].authmode));
  }
  if (count == 0) {
    printf("wifi: none — the antenna is not hearing anything\n");
  }
}

void wifi_probe::join(const char* ssid, const char* psk) {
  if (!g_started) {
    printf("wifi: the radio is not up\n");
    return;
  }
  if (ssid == nullptr || ssid[0] == 0) {
    printf("wifi: an ssid is required\n");
    return;
  }
  if (std::strlen(ssid) > 32) {
    printf("wifi: the ssid is longer than 32 characters\n");
    return;
  }
  if (psk != nullptr && std::strlen(psk) > 64) {
    printf("wifi: the psk is longer than 64 characters\n");
    return;
  }

  wifi_config_t conf;
  std::memset(&conf, 0, sizeof(conf));
  std::strncpy(reinterpret_cast<char*>(conf.sta.ssid), ssid,
               sizeof(conf.sta.ssid) - 1);
  if (psk != nullptr && psk[0] != 0) {
    std::strncpy(reinterpret_cast<char*>(conf.sta.password), psk,
                 sizeof(conf.sta.password) - 1);
    conf.sta.threshold.authmode = WIFI_AUTH_WPA2_PSK;
  } else {
    // ⚠️ No psk means an open network, and not an empty password. The two are
    //    different to the driver and printing one as the other would be wrong.
    conf.sta.threshold.authmode = WIFI_AUTH_OPEN;
  }

  if (esp_wifi_set_config(WIFI_IF_STA, &conf) != ESP_OK) {
    printf("wifi: the configuration was refused\n");
    return;
  }
  // ⛔ The psk is not echoed, in any length, in any form.
  printf("wifi: joining \"%s\"%s\n", ssid,
         psk != nullptr && psk[0] != 0 ? " with a psk (not printed)" : " (open)");
  esp_wifi_disconnect();
  esp_wifi_connect();
}

void wifi_probe::set_address(const char* spec) {
  if (!g_started) {
    printf("wifi: the radio is not up\n");
    return;
  }
  esp_netif_t* netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
  if (netif == nullptr) {
    printf("wifi: the interface is not there\n");
    return;
  }

  char ip[16] = {0};
  char mask[16] = {0};
  char gateway[16] = {0};
  if (spec == nullptr ||
      std::sscanf(spec, "%15s %15s %15s", ip, mask, gateway) != 3) {
    printf("wifi: addr needs <ip> <mask> <gateway>\n");
    return;
  }

  // ⚠️ Parsed by the stack's own reader. A hand-rolled dotted quad would accept
  //    `999.1.1.1` and set an address that is not what was typed.
  esp_ip4_addr_t address;
  esp_ip4_addr_t netmask;
  esp_ip4_addr_t router;
  if (esp_netif_str_to_ip4(ip, &address) != ESP_OK ||
      esp_netif_str_to_ip4(mask, &netmask) != ESP_OK ||
      esp_netif_str_to_ip4(gateway, &router) != ESP_OK) {
    printf("wifi: one of those was not an address\n");
    return;
  }

  // ⛔ The DHCP client is stopped first. Without that it re-applies the lease
  //    under this address within a second and the measurement measures nothing.
  esp_netif_dhcpc_stop(netif);

  esp_netif_ip_info_t info;
  std::memset(&info, 0, sizeof(info));
  info.ip = address;
  info.netmask = netmask;
  info.gw = router;
  const esp_err_t set = esp_netif_set_ip_info(netif, &info);
  if (set != ESP_OK) {
    printf("wifi: the address was refused (%d)\n", static_cast<int>(set));
    return;
  }
  // ⚠️ Nothing goes to NVS: a reboot returns this board to what the network
  //    hands it, which is what makes this a probe and not a configuration.
  printf("wifi: address %s/%s gw %s, for this boot only\n", ip, mask, gateway);
}

void wifi_probe::report() {
  if (!g_started) {
    printf("wifi: the radio is not up\n");
    return;
  }

  wifi_config_t conf;
  std::memset(&conf, 0, sizeof(conf));
  const bool stored =
      esp_wifi_get_config(WIFI_IF_STA, &conf) == ESP_OK && conf.sta.ssid[0] != 0;
  char ssid[33] = {0};
  if (stored) {
    CopySsid(ssid, sizeof(ssid), conf);
  }

  // ⚠️ Association and an address are two different facts. A station can be
  //    associated and have no address, and that is the state worth seeing.
  wifi_ap_record_t ap;
  std::memset(&ap, 0, sizeof(ap));
  const bool associated = esp_wifi_sta_get_ap_info(&ap) == ESP_OK;

  esp_netif_t* netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
  esp_netif_ip_info_t info;
  std::memset(&info, 0, sizeof(info));
  const bool has_ip = netif != nullptr &&
                      esp_netif_get_ip_info(netif, &info) == ESP_OK &&
                      info.ip.addr != 0;

  char address[16] = {0};
  if (has_ip) {
    esp_ip4addr_ntoa(&info.ip, address, sizeof(address));
  }

  printf("wifi: credentials \"%s\", %s, %s\n", stored ? ssid : "none",
         associated ? "associated" : "not associated", has_ip ? address : "no ip");
  if (associated) {
    printf("wifi:   ch %u rssi %d\n", static_cast<unsigned>(ap.primary), ap.rssi);
  }
  // ⛔ Zero here is not "the radio is healthy" — it is "nothing has dropped
  //    since boot". A board that was off the network for a day and never
  //    retried also reads zero, which is why the count is only worth reading
  //    beside the association above.
  if (g_retries != 0) {
    printf("wifi:   %u retr%s since boot, last drop reason %d (%s)\n",
           static_cast<unsigned>(g_retries),
           g_retries == 1 ? "y" : "ies", g_last_reason,
           ReasonName(g_last_reason));
  }

  // ⚠️ The margin, in bytes, of the task that runs every handler here. The
  //    overflow of 2026-10-21 happened with 2304 and was found by a coredump,
  //    not by this line — so this line is the one that would have said it first.
  // ⛔ A task that has not run since the last boot reports its whole stack, and
  //    that number means "not measured yet", not "plenty left".
  TaskHandle_t event_task = xTaskGetHandle("sys_evt");
  if (event_task != nullptr) {
    printf("wifi:   sys_evt stack, %u bytes never used\n",
           static_cast<unsigned>(uxTaskGetStackHighWaterMark(event_task)));
  }
}

bool wifi_probe::routed() {
  // ⚠️ **Associated is not routed.** A station can hold the AP and have no
  //    address yet — `wifi: associated — waiting for an address` is exactly the
  //    window the boot dial lands in, and in it `connect` returns
  //    `ENETUNREACH` in 0 ms against *every* address. An empty list of
  //    attempted addresses cannot tell a missing host from a missing route.
  esp_netif_t* netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
  if (netif == nullptr) {
    return false;
  }
  esp_netif_ip_info_t info;
  std::memset(&info, 0, sizeof(info));
  return esp_netif_get_ip_info(netif, &info) == ESP_OK && info.ip.addr != 0;
}
