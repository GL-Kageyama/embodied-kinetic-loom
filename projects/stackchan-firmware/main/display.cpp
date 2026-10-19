#include "display.h"

#include <cstdio>
#include <cstring>

#include "driver/i2c_master.h"
#include "driver/spi_master.h"
#include "esp_lcd_panel_io.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"

#include "board.h"
#include "face_bitmap.h"
#include "i2c_bus.h"

namespace {

i2c_master_dev_handle_t g_aw9523 = nullptr;
i2c_master_dev_handle_t g_axp2101 = nullptr;
esp_lcd_panel_io_handle_t g_io = nullptr;
SemaphoreHandle_t g_flushed = nullptr;

uint8_t g_grey[face_bitmap::kBytes] = {};
uint16_t g_line[board::kDisplayWidth * 8] = {};

// ⛔ Two tasks reach this buffer now: `show` from the console task (a frame
//    arrived) and `tick` from the main loop (a blink). ⚠️ A half-drawn frame is
//    not a wrong face — it is the tear that took a day to find (0.19.x, the
//    DMA buffer), so the lock is not about the face being interesting.
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

// ⚠️ The blink clock. ⛔ Its gaps are a choice, not a measurement: a blink is a
//    drawing the author's eye has not seen yet. They are irregular on purpose —
//    an even period reads as a metronome, and a metronome is not alive. ⛔ No
//    RNG: a schedule that cannot be read out of the source cannot be checked by
//    anyone, and this list can.
constexpr int kBlinkGapsMs[] = {3200, 5400, 4100, 6800, 3700, 5900, 4600};
constexpr int kBlinkGapCount = static_cast<int>(sizeof(kBlinkGapsMs) / sizeof(kBlinkGapsMs[0]));
//: ⚠️ How long the lids stay shut. A real blink is 100–400 ms; this one is short
//: because a whole frame is 30 ms and the screen is the only thing moving.
constexpr int kBlinkClosedMs = 80;

//: ⚠️ The last face actually drawn. `Face::kNone` means "nothing drawn yet":
//: since 0.19.45 a `face:null` frame does not reach `show` at all, so this is
//: never cleared by the host saying "do not change".
Face g_drawn = Face::kNone;
int g_next_blink_ms = 0;
int g_blink_until_ms = -1;
int g_blink_index = 0;

int NowMs() { return static_cast<int>(esp_timer_get_time() / 1000); }

void ScheduleBlink(int now) {
  g_next_blink_ms = now + kBlinkGapsMs[g_blink_index % kBlinkGapCount];
  ++g_blink_index;
}

// ⛔ **`tx_color` queues a DMA transfer and returns; the buffer belongs to the
//    DMA until this callback fires.** `esp_lcd_panel_io.h` says so in the one
//    sentence that mattered here: *"The caller should take care of the lifecycle
//    of the `color` buffer. Recycling of color buffer should be done in the
//    callback `on_color_trans_done()`."* ⚠️ The first version of this file
//    filled `g_line` with the next eight rows immediately, so the tail of every
//    chunk was read after it had been overwritten with the head of the next one.
//    On the screen that looked like a copy of every shape eight rows below it —
//    a mouth drawn as two lines — and it was read as "jagged", then as "shifted
//    by two rows", for a day. ⇒ One buffer, one transfer at a time.
bool OnColorTransDone(esp_lcd_panel_io_handle_t, esp_lcd_panel_io_event_data_t*,
                      void*) {
  BaseType_t woken = pdFALSE;
  if (g_flushed != nullptr) {
    xSemaphoreGiveFromISR(g_flushed, &woken);
  }
  return woken == pdTRUE;
}

bool AddDevice(int address, i2c_master_dev_handle_t* out) {
  i2c_device_config_t config = {};
  config.dev_addr_length = I2C_ADDR_BIT_LEN_7;
  config.device_address = static_cast<uint16_t>(address);
  config.scl_speed_hz = 100000;
  return i2c_master_bus_add_device(i2c_bus::handle(), &config, out) == ESP_OK;
}

bool WriteReg(i2c_master_dev_handle_t device, uint8_t reg, uint8_t value) {
  const uint8_t buffer[2] = {reg, value};
  return i2c_master_transmit(device, buffer, sizeof(buffer), 100) == ESP_OK;
}

bool ReadReg(i2c_master_dev_handle_t device, uint8_t reg, uint8_t* out) {
  return i2c_master_transmit_receive(device, &reg, 1, out, 1, 100) == ESP_OK;
}

// --- the panel's two rails, and its reset line -----------------------------
// ⚠️ The vendor's own boot sequence (stackchan.cc: Aw9523 constructor and
//    ResetIli9342; Pmic constructor). ⛔ Not one of these values was measured
//    here, and the record says so.

bool BringUpAw9523() {
  const uint8_t setup[][2] = {
      {0x02, 0b00000111},
      {0x03, 0b10001111},
      {0x04, 0b00011000},
      {0x05, 0b00001100},
      {0x11, 0b00010000},
      {0x12, 0b11111111},
      {0x13, 0b11111111},
  };
  for (const auto& pair : setup) {
    if (!WriteReg(g_aw9523, pair[0], pair[1])) {
      return false;
    }
  }

  // Reset the LCD: P1.7 low for 20 ms, then high.
  if (!WriteReg(g_aw9523, 0x03, 0b10000001)) {
    return false;
  }
  vTaskDelay(pdMS_TO_TICKS(20));
  return WriteReg(g_aw9523, 0x03, 0b10000011);
}

bool BringUpAxp2101() {
  uint8_t value = 0;
  if (!ReadReg(g_axp2101, 0x90, &value)) {
    return false;
  }
  const uint8_t rails[][2] = {
      {0x90, static_cast<uint8_t>(value | 0b10110100)},
      {0x97, 28},
      {0x69, 0b00110101},
      {0x30, 0b00111111},
      {0x90, 0xBF},
      {0x94, 28},
      {0x95, 28},
      {0x27, 0x00},
      // The backlight is DLDO1 on the AXP2101: its voltage register is 0x99,
      // mapped by the vendor as 20 + brightness * 8 / 100. 26 is 75 %.
      {0x99, 26},
  };
  for (const auto& pair : rails) {
    if (!WriteReg(g_axp2101, pair[0], pair[1])) {
      return false;
    }
  }
  return ReadReg(g_axp2101, 0x62, &value) &&
         WriteReg(g_axp2101, 0x62, (value & 0xE0) | 0x06);
}

// --- the panel -------------------------------------------------------------

struct InitCommand {
  uint8_t command;
  const uint8_t* data;
  size_t size;
  uint16_t delay_ms;
};

// ⚠️ The ILI9342C init sequence esp_lcd_ili9341 v1.2.0 sends — the version the
//    unit's own boot log names (`LCD panel create success, version: 1.2.0`).
//    This file sends it through the core panel-IO API instead of that component,
//    so the repository gains no vendored tree. ⛔ MADCTL (0x36) carries BGR only:
//    the vendor's panel is created with `rgb_ele_order = BGR`, no mirror and no
//    swap.
constexpr uint8_t kCf[] = {0x00, 0xC1, 0x30};
constexpr uint8_t kEd[] = {0x64, 0x03, 0x12, 0x81};
constexpr uint8_t kE8[] = {0x85, 0x00, 0x78};
constexpr uint8_t kCb[] = {0x39, 0x2C, 0x00, 0x34, 0x02};
constexpr uint8_t kF7[] = {0x20};
constexpr uint8_t kEa[] = {0x00, 0x00};
constexpr uint8_t kC0[] = {0x23};
constexpr uint8_t kC1[] = {0x10};
constexpr uint8_t kC5[] = {0x3E, 0x28};
constexpr uint8_t kC7[] = {0x86};
constexpr uint8_t kMadctl[] = {0x08};
constexpr uint8_t kPixelFormat[] = {0x55};
constexpr uint8_t kB1[] = {0x00, 0x18};
constexpr uint8_t kB6[] = {0x08, 0x82, 0x27};
constexpr uint8_t kF2[] = {0x00};
constexpr uint8_t k26[] = {0x01};
constexpr uint8_t kPositive[] = {0x0F, 0x31, 0x2B, 0x0C, 0x0E, 0x08, 0x4E, 0xF1,
                                 0x37, 0x07, 0x10, 0x03, 0x0E, 0x09, 0x00};
constexpr uint8_t kNegative[] = {0x00, 0x0E, 0x14, 0x03, 0x11, 0x07, 0x31, 0xC1,
                                 0x48, 0x08, 0x0F, 0x0C, 0x31, 0x36, 0x0F};

constexpr InitCommand kInit[] = {
    {0xCF, kCf, sizeof(kCf), 0},   {0xED, kEd, sizeof(kEd), 0},
    {0xE8, kE8, sizeof(kE8), 0},   {0xCB, kCb, sizeof(kCb), 0},
    {0xF7, kF7, sizeof(kF7), 0},   {0xEA, kEa, sizeof(kEa), 0},
    {0xC0, kC0, sizeof(kC0), 0},   {0xC1, kC1, sizeof(kC1), 0},
    {0xC5, kC5, sizeof(kC5), 0},   {0xC7, kC7, sizeof(kC7), 0},
    {0x36, kMadctl, sizeof(kMadctl), 0},
    {0x3A, kPixelFormat, sizeof(kPixelFormat), 0},
    {0xB1, kB1, sizeof(kB1), 0},   {0xB6, kB6, sizeof(kB6), 0},
    {0xF2, kF2, sizeof(kF2), 0},   {0x26, k26, sizeof(k26), 0},
    {0xE0, kPositive, sizeof(kPositive), 0},
    {0xE1, kNegative, sizeof(kNegative), 0},
    // Invert on (0x21), sleep out (0x11) and display on (0x29).
    {0x21, nullptr, 0, 0},
    {0x11, nullptr, 0, 120},
    {0x29, nullptr, 0, 120},
};

bool BringUpPanel() {
  spi_bus_config_t bus = {};
  bus.mosi_io_num = board::kDisplayMosi;
  bus.miso_io_num = -1;
  bus.sclk_io_num = board::kDisplaySclk;
  bus.quadwp_io_num = -1;
  bus.quadhd_io_num = -1;
  bus.max_transfer_sz = sizeof(g_line);

  if (spi_bus_initialize(SPI3_HOST, &bus, SPI_DMA_CH_AUTO) != ESP_OK) {
    return false;
  }

  esp_lcd_panel_io_spi_config_t io_config = {};
  io_config.cs_gpio_num = board::kDisplayCs;
  io_config.dc_gpio_num = board::kDisplayDc;
  io_config.spi_mode = 2;
  io_config.pclk_hz = 40 * 1000 * 1000;
  io_config.trans_queue_depth = 10;
  io_config.lcd_cmd_bits = 8;
  io_config.lcd_param_bits = 8;

  if (esp_lcd_new_panel_io_spi(SPI3_HOST, &io_config, &g_io) != ESP_OK) {
    return false;
  }

  g_flushed = xSemaphoreCreateBinary();
  if (g_flushed == nullptr) {
    return false;
  }
  const esp_lcd_panel_io_callbacks_t callbacks = {
      .on_color_trans_done = OnColorTransDone,
  };
  if (esp_lcd_panel_io_register_event_callbacks(g_io, &callbacks, nullptr) != ESP_OK) {
    return false;
  }

  for (const auto& init : kInit) {
    if (esp_lcd_panel_io_tx_param(g_io, init.command, init.data, init.size) != ESP_OK) {
      return false;
    }
    if (init.delay_ms != 0) {
      vTaskDelay(pdMS_TO_TICKS(init.delay_ms));
    }
  }
  return true;
}

bool SetWindow() {
  const uint8_t columns[4] = {0x00, 0x00,
                              static_cast<uint8_t>((board::kDisplayWidth - 1) >> 8),
                              static_cast<uint8_t>((board::kDisplayWidth - 1) & 0xFF)};
  const uint8_t rows[4] = {0x00, 0x00,
                           static_cast<uint8_t>((board::kDisplayHeight - 1) >> 8),
                           static_cast<uint8_t>((board::kDisplayHeight - 1) & 0xFF)};
  return esp_lcd_panel_io_tx_param(g_io, 0x2A, columns, sizeof(columns)) == ESP_OK &&
         esp_lcd_panel_io_tx_param(g_io, 0x2B, rows, sizeof(rows)) == ESP_OK &&
         esp_lcd_panel_io_tx_param(g_io, 0x2C, nullptr, 0) == ESP_OK;
}

bool Push() {
  if (g_io == nullptr || !SetWindow()) {
    return false;
  }
  constexpr int kRowsPerChunk = 8;
  constexpr TickType_t kTransferTimeout = pdMS_TO_TICKS(200);
  for (int y0 = 0; y0 < board::kDisplayHeight; y0 += kRowsPerChunk) {
    int rows = board::kDisplayHeight - y0;
    if (rows > kRowsPerChunk) {
      rows = kRowsPerChunk;
    }
    const int pixels = rows * board::kDisplayWidth;
    for (int i = 0; i < pixels; ++i) {
      const int y = y0 + i / board::kDisplayWidth;
      const int x = i % board::kDisplayWidth;
      // ⚠️ One byte of coverage -> a grey RGB565 word, **byte-swapped**.
      //    The panel reads colour big-endian; the ESP32 writes it little-endian.
      //    0xFFFF and 0x0000 are the same either way, which is why the first two
      //    faces looked right and every grey edge was invisible: 0x8410 arrived
      //    as 0x1084 — near black — so the anti-aliasing was sent and not shown.
      const uint8_t value = g_grey[y * board::kDisplayWidth + x];
      const uint16_t colour = static_cast<uint16_t>(
          ((value >> 3) << 11) | ((value >> 2) << 5) | (value >> 3));
      g_line[i] = static_cast<uint16_t>((colour >> 8) | (colour << 8));
    }
    if (esp_lcd_panel_io_tx_color(g_io, -1, g_line,
                                  static_cast<size_t>(pixels) * sizeof(uint16_t)) != ESP_OK) {
      return false;
    }
    // ⛔ Wait for *this* chunk before touching `g_line` again. The wait is about
    //    a millisecond per chunk at 40 MHz, so a whole frame costs some 30 ms —
    //    which is the price of not tearing, and a face changes on an event.
    if (xSemaphoreTake(g_flushed, kTransferTimeout) != pdTRUE) {
      return false;
    }
  }
  return true;
}

}  // namespace

