#include "wifi_profiles.h"

#include <cstring>

namespace wifi_profiles {
namespace {

//: Copy `text` into a fixed slot and NUL-pad the rest. The caller has already
//: checked the length, so this truncates nothing — the padding is what makes a
//: row's bytes independent of what sat in the slot before.
void CopySlot(char* slot, std::size_t width, const char* text) {
  std::memset(slot, 0, width);
  if (text != nullptr && text[0] != 0) {
    std::memcpy(slot, text, std::strlen(text));
  }
}

//: The length of a slot's text, or `width` when the slot is not terminated.
//: ⚠️ A reader that used `strlen` on a blob would run past the row into the
//: next one, and a row is all a caller has any right to.
std::size_t SlotLength(const char* slot, std::size_t width) {
  const void* end = std::memchr(slot, 0, width);
  if (end == nullptr) {
    return width;
  }
  return static_cast<const char*>(end) - slot;
}

}  // namespace

void clear(Table& table) {
  std::memset(&table, 0, sizeof(table));
}

Add add(Table& table, const char* ssid, const char* psk) {
  if (ssid == nullptr || ssid[0] == 0 ||
      std::strlen(ssid) > kSsidMax) {
    return Add::kBadSsid;
  }
  const char* password = psk != nullptr ? psk : "";
  if (std::strlen(password) > kPskMax) {
    return Add::kBadPsk;
  }

  const int at = index_of(table, ssid);
  if (at >= 0) {
    CopySlot(table.rows[at].psk, sizeof(table.rows[at].psk), password);
    return Add::kUpdated;
  }
  if (table.count >= kMax) {
    return Add::kFull;
  }
  CopySlot(table.rows[table.count].ssid, sizeof(table.rows[table.count].ssid),
           ssid);
  CopySlot(table.rows[table.count].psk, sizeof(table.rows[table.count].psk),
           password);
  ++table.count;
  return Add::kAdded;
}

bool remove(Table& table, const char* ssid) {
  const int at = index_of(table, ssid);
  if (at < 0) {
    return false;
  }
  //: ⚠️ The rows after it move up, so the order the board tries them in is
  //: what a reader sees — and the vacated tail is zeroed rather than left to
  //: be read as a row by a later encode.
  for (uint8_t i = static_cast<uint8_t>(at); i + 1 < table.count; ++i) {
    table.rows[i] = table.rows[i + 1];
  }
  --table.count;
  std::memset(&table.rows[table.count], 0, sizeof(table.rows[table.count]));
  return true;
}

int index_of(const Table& table, const char* ssid) {
  if (ssid == nullptr) {
    return -1;
  }
  for (uint8_t i = 0; i < table.count; ++i) {
    if (std::strcmp(table.rows[i].ssid, ssid) == 0) {
      return static_cast<int>(i);
    }
  }
  return -1;
}

uint8_t index_for(uint8_t count, uint8_t start, uint32_t attempt,
                  uint32_t tries) {
  if (count == 0) {
    return 0;
  }
  if (start >= count) {
    start = 0;
  }
  if (tries == 0 || attempt == 0) {
    return start;
  }
  //: ⚠️ One-based: attempt 1 is the first try on `start`, and the first move
  //: happens at `tries + 1`, not at `tries`.
  const uint32_t moves = (attempt - 1) / tries;
  return static_cast<uint8_t>((start + moves) % count);
}

std::size_t encode(const Table& table, uint8_t* out, std::size_t capacity) {
  if (out == nullptr || table.count > kMax) {
    return 0;
  }
  const std::size_t needed =
      2 + static_cast<std::size_t>(table.count) * kRowBytes;
  if (capacity < needed) {
    return 0;
  }

  out[0] = kVersion;
  out[1] = table.count;
  std::size_t at = 2;
  for (uint8_t i = 0; i < table.count; ++i) {
    const Profile& row = table.rows[i];
    const std::size_t ssid_length = SlotLength(row.ssid, sizeof(row.ssid));
    const std::size_t psk_length = SlotLength(row.psk, sizeof(row.psk));
    //: ⛔ A row that could not be read back is not written out. Saving a table
    //: with a broken row would put a network in the list that no reboot can
    //: use and no line names.
    if (ssid_length == 0 || ssid_length > kSsidMax ||
        psk_length > kPskMax) {
      return 0;
    }
    std::memset(out + at, 0, kRowBytes);
    std::memcpy(out + at, row.ssid, ssid_length);
    std::memcpy(out + at + kSsidMax + 1, row.psk, psk_length);
    at += kRowBytes;
  }
  return needed;
}

bool decode(Table& table, const uint8_t* data, std::size_t length) {
  if (data == nullptr || length < 2) {
    return false;
  }
  if (data[0] != kVersion) {
    return false;
  }
  const uint8_t count = data[1];
  if (count > kMax) {
    return false;
  }
  const std::size_t needed =
      2 + static_cast<std::size_t>(count) * kRowBytes;
  //: ⚠️ An exact match, both ways: a truncated blob and a blob with a tail are
  //: both a shape this file did not write.
  if (length != needed) {
    return false;
  }

  Table read;
  clear(read);
  std::size_t at = 2;
  for (uint8_t i = 0; i < count; ++i) {
    const char* ssid = reinterpret_cast<const char*>(data + at);
    const char* psk =
        reinterpret_cast<const char*>(data + at + kSsidMax + 1);
    const std::size_t ssid_length = SlotLength(ssid, kSsidMax + 1);
    const std::size_t psk_length = SlotLength(psk, kPskMax + 1);
    if (ssid_length == 0 || ssid_length > kSsidMax ||
        psk_length > kPskMax) {
      return false;
    }
    std::memcpy(read.rows[i].ssid, ssid, ssid_length);
    std::memcpy(read.rows[i].psk, psk, psk_length);
    at += kRowBytes;
  }
  read.count = count;
  table = read;
  return true;
}

}  // namespace wifi_profiles
