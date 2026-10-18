#include "leds.h"

#include <cstdio>

#include "driver/i2c_master.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"

#include "board.h"

namespace {

i2c_master_bus_handle_t g_bus = nullptr;
i2c_master_dev_handle_t g_dev = nullptr;

// ⛔ One expander, now reached from two tasks: `set_light` from the console task
//    (a frame arrived) and `tick` from the main loop (a breath). An interleaved
//    write is not a refused light — it is a different light.
SemaphoreHandle_t g_lock = nullptr;

struct Guard {
  Guard() {
    if (g_lock != nullptr) {
      xSemaphoreTake(g_lock, portMAX_DELAY);
    }
  }
  ~Guard() {
    if (g_lock != nullptr) {
      xSemaphoreGive(g_lock);
    }
  }
};

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
//
// ⚠️ Multiplied by four on 2026-10-18. The first values were written before any
//    LED on this unit had been looked at, and the first frame a host ever sent
//    produced 「無点灯」 in a lit room — at r=28/255 a warm light is below what
//    daylight shows. The ratio between the words is unchanged; only the scale.
Rgb ColorFor(Light light) {
  switch (light) {
    case Light::kOff:
      return {0, 0, 0};
    case Light::kDim:
      return {24, 24, 40};
    case Light::kBreathe:
      return {40, 48, 72};
    case Light::kWarm:
      return {112, 64, 24};
    case Light::kAlert:
      return {160, 104, 0};
    case Light::kError:
      return {144, 0, 0};
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
  if (g_lock == nullptr) {
    g_lock = xSemaphoreCreateMutex();
    if (g_lock == nullptr) {
      return false;
    }
  }

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
  Guard guard;
  g_light = light;
  if (g_ready) {
    Render(g_light);
  }
}

void leds::tick() {
  Guard guard;
  if (g_ready && g_light == Light::kBreathe) {
    Render(g_light);
  }
}

bool leds::servo_power(bool on) {
  Guard guard;
  return SetPin(board::kServoPowerPin, on);
}

// ⚠️ Written on 2026-10-18, after a frame that the board accepted produced
//    nothing the author could see. Two things had been one word until then:
//    "the expander holds this colour" and "a pixel shows it". They are asked
//    separately here, and the answer is printed either way.
void leds::probe() {
  Guard guard;

  unsigned char version = 0;
  unsigned char cfg = 0;
  const bool has_version = ReadRegister8(kRegVersion, &version);
  const bool has_cfg = ReadRegister8(kRegLedCfg, &cfg);
  printf("leds: ready=%d version=%s0x%02X cfg=%s0x%02X\n", g_ready ? 1 : 0,
         has_version ? "" : "unreadable ",
         has_version ? version : 0, has_cfg ? "" : "unreadable ",
         has_cfg ? cfg : 0);

  // ⚠️ The pin behind the data line, register by register. A colour that the
  //    expander holds and does not send is usually a pin that is not an output.
  struct Named {
    const char* name;
    unsigned char reg;
  };
  const Named pins[] = {{"M_H", kRegGpioMH},   {"O_H", kRegGpioOH},  {"I_H", 0x08},
                        {"PU_H", kRegGpioPuH}, {"PD_H", 0x0C},      {"DRV_H", kRegGpioDrvH}};
  for (const Named& pin : pins) {
    unsigned char value = 0;
    if (ReadRegister8(pin.reg, &value)) {
      printf("leds: %s=0x%02X (%s)\n", pin.name, value, (value & (1u << 5)) ? "pin 13 set" : "pin 13 clear");
    } else {
      printf("leds: %s unreadable\n", pin.name);
    }
  }

  unsigned char pixel[2] = {0, 0};
  for (int i = 0; i < 4; ++i) {
    const bool lo = ReadRegister8(static_cast<unsigned char>(kRegLedRamStart + i * 2), &pixel[0]);
    const bool hi = ReadRegister8(static_cast<unsigned char>(kRegLedRamStart + i * 2 + 1), &pixel[1]);
    if (!lo || !hi) {
      printf("leds: pixel %d unreadable\n", i);
      continue;
    }
    const unsigned int value = static_cast<unsigned int>(pixel[0]) |
                               (static_cast<unsigned int>(pixel[1]) << 8);
    printf("leds: pixel %d = 0x%04X (r=%u g=%u b=%u)\n", i, value,
           (value >> 11) & 0x1F, (value >> 5) & 0x3F, value & 0x1F);
  }

  // ⛔ Full red, all twelve, and a refresh. If the registers below come back
  //    holding the red and no pixel lights, then the expander's LED path is not
  //    what drives this unit — and the next question is which path does.
  bool ok = true;
  for (int i = 0; i < board::kLedCount; ++i) {
    ok = SetLedColor(i, 255, 0, 0) && ok;
  }
  ok = RefreshLeds() && ok;
  vTaskDelay(pdMS_TO_TICKS(200));

  unsigned char after_lo = 0;
  unsigned char after_hi = 0;
  const bool lo = ReadRegister8(kRegLedRamStart, &after_lo);
  const bool hi = ReadRegister8(static_cast<unsigned char>(kRegLedRamStart + 1), &after_hi);
  const unsigned int after = static_cast<unsigned int>(after_lo) |
                             (static_cast<unsigned int>(after_hi) << 8);
  printf("leds: wrote full red to %d, refresh %s; pixel 0 now %s0x%04X\n",
         board::kLedCount, ok ? "ok" : "failed",
         (lo && hi) ? "" : "unreadable ", (lo && hi) ? after : 0);

  g_light = Light::kOff;  // the write above is not a light; the next frame sets one
}

// ⛔ REMOVED on 2026-10-18, after it hung the machine. A bench command that held
//    LED_CFG bit 7 for three seconds — a bit no vendor driver writes — stopped
//    the console, the heartbeat, and the USB-Serial-JTAG ROM responding: the
//    board had to be unplugged and replugged. ⚠️ The lesson is the shape of the
//    rule: an untouched register bit is not "unused", it is "unknown", and a
//    guess written to it stops a machine rather than lighting one.
