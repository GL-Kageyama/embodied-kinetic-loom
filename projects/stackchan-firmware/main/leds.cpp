#include "leds.h"

#include "driver/i2c_master.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "board.h"

namespace {

i2c_master_bus_handle_t g_bus = nullptr;
i2c_master_dev_handle_t g_dev = nullptr;

// The expander's registers, as the vendor's driver names them.
constexpr unsigned char kRegVersion = 0x02;
constexpr unsigned char kRegGpioML = 0x03;
constexpr unsigned char kRegGpioMH = 0x04;
constexpr unsigned char kRegGpioOL = 0x05;
constexpr unsigned char kRegGpioOH = 0x06;
constexpr unsigned char kRegGpioPuL = 0x09;
constexpr unsigned char kRegGpioPuH = 0x0A;
constexpr unsigned char kRegGpioDrvL = 0x13;
constexpr unsigned char kRegGpioDrvH = 0x14;
constexpr unsigned char kRegLedCfg = 0x24;
constexpr unsigned char kRegLedRamStart = 0x30;

Light g_light = Light::kOff;
bool g_ready = false;

bool WriteRegister8(unsigned char reg, unsigned char value) {
  if (g_dev == nullptr) {
    return false;
  }
  const unsigned char buffer[2] = {reg, value};
  return i2c_master_transmit(g_dev, buffer, sizeof(buffer), 100) == ESP_OK;
}

bool ReadRegister8(unsigned char reg, unsigned char* out) {
  if (g_dev == nullptr || out == nullptr) {
    return false;
  }
  return i2c_master_transmit_receive(g_dev, &reg, 1, out, 1, 100) == ESP_OK;
}

bool WriteRegister(unsigned char reg, const unsigned char* data, int n) {
  if (g_dev == nullptr || data == nullptr || n <= 0) {
    return false;
  }
  unsigned char buffer[8];
  if (n + 1 > static_cast<int>(sizeof(buffer))) {
    return false;
  }
  buffer[0] = reg;
  for (int i = 0; i < n; ++i) {
    buffer[i + 1] = data[i];
  }
  return i2c_master_transmit(g_dev, buffer, n + 1, 100) == ESP_OK;
}

bool SetBit(unsigned char reg_low, unsigned char reg_high, int pin, bool on) {
  const unsigned char reg = pin < 8 ? reg_low : reg_high;
  const unsigned char mask = static_cast<unsigned char>(1u << (pin < 8 ? pin : pin - 8));
  unsigned char value = 0;
  if (!ReadRegister8(reg, &value)) {
    return false;
  }
  value = on ? static_cast<unsigned char>(value | mask)
             : static_cast<unsigned char>(value & ~mask);
  return WriteRegister8(reg, value);
}

bool SetDirection(int pin, bool output) {
  return SetBit(kRegGpioML, kRegGpioMH, pin, output);
}
bool SetPullUp(int pin, bool on) {
  return SetBit(kRegGpioPuL, kRegGpioPuH, pin, on);
}
bool SetPushPull(int pin) {
  return SetBit(kRegGpioDrvL, kRegGpioDrvH, pin, false);
}
bool SetPin(int pin, bool level) {
  return SetBit(kRegGpioOL, kRegGpioOH, pin, level);
}

bool SetLedCount(int count) {
  return WriteRegister8(kRegLedCfg, static_cast<unsigned char>(count & 0x3F));
}

bool SetLedColor(int index, unsigned char r, unsigned char g, unsigned char b) {
  if (index < 0 || index >= board::kLedCount) {
    return false;
  }
  // RGB565, little endian — the vendor's register layout.
  const unsigned short value =
      static_cast<unsigned short>(((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3));
  const unsigned char data[2] = {static_cast<unsigned char>(value & 0xFF),
                                 static_cast<unsigned char>((value >> 8) & 0xFF)};
  return WriteRegister(static_cast<unsigned char>(kRegLedRamStart + index * 2), data, 2);
}

bool RefreshLeds() {
  unsigned char cfg = 0;
  if (!ReadRegister8(kRegLedCfg, &cfg)) {
    return false;
  }
  return WriteRegister8(kRegLedCfg, static_cast<unsigned char>(cfg | (1u << 6)));
}

struct Rgb {
  unsigned char r;
  unsigned char g;
  unsigned char b;
};

// ⚠️ These are choices, not measurements. They are deliberately dim: twelve
//    pixels at full brightness in a dark room is a lamp, not a face.
Rgb ColorFor(Light light) {
  switch (light) {
    case Light::kOff:
      return {0, 0, 0};
    case Light::kDim:
      return {6, 6, 10};
    case Light::kBreathe:
      return {10, 12, 18};
    case Light::kWarm:
      return {28, 16, 6};
    case Light::kAlert:
      return {40, 26, 0};
    case Light::kError:
      return {36, 0, 0};
  }
  return {0, 0, 0};
}

// A triangle wave between 20% and 100% over three seconds.
int BreathScalePercent() {
  const int period_ms = 3000;
  const int phase = static_cast<int>((esp_timer_get_time() / 1000) % period_ms);
  const int triangle = phase < period_ms / 2
                           ? (phase * 200 / period_ms)
                           : ((period_ms - phase) * 200 / period_ms);
  return 20 + triangle * 80 / 100;
}

bool Render(Light light) {
  Rgb color = ColorFor(light);
  if (light == Light::kBreathe) {
    const int scale = BreathScalePercent();
    color.r = static_cast<unsigned char>(color.r * scale / 100);
    color.g = static_cast<unsigned char>(color.g * scale / 100);
    color.b = static_cast<unsigned char>(color.b * scale / 100);
  }
  bool ok = true;
  for (int i = 0; i < board::kLedCount; ++i) {
    ok = SetLedColor(i, color.r, color.g, color.b) && ok;
  }
  ok = RefreshLeds() && ok;
  return ok;
}

}  // namespace

bool leds::begin() {
  i2c_master_bus_config_t bus_cfg = {};
  bus_cfg.i2c_port = static_cast<i2c_port_num_t>(board::kI2cPort);
  bus_cfg.sda_io_num = static_cast<gpio_num_t>(board::kI2cSda);
  bus_cfg.scl_io_num = static_cast<gpio_num_t>(board::kI2cScl);
  bus_cfg.clk_source = I2C_CLK_SRC_DEFAULT;
  bus_cfg.glitch_ignore_cnt = 7;
  bus_cfg.flags.enable_internal_pullup = 1;

  if (i2c_new_master_bus(&bus_cfg, &g_bus) != ESP_OK) {
    return false;
  }

  i2c_device_config_t dev_cfg = {};
  dev_cfg.dev_addr_length = I2C_ADDR_BIT_LEN_7;
  dev_cfg.device_address = board::kExpanderAddress;
  dev_cfg.scl_speed_hz = 100000;

  if (i2c_master_bus_add_device(g_bus, &dev_cfg, &g_dev) != ESP_OK) {
    return false;
  }

  // ⚠️ The expander may boot slowly; the vendor waits up to 1.2 s for it.
  bool answered = false;
  for (int attempt = 0; attempt < 6; ++attempt) {
    vTaskDelay(pdMS_TO_TICKS(200));
    unsigned char version = 0;
    if (ReadRegister8(kRegVersion, &version) && version != 0 && version != 0xFF) {
      answered = true;
      break;
    }
  }
  if (!answered) {
    return false;
  }

  // Servo power: output, pull-up, then on.
  SetDirection(board::kServoPowerPin, true);
  SetPullUp(board::kServoPowerPin, true);
  servo_power(true);
  vTaskDelay(pdMS_TO_TICKS(200));

  // Twelve LEDs behind pin 13, push-pull.
  SetDirection(board::kLedDataPin, true);
  SetPullUp(board::kLedDataPin, true);
  SetPushPull(board::kLedDataPin);
  SetLedCount(board::kLedCount);
  vTaskDelay(pdMS_TO_TICKS(200));

  g_ready = true;
  g_light = Light::kOff;
  Render(g_light);
  return true;
}

void leds::set_light(Light light) {
  g_light = light;
  if (g_ready) {
    Render(g_light);
  }
}

void leds::tick() {
  if (g_ready && g_light == Light::kBreathe) {
    Render(g_light);
  }
}

bool leds::servo_power(bool on) {
  return SetPin(board::kServoPowerPin, on);
}
