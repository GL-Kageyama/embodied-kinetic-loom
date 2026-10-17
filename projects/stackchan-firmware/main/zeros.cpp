#include "zeros.h"

#include "nvs.h"
#include "nvs_flash.h"

#include "board.h"

namespace {

constexpr const char* kNamespace = "servo";     // vendor: yaw_servo_config.settingNs
constexpr const char* kYawKey = "zero_pos_1";   // vendor: settingZeroPositionKey
constexpr const char* kPitchKey = "zero_pos_2";

}  // namespace

bool zeros::read(int* yaw_zero, int* pitch_zero, bool* from_nvs) {
  if (yaw_zero == nullptr || pitch_zero == nullptr || from_nvs == nullptr) {
    return false;
  }
  *yaw_zero = board::kYawZeroDefault;
  *pitch_zero = board::kPitchZeroDefault;
  *from_nvs = false;

  const esp_err_t init = nvs_flash_init();
  if (init != ESP_OK) {
    // ⛔ Do not erase. An unreadable NVS is reported, not repaired: the erase
    //    would destroy the measurement this firmware came to read.
    return false;
  }

  nvs_handle_t handle;
  if (nvs_open(kNamespace, NVS_READONLY, &handle) != ESP_OK) {
    return false;
  }

  int32_t yaw = 0;
  int32_t pitch = 0;
  const bool both = nvs_get_i32(handle, kYawKey, &yaw) == ESP_OK &&
                    nvs_get_i32(handle, kPitchKey, &pitch) == ESP_OK;
  nvs_close(handle);

  if (!both) {
    return false;
  }
  if (yaw < board::kRawMin || yaw > board::kRawMax ||
      pitch < board::kRawMin || pitch > board::kRawMax) {
    // ⚠️ The vendor refuses an out-of-range zero too. A stored value outside
    //    0..1000 cannot be a position this servo can hold.
    return false;
  }

  *yaw_zero = yaw;
  *pitch_zero = pitch;
  *from_nvs = true;
  return true;
}