// ⚠️ Written on 2026-10-19, when the servo bus was silent from boot. The rail's
//    switch is the expander's pin 0; its volts come through this PMIC's path.
//    These registers say what the power side knows. ⛔ They are not the rail.
void display::pmu_probe() {
  if (g_axp2101 == nullptr) {
    std::printf("pmu: the AXP2101 never came up\n");
    return;
  }
  uint8_t status1 = 0;
  uint8_t status2 = 0;
  uint8_t batt_lo = 0;
  uint8_t batt_hi = 0;
  const bool has1 = ReadReg(g_axp2101, 0x00, &status1);
  const bool has2 = ReadReg(g_axp2101, 0x01, &status2);
  const bool has_batt = ReadReg(g_axp2101, 0x34, &batt_lo) && ReadReg(g_axp2101, 0x35, &batt_hi);

  std::printf("pmu: 0x00=%s0x%02X 0x01=%s0x%02X vbat=%s%d mV\n", has1 ? "" : "unreadable ",
              has1 ? status1 : 0, has2 ? "" : "unreadable ", has2 ? status2 : 0,
              has_batt ? "" : "unreadable ",
              has_batt ? (((batt_hi & 0x3F) << 8) | batt_lo) : 0);

  if (has2) {
    // The vendor's own reading of 0x01: bits 5–6 are the current's direction.
    const int direction = (status2 & 0b01100000) >> 5;
    const int charge_state = status2 & 0b00000111;
    std::printf("pmu: direction=%d (%s) charge_state=%d\n", direction,
                direction == 0   ? "standby"
                : direction == 1 ? "charging"
                : direction == 2 ? "discharging"
                                 : "unknown",
                charge_state);
  }
  std::printf("pmu: these are the PMIC's registers, not the servo rail's volts\n");
}

