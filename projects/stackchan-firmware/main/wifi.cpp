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
#include "wifi_profiles.h"
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

//: ⛔ **2026-11-08、この体は1つの網しか持てなかった。** `esp_wifi_set_config` は
//:    ひとつの設定しか保たないので、別の場所で `bench wifi join` すれば前の
//:    網は消えた。**持ち運ぶたびに、両端でパスワードを打ち直すことになる。**
//:    ⇒ **表を持つ。順に試し、手で選んだ一つを先に置く。**
//:    ⚠️ 表そのものは `wifi_profiles` にあり、IDF のヘッダを持たない。
//:    ここが持つのは保存と、無線に渡す順番だけである。
wifi_profiles::Table g_profiles;
SemaphoreHandle_t g_profiles_lock = nullptr;
volatile uint8_t g_profile_count = 0;
//: The row the radio is on (or was last handed). Written by `ApplyProfile`,
//: read by the retry task and `report()`.
volatile uint8_t g_index = 0;
//: Bumped whenever the console changes which row is wanted. The retry task
//: reads it at the start of an episode and starts over when it moved — a
//: `bench wifi join` typed mid-wait must not be undone by the wait it interrupted.
volatile uint32_t g_epoch = 0;

//: How many attempts one row gets before the next row is tried.
//: ⚠️ **Chosen, not measured.** With two networks and the retry ladder's own
//: 2 / 4 / 8 / … ms, the second network is reached 6 s after the first attempt
//: fails — fast enough that a body carried into another room is on the network
//: before its owner has put it down, slow enough that a network which is merely
//: out of range for a moment is not abandoned at once.
constexpr uint32_t kProfileTries = 2;

//: Where the table lives in NVS. ⛔ A namespace of this repository's own: the
//: vendor's wizard writes the driver's single config, and that blob is not
//: ours to reinterpret.
constexpr char kProfilesNamespace[] = "ekl_wifi";
constexpr char kProfilesKey[] = "profiles";

// The SSID the driver is holding, if any. Kept because `report()` has to answer
// with a name, and `esp_wifi_get_config` copies it out each time anyway.
void CopySsid(char* out, size_t size, const wifi_config_t& conf) {
  size_t i = 0;
  for (; i + 1 < size && conf.sta.ssid[i] != 0; ++i) {
    out[i] = static_cast<char>(conf.sta.ssid[i]);
  }
  out[i] = 0;
}

