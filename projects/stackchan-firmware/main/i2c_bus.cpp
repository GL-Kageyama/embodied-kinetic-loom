#include "i2c_bus.h"

#include "board.h"

namespace {

i2c_master_bus_handle_t g_bus = nullptr;

}  // namespace

bool i2c_bus::begin() {
  if (g_bus != nullptr) {
    return true;
  }

  i2c_master_bus_config_t bus_cfg = {};
  bus_cfg.i2c_port = static_cast<i2c_port_num_t>(board::kI2cPort);
  bus_cfg.sda_io_num = static_cast<gpio_num_t>(board::kI2cSda);
  bus_cfg.scl_io_num = static_cast<gpio_num_t>(board::kI2cScl);
  bus_cfg.clk_source = I2C_CLK_SRC_DEFAULT;
  bus_cfg.glitch_ignore_cnt = 7;
  bus_cfg.flags.enable_internal_pullup = 1;

  return i2c_new_master_bus(&bus_cfg, &g_bus) == ESP_OK;
}

i2c_master_bus_handle_t i2c_bus::handle() {
  return g_bus;
}