bool display::begin() {
  if (g_io != nullptr) {
    return true;
  }
  if (g_lock == nullptr) {
    g_lock = xSemaphoreCreateMutex();
    if (g_lock == nullptr) {
      std::printf("display: no lock\n");
      return false;
    }
  }
  if (!i2c_bus::begin()) {
    std::printf("display: no I2C bus\n");
    return false;
  }
  if (!AddDevice(board::kAw9523Address, &g_aw9523) ||
      !AddDevice(board::kAxp2101Address, &g_axp2101)) {
    std::printf("display: the AW9523 or the AXP2101 did not answer on the bus\n");
    return false;
  }
  if (!BringUpAw9523()) {
    std::printf("display: the AW9523 did not take its setup\n");
    return false;
  }
  if (!BringUpAxp2101()) {
    std::printf("display: the AXP2101 did not take its setup\n");
    return false;
  }
  if (!BringUpPanel()) {
    std::printf("display: the panel did not take its init sequence\n");
    return false;
  }

  std::memset(g_grey, 0, sizeof(g_grey));
  if (!Push()) {
    std::printf("display: the first frame did not go out\n");
    return false;
  }
  std::printf("display: ILI9342C up, backlight on — 320x240, five faces\n");
  return true;
}

void display::show(Face face) {
  if (g_io == nullptr) {
    return;
  }
  Guard guard;
  face_bitmap::render(face, g_grey);
  g_drawn = face;
  // ⚠️ A new face opens the lids: an expression arriving mid-blink is an
  //    expression, and finishing the blink first would delay it by 80 ms.
  g_blink_until_ms = -1;
  if (Push()) {
    ScheduleBlink(NowMs());
  }
}