// The psk the driver is holding, copied with the same rule. ⚠️ Bounded by the
// destination rather than by `strlen`: a stored field without a NUL is the one
// shape that would run past the end of the driver's own array.
void CopyPsk(char* out, size_t size, const wifi_config_t& conf) {
  size_t i = 0;
  for (; i + 1 < size && conf.sta.password[i] != 0; ++i) {
    out[i] = static_cast<char>(conf.sta.password[i]);
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

// ---------------------------------------------------------------------------
// The table of networks.
// ---------------------------------------------------------------------------

//: Reads the blob. False when there is none, or when it cannot be read — and
//: ⚠️ `unreadable` tells the two apart, because a board that silently started
//: empty when a row was corrupt would look exactly like a board that never had
//: one, and the next boot would overwrite whatever was there.
bool LoadProfiles(bool* unreadable) {
  *unreadable = false;
  nvs_handle_t handle;
  if (nvs_open(kProfilesNamespace, NVS_READONLY, &handle) != ESP_OK) {
    return false;
  }
  uint8_t buffer[wifi_profiles::kEncodedMax];
  size_t length = sizeof(buffer);
  const esp_err_t got = nvs_get_blob(handle, kProfilesKey, buffer, &length);
  nvs_close(handle);
  if (got != ESP_OK) {
    return false;
  }
  wifi_profiles::Table loaded;
  if (!wifi_profiles::decode(loaded, buffer, length)) {
    *unreadable = true;
    return false;
  }
  g_profiles = loaded;
  g_profile_count = loaded.count;
  return true;
}

//: Writes the blob. ⚠️ The caller holds `g_profiles_lock`, so RAM and NVS move
//: together: a row added to one and not the other would be a network this boot
//: uses and the next one does not.
bool SaveProfilesLocked() {
  uint8_t buffer[wifi_profiles::kEncodedMax];
  const size_t length =
      wifi_profiles::encode(g_profiles, buffer, sizeof(buffer));
  if (length == 0) {
    return false;
  }
  nvs_handle_t handle;
  if (nvs_open(kProfilesNamespace, NVS_READWRITE, &handle) != ESP_OK) {
    return false;
  }
  bool ok = nvs_set_blob(handle, kProfilesKey, buffer, length) == ESP_OK;
  if (ok) {
    ok = nvs_commit(handle) == ESP_OK;
  }
  nvs_close(handle);
  if (ok) {
    g_profile_count = g_profiles.count;
  }
  return ok;
}

//: A copy of the table, for printers and for handing one row to the driver.
bool SnapshotLocked(wifi_profiles::Table* out) {
  if (g_profiles_lock == nullptr) {
    return false;
  }
  if (xSemaphoreTake(g_profiles_lock, pdMS_TO_TICKS(100)) != pdTRUE) {
    return false;
  }
  *out = g_profiles;
  xSemaphoreGive(g_profiles_lock);
  return true;
}

//: One row and the count, copied under the lock. ⚠️ **One row, not the table**:
//: the retry task's stack is 4 KB, and copying the whole table on it overflowed
//: at the old 3,072 on 2026-11-08 — measured, with a panic naming `wifi_retry`,
//: not imagined. A row is 97 bytes; a table is 390.
bool RowAt(uint8_t index, wifi_profiles::Profile* out, uint8_t* count) {
  if (g_profiles_lock == nullptr) {
    return false;
  }
  if (xSemaphoreTake(g_profiles_lock, pdMS_TO_TICKS(100)) != pdTRUE) {
    return false;
  }
  const bool ok = index < g_profiles.count;
  if (ok) {
    *out = g_profiles.rows[index];
  }
  if (count != nullptr) {
    *count = g_profiles.count;
  }
  xSemaphoreGive(g_profiles_lock);
  return ok;
}

//: Hands one row to the driver. ⛔ The psk is never printed here, in any form.
bool ApplyProfile(uint8_t index, bool announce) {
  wifi_profiles::Profile profile;
  std::memset(&profile, 0, sizeof(profile));
  uint8_t count = 0;
  if (!RowAt(index, &profile, &count)) {
    return false;
  }

  wifi_config_t conf;
  std::memset(&conf, 0, sizeof(conf));
  std::strncpy(reinterpret_cast<char*>(conf.sta.ssid), profile.ssid,
               sizeof(conf.sta.ssid) - 1);
  if (profile.psk[0] != 0) {
    std::strncpy(reinterpret_cast<char*>(conf.sta.password), profile.psk,
                 sizeof(conf.sta.password) - 1);
    conf.sta.threshold.authmode = WIFI_AUTH_WPA2_PSK;
  } else {
    conf.sta.threshold.authmode = WIFI_AUTH_OPEN;
  }
  if (esp_wifi_set_config(WIFI_IF_STA, &conf) != ESP_OK) {
    printf("wifi: profile %u was refused by the driver\n",
           static_cast<unsigned>(index + 1));
    return false;
  }
  g_index = index;
  if (announce) {
    printf("wifi: trying \"%s\" (%u of %u)\n", profile.ssid,
           static_cast<unsigned>(index + 1),
           static_cast<unsigned>(g_profile_count));
  }
  return true;
}

//: Adds or updates a row and saves it, printing the reason when it cannot.
//: Answers whether the table changed. ⚠️ Called from the console only, so the
//: lines it prints sit beside what the person typed.
bool RememberProfile(const char* ssid, const char* psk) {
  if (g_profiles_lock == nullptr) {
    printf("wifi: no profile lock — nothing can be stored\n");
    return false;
  }
  if (xSemaphoreTake(g_profiles_lock, pdMS_TO_TICKS(200)) != pdTRUE) {
    printf("wifi: the profile list is busy — nothing was stored\n");
    return false;
  }
  const wifi_profiles::Table before = g_profiles;
  const wifi_profiles::Add result = wifi_profiles::add(g_profiles, ssid, psk);
  bool ok = false;
  switch (result) {
    case wifi_profiles::Add::kBadSsid:
      printf("wifi: an ssid is required, and at most 32 characters\n");
      break;
    case wifi_profiles::Add::kBadPsk:
      printf("wifi: the psk is longer than 63 characters\n");
      break;
    case wifi_profiles::Add::kFull:
      printf("wifi: the list holds %u networks already — `bench wifi forget <ssid>` first\n",
             static_cast<unsigned>(wifi_profiles::kMax));
      break;
    case wifi_profiles::Add::kAdded:
    case wifi_profiles::Add::kUpdated:
      if (SaveProfilesLocked()) {
        ok = true;
        printf("wifi: %s \"%s\" (%u of %u)\n",
               result == wifi_profiles::Add::kAdded ? "added" : "updated", ssid,
               static_cast<unsigned>(g_profiles.count),
               static_cast<unsigned>(wifi_profiles::kMax));
      } else {
        //: ⛔ A row this boot can use and the next one cannot is worse than a
        //: refusal: it would look like the network was remembered.
        g_profiles = before;
        g_profile_count = before.count;
        printf("wifi: the list could not be saved — nothing changed\n");
      }
      break;
  }
  xSemaphoreGive(g_profiles_lock);
  return ok;
}

//: Removes a row and saves the rest.
bool ForgetProfile(const char* ssid) {
  if (g_profiles_lock == nullptr || ssid == nullptr) {
    return false;
  }
  if (xSemaphoreTake(g_profiles_lock, pdMS_TO_TICKS(200)) != pdTRUE) {
    printf("wifi: the profile list is busy — nothing was removed\n");
    return false;
  }
  const wifi_profiles::Table before = g_profiles;
  bool ok = false;
  if (!wifi_profiles::remove(g_profiles, ssid)) {
    printf("wifi: no profile holds \"%s\"\n", ssid);
  } else if (SaveProfilesLocked()) {
    ok = true;
    //: ⚠️ The row after the removed one takes its place, so the index that
    //: pointed at or past it moves back with the row.
    if (g_index >= g_profiles.count) {
      g_index = g_profiles.count == 0 ? 0 : g_profiles.count - 1;
    }
    //: The console changed which network is wanted; a retry episode already in
    //: its wait starts over rather than rotating off this change.
    g_epoch = g_epoch + 1;
    printf("wifi: forgot \"%s\" (%u left)\n", ssid,
           static_cast<unsigned>(g_profiles.count));
  } else {
    g_profiles = before;
    g_profile_count = before.count;
    printf("wifi: the list could not be saved — nothing changed\n");
  }
  xSemaphoreGive(g_profiles_lock);
  return ok;
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
    //: ⚠️ The row the episode begins on. `index_for` counts moves from here,
    //: so the episode keeps its own starting point even while `g_index` moves.
    const uint8_t start = g_index;
    const uint32_t epoch = g_epoch;
    uint32_t waited = wifi_retry::kMinMs;
    uint32_t attempt = 0;
    while (!g_have_ip) {
      for (uint32_t slept = 0; slept < waited && !g_have_ip; slept += kSliceMs) {
        vTaskDelay(pdMS_TO_TICKS(kSliceMs));
      }
      if (g_have_ip) {
        break;
      }
      if (g_epoch != epoch) {
        //: ⛔ The console pinned another network while this episode waited.
        //: Continuing would rotate away from the network the person just chose.
        break;
      }
      ++attempt;
      // ⚠️ Not `++`: `g_retries` is volatile so the task and `report()` see the
      //    same number, and the compiler warns on a volatile increment.
      g_retries = g_retries + 1;
      //: ⛔ **The wait keeps its ladder; only the row moves.** An earlier draft
      //: rotated on every attempt and reset the wait with the row, which would
      //: have retried every two seconds forever off-network — the busy loop
      //: `wifi_retry` exists to avoid.
      const uint8_t wanted = wifi_profiles::index_for(
          g_profile_count, start, attempt, kProfileTries);
      if (g_profile_count > 1 && wanted != g_index) {
        ApplyProfile(wanted, true);
      }
      if (wifi_retry::worth_printing(attempt)) {
        wifi_profiles::Profile shown;
        std::memset(&shown, 0, sizeof(shown));
        if (RowAt(g_index, &shown, nullptr)) {
          printf("wifi: asking again — attempt %u, waited %u ms, on \"%s\"\n",
                 static_cast<unsigned>(attempt), static_cast<unsigned>(waited),
                 shown.ssid);
        } else {
          printf("wifi: asking again — attempt %u, waited %u ms\n",
                 static_cast<unsigned>(attempt), static_cast<unsigned>(waited));
        }
      }
      esp_wifi_connect();
      waited = wifi_retry::next(waited);
    }
    //: ⚠️ Only when the wait ended in an address. An episode cut short by the
    //: console did not associate, and saying it did would be a false line.
    if (attempt > 0 && g_have_ip) {
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
  // ⚠️ **4,096 since 2026-11-08, and the number is part measurement and part
  //    margin.** The task overflowed at 3,072 the first time the profile table
  //    was copied on its stack (measured: a panic naming `wifi_retry`). The
  //    retry path now copies one row rather than the table, and 4,096 is the
  //    console's own size — chosen after that panic, not measured to be exact.
  } else if (xTaskCreate(&RetryTask, "wifi_retry", 4096, nullptr, 4, nullptr) !=
             pdPASS) {
    printf("wifi: the retry task did not start — a drop will not be retried\n");
  }

  esp_wifi_set_mode(WIFI_MODE_STA);
  // ⚠️ Anything `ApplyProfile` writes goes to NVS, so it survives the reset
  //    that this board keeps needing. It is the vendor's own storage setting.
  esp_wifi_set_storage(WIFI_STORAGE_FLASH);

  // ⛔ The table's lock is made before anything can read the table — the retry
  //    task is created above this, and a lock created after it would have a
  //    window in which the task reads a table no one owns.
  g_profiles_lock = xSemaphoreCreateMutex();
  if (g_profiles_lock == nullptr) {
    printf("wifi: no profile lock — the list cannot be read or stored\n");
  }

  // ⚠️ The list is seeded from the driver's own stored config on the first
  //    boot after this version: the network the vendor's wizard and `join`
  //    wrote is what the board was already joining, and asking for its
  //    password again to put it in a table would be asking for nothing.
  bool unreadable = false;
  const bool loaded = LoadProfiles(&unreadable);
  if (unreadable) {
    printf("wifi: the stored profile list did not read — starting from the driver's one\n");
  }
  if (!loaded && g_profile_count == 0) {
    wifi_config_t conf;
    std::memset(&conf, 0, sizeof(conf));
    if (esp_wifi_get_config(WIFI_IF_STA, &conf) == ESP_OK &&
        conf.sta.ssid[0] != 0) {
      char ssid[33] = {0};
      char psk[wifi_profiles::kPskMax + 1] = {0};
      CopySsid(ssid, sizeof(ssid), conf);
      CopyPsk(psk, sizeof(psk), conf);
      if (RememberProfile(ssid, psk)) {
        printf("wifi: the driver's one network is now profile 1\n");
      }
    }
  }

  if (g_profile_count == 0) {
    printf("wifi: nvs holds no ssid — `bench wifi add <ssid> <psk>`\n");
  } else {
    wifi_profiles::Table snapshot;
    if (SnapshotLocked(&snapshot) && snapshot.count > 0) {
      if (snapshot.count == 1) {
        printf("wifi: nvs holds \"%s\" — connecting\n", snapshot.rows[0].ssid);
      } else {
        printf("wifi: nvs holds %u profiles — trying \"%s\" first\n",
               static_cast<unsigned>(snapshot.count), snapshot.rows[0].ssid);
      }
      //: ⚠️ The first row is applied by name, not left to whatever the driver
      //: happens to hold: the driver's config is the *last* row applied, and a
      //: boot that began on a different row at different places would make the
      //: order in the table mean nothing.
      ApplyProfile(0, snapshot.count > 1);
    }
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

  if (g_profile_count == 0) {
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

void wifi_probe::add(const char* ssid, const char* psk) {
  if (!g_started) {
    printf("wifi: the radio is not up\n");
    return;
  }
  if (!RememberProfile(ssid, psk)) {
    return;
  }
  // ⚠️ Storing is not switching, said out loud: the person who typed this may
  //    mean "remember this place for next time", not "leave the network I am
  //    on now". `join` is the verb that moves.
  printf("wifi: not connected — `bench wifi join <ssid>` to switch now\n");
}

void wifi_probe::forget(const char* ssid) {
  if (!g_started) {
    printf("wifi: the radio is not up\n");
    return;
  }
  ForgetProfile(ssid);
}

void wifi_probe::join(const char* ssid, const char* psk) {
  if (!g_started) {
    printf("wifi: the radio is not up\n");
    return;
  }
  if (!RememberProfile(ssid, psk)) {
    return;
  }

  uint8_t index = 0;
  {
    wifi_profiles::Table snapshot;
    if (!SnapshotLocked(&snapshot)) {
      printf("wifi: the profile list did not read\n");
      return;
    }
    const int at = wifi_profiles::index_of(snapshot, ssid);
    if (at < 0) {
      printf("wifi: \"%s\" is not in the list\n", ssid);
      return;
    }
    index = static_cast<uint8_t>(at);
  }

  //: ⛔ The pin, before the connect: the retry task reads `g_epoch` when it
  //: starts an episode, and a change made here must end the episode it
  //: interrupts rather than be rotated away by it.
  g_epoch = g_epoch + 1;
  if (!ApplyProfile(index, true)) {
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

  // ⚠️ The list, without one psk in it. `*` is the row the radio is on, which
  //    is not necessarily the row it is associated with — a failing row stays
  //    the current one until the retry rule moves it.
  wifi_profiles::Table snapshot;
  if (SnapshotLocked(&snapshot)) {
    printf("wifi: list %u of %u — `*` is the row the radio is on\n",
           static_cast<unsigned>(snapshot.count),
           static_cast<unsigned>(wifi_profiles::kMax));
    for (uint8_t i = 0; i < snapshot.count; ++i) {
      printf("wifi:   %s\"%s\"\n", i == g_index ? "* " : "  ",
             snapshot.rows[i].ssid);
    }
  } else {
    printf("wifi: the list did not read\n");
  }
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
