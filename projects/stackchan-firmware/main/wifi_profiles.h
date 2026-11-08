// The networks this body may join, in the order it tries them.
//
// ⛔ Why this file exists. Until 0.19.86 the board held exactly one network —
//    whatever `esp_wifi_set_config(WIFI_IF_STA, …)` stored — so `bench wifi join`
//    at a second location overwrote the first, and carrying the body between
//    two places meant retyping a password at each end. Measured on 2026-11-08:
//    the body was carried to a different network, the list did not exist, and
//    there was nothing to add it to.
//    ⇒ **A table of networks, tried in order, with one of them pinned by hand.**
//
// ⚠️ The table is pure: no IDF header, no NVS, no clock. `wifi.cpp` owns the
//    storage, and `tests/test_stackchan_wifi_profiles.py` compiles this file on
//    the host and asks it questions — the same split `wifi_retry` follows.
//
// ⛔ What this file does NOT decide: which network is up. The radio answers
//    that, and no table can.
#pragma once

#include <cstddef>
#include <cstdint>

namespace wifi_profiles {

//: How many networks the table holds. ⚠️ **Chosen, not measured** — a home, a
//: place of work, and one spare is what the drawer holds; the NVS blob grows by
//: 98 bytes per row and this board has room for far more than four.
constexpr uint8_t kMax = 4;

//: An SSID is at most 32 bytes and a PSK at most 63, which is the driver's own
//: limit (`wifi_config_t.sta.ssid` is 33 bytes and `.password` is 64 bytes, each
//: holding a NUL) and not this table's opinion. ⛔ The psk's 64th byte is why
//: this says 63: a 64-character psk used to be accepted at the console and
//: truncated when it reached the driver, silently. It is now refused.
constexpr std::size_t kSsidMax = 32;
constexpr std::size_t kPskMax = 63;

//: The blob's first byte. ⛔ A blob this file cannot read is an empty table and
//: never a half-read one — a row that came back wrong would be tried with a
//: password nobody typed.
constexpr uint8_t kVersion = 1;

//: ssid slot + psk slot, both NUL-padded to their whole width.
constexpr std::size_t kRowBytes = (kSsidMax + 1) + (kPskMax + 1);

//: version + count + every row.
constexpr std::size_t kEncodedMax = 2 + kMax * kRowBytes;

struct Profile {
  char ssid[kSsidMax + 1];
  //: ⛔ Empty is an open network, not an empty password. The two are different
  //: to the driver and printing one as the other would be wrong.
  char psk[kPskMax + 1];
};

struct Table {
  Profile rows[kMax];
  uint8_t count;
};

//: Why `add` did or did not change the table. The console prints one sentence
//: per outcome, so the distinction is carried as a value rather than a string.
enum class Add {
  kAdded,    //: a new row at the end
  kUpdated,  //: the ssid was already there; its psk was replaced in place
  kFull,     //: `kMax` rows and this is a new one
  kBadSsid,  //: null, empty, or longer than `kSsidMax`
  kBadPsk,   //: longer than `kPskMax`
};

//: An empty table. `count` is the only thing that says which rows are live.
void clear(Table& table);

//: Add or update. ⚠️ An update keeps the row's place, because the place is the
//: order the board tries them in and a re-typed password is not a new network.
Add add(Table& table, const char* ssid, const char* psk);

//: Remove by exact ssid. False when no row holds it.
bool remove(Table& table, const char* ssid);

//: Where the ssid sits, or −1.
int index_of(const Table& table, const char* ssid);

//: **Which row attempt `attempt` asks for.** Attempts are one-based, and the
//: episode begins at `start`. Every `tries` attempts the answer moves one row
//: on, wrapping — so a network that is not here is left behind in bounded time
//: and a network that is here is never abandoned for more than one round.
//:
//: ⚠️ `tries` is passed rather than fixed: the number belongs to the radio's
//: retry rule, and a table that baked it in would be two rules for one wait.
uint8_t index_for(uint8_t count, uint8_t start, uint32_t attempt, uint32_t tries);

//: The blob, ready for `nvs_set_blob`. Returns the number of bytes written, or
//: zero when the table cannot be written — too many rows, an invalid row, or a
//: buffer that is too small. ⛔ Zero is a refusal, never an empty table.
std::size_t encode(const Table& table, uint8_t* out, std::size_t capacity);

//: The blob, read back. False on any disagreement — a version this file does
//: not know, a count past `kMax`, a length that does not match the count, a
//: slot with no NUL in it. ⛔ The table is left untouched on failure.
bool decode(Table& table, const uint8_t* data, std::size_t length);

}  // namespace wifi_profiles