void display::tick() {
  if (g_io == nullptr) {
    return;
  }
  const int now = NowMs();

  // ⚠️ One blink is two frames: shut, then open. Both are pushed from here, so
  //    that the console task never waits for a blink to finish.
  if (g_blink_until_ms >= 0) {
    if (now < g_blink_until_ms) {
      return;
    }
    Guard guard;
    g_blink_until_ms = -1;
    face_bitmap::render(g_drawn, g_grey);
    // ⚠️ The next gap is scheduled *here*, on the frame that opens the lids. It
    //    was scheduled only by `show()` at first, so after one blink the due time
    //    stayed in the past and every tick from then on closed the lids again —
    //    a light that did not blink but flickered. ⛔ A blink has two halves and
    //    the schedule belongs to the half that finishes it.
    if (Push()) {
      ScheduleBlink(now);
    }
    return;
  }

  if (now < g_next_blink_ms || !face_bitmap::can_blink(g_drawn)) {
    return;
  }
  Guard guard;
  face_bitmap::render_blink(g_drawn, g_grey);
  if (!Push()) {
    return;
  }
  g_blink_until_ms = now + kBlinkClosedMs;
}

bool display::pulse_amplifier_reset() {
  if (g_aw9523 == nullptr) {
    return false;
  }
  // ⚠️ The vendor's own pulse (stackchan.cc: Aw9523::ResetAw88298): P0.2 low
  //    for 10 ms, high again, then 50 ms before the amplifier is spoken to.
  //    The other two bits of port 0 are left high, as the constructor left them.
  const uint8_t high = static_cast<uint8_t>(0b00000111);
  const uint8_t low = static_cast<uint8_t>(high & ~(1u << board::kAmpResetBit));
  if (!WriteReg(g_aw9523, 0x02, low)) {
    return false;
  }
  vTaskDelay(pdMS_TO_TICKS(10));
  if (!WriteReg(g_aw9523, 0x02, high)) {
    return false;
  }
  vTaskDelay(pdMS_TO_TICKS(50));
  return true;
}
