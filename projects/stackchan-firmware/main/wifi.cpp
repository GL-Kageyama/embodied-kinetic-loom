#include "wifi.h"

#include <cstdio>
#include <cstring>

#include "esp_event.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "nvs_flash.h"

namespace {

// ⚠️ Every address below is a value the driver owns. The only thing this file
//    does with them is print them — nothing is routed, and no line is read
//    back over the radio.
bool g_started = false;

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
    // ⚠️ One attempt, and no retry loop. A probe that retried would print a
    //    line every few seconds and bury the first reason, which is the one
    //    worth reading.
    esp_wifi_connect();
  } else if (id == WIFI_EVENT_STA_CONNECTED) {
    printf("wifi: associated — waiting for an address\n");
  } else if (id == WIFI_EVENT_STA_DISCONNECTED) {
    const auto* e = static_cast<const wifi_event_sta_disconnected_t*>(data);
    // ⛔ Only the number and the name. The frame that carried the reason can
    //    carry an SSID, and an SSID is not a secret but a neighbour's is.
    printf("wifi: not connected — reason %d (%s)\n", e->reason,
           ReasonName(e->reason));
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
