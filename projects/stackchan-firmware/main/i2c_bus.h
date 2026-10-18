// The one I2C bus on this board: GPIO 12 (SDA) and GPIO 11 (SCL).
//
// ⚠️ Three devices answer on it, and each was named by the vendor before this
//    repository touched it:
//      - the servo board's PY32 expander, 0x6F (the servo rail and the LEDs);
//      - the AW9523, 0x58, behind the display's reset line;
//      - the AXP2101, 0x34, which holds the display's backlight rail.
// ⛔ One bus, one owner. A second `i2c_new_master_bus` on the same pins is not a
//    second bus — it is two drivers on one wire.
#pragma once

#include "driver/i2c_master.h"

namespace i2c_bus {

// Idempotent: the first call creates the bus, every later call is a no-op.
bool begin();

// Null until `begin()` has succeeded.
i2c_master_bus_handle_t handle();

}  // namespace i2c_bus
