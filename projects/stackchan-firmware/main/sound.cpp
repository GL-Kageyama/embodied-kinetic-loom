#include "sound.h"

#include <cmath>
#include <cstdio>

#include "driver/i2c_master.h"
#include "driver/i2s_std.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "board.h"
#include "display.h"
#include "i2c_bus.h"

namespace {

i2c_master_dev_handle_t g_amp = nullptr;
i2s_chan_handle_t g_tx = nullptr;
bool g_ready = false;

// --- the amplifier --------------------------------------------------------
//
// ⚠️ 16-bit registers behind an 8-bit address, big-endian. Every value below is
//    the driver's (esp_codec_dev, device/aw88298), read on 2026-10-18 — ⛔ not
//    one of them was discovered on this unit.
constexpr int kRegId = 0x00;
constexpr int kRegSysctrl = 0x04;
constexpr int kRegSysctrl2 = 0x05;
constexpr int kRegI2sctrl = 0x06;
constexpr int kRegHagccfg4 = 0x0C;  // the volume is this register's high byte
constexpr int kRegUnknown61 = 0x61;

// A software reset into the ID register. The vendor's driver writes this first
// and waits 50 ms.
constexpr uint16_t kSoftReset = 0x55AA;
// I2S enabled (bit 6) and the amplifier out of power-down (bits 0 and 1 clear).
constexpr uint16_t kSysctrlUp = 0x4040;
constexpr uint16_t kSysctrl2 = 0x0008;
// Philips I2S, 16-bit frame; the low nibble is the sample-rate code and is
// replaced below. ⚠️ The init table's own low nibble is `8` — 48,000 Hz — and
//    this board runs at 24,000, which is code `5`.
constexpr uint16_t kI2sctrlBase = 0x3CC0;
constexpr uint16_t kRateCode24k = 0x5;
// The low byte is another field's; the init leaves it at 0x64 and the volume
// writes preserve it.
constexpr uint16_t kHagccfg4Low = 0x0064;
constexpr uint16_t kUnknown61 = 0x0673;

bool WriteReg(uint8_t reg, uint16_t value) {
  const uint8_t buffer[3] = {reg, static_cast<uint8_t>(value >> 8),
                             static_cast<uint8_t>(value & 0xFF)};
  return i2c_master_transmit(g_amp, buffer, sizeof(buffer), 100) == ESP_OK;
}

// The vendor's driver's own conversion: -96 dB .. 0 dB in 6 dB steps of the high
// nibble and 3 dB steps of the low one. ⛔ A number in a register is not a
// loudness — the knob the bench turns is a percentage, and this is only the
// translation the vendor uses.
uint8_t VolumeField(int db) {
  if (db > 0) {
    return 0;
  }
  int hi = (-db) / 6;
  if (hi > 0xF) {
    hi = 0xF;
  }
  int lo = ((-db) - hi * 6) * 2;
  if (lo < 0) lo = 0;
  if (lo > 0xF) lo = 0xF;
  return static_cast<uint8_t>((hi << 4) | lo);
}

bool WriteVolumeField(uint8_t field) {
  return WriteReg(static_cast<uint8_t>(kRegHagccfg4),
                  static_cast<uint16_t>((field << 8) | kHagccfg4Low));
}

bool BringUpAmplifier() {
  if (!i2c_bus::begin()) {
    std::printf("sound: no I2C bus\n");
    return false;
  }
  i2c_device_config_t config = {};
  config.dev_addr_length = I2C_ADDR_BIT_LEN_7;
  config.device_address = board::kAw88298Address;
  config.scl_speed_hz = 100000;
  if (i2c_master_bus_add_device(i2c_bus::handle(), &config, &g_amp) != ESP_OK) {
    std::printf("sound: the AW88298 did not answer on the bus\n");
    return false;
  }

  // ⚠️ Reset is a pin on the expander, not a register on the amplifier. The
  //    display owns that expander and does the pulse.
  if (!display::pulse_amplifier_reset()) {
    std::printf("sound: the reset line could not be pulsed (the display's expander is down)\n");
    return false;
  }

  const uint16_t init[][2] = {
      {kRegId, kSoftReset},
  };
  for (const auto& pair : init) {
    if (!WriteReg(static_cast<uint8_t>(pair[0]), pair[1])) {
      std::printf("sound: the AW88298 did not take its reset\n");
      return false;
    }
  }
  vTaskDelay(pdMS_TO_TICKS(50));

  const uint16_t setup[][2] = {
      {kRegSysctrl, kSysctrlUp},
      {kRegSysctrl2, kSysctrl2},
      {kRegI2sctrl, static_cast<uint16_t>(kI2sctrlBase | kRateCode24k)},
      {kRegUnknown61, kUnknown61},
  };
  for (const auto& pair : setup) {
    if (!WriteReg(static_cast<uint8_t>(pair[0]), pair[1])) {
      std::printf("sound: the AW88298 did not take register 0x%02X\n", pair[0]);
      return false;
    }
  }

  // ⚠️ **The vendor's own initial volume is -18 dB (6 dB x 3 in the high
  //    nibble), and until 2026-10-19 this line wrote it.** On that morning the
  //    author heard the four words and said the whole thing was 「少し小さい」;
  //    at `bench volume 90` — the vendor's -10 dB — the four were judged right.
  //    ⛔ **The boot volume is now that judgement, not the vendor's default**:
  //    -10 dB in the same 6 dB / 3 dB encoding, i.e. 0x18.
  if (!WriteVolumeField(VolumeField(-10))) {
    std::printf("sound: the AW88298 did not take a volume\n");
    return false;
  }
  return true;
}

// --- I2S ------------------------------------------------------------------

bool BringUpI2s() {
  i2s_chan_config_t channel = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
  channel.auto_clear = true;  // a gap is silence, not the last buffer again
  if (i2s_new_channel(&channel, &g_tx, nullptr) != ESP_OK) {
    std::printf("sound: I2S_NUM_0 would not open\n");
    return false;
  }

  i2s_std_config_t std = {
      .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(board::kAudioSampleRate),
      .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT,
                                                     I2S_SLOT_MODE_STEREO),
      .gpio_cfg =
          {
              .mclk = static_cast<gpio_num_t>(board::kAudioMclk),
              .bclk = static_cast<gpio_num_t>(board::kAudioBclk),
              .ws = static_cast<gpio_num_t>(board::kAudioWs),
              .dout = static_cast<gpio_num_t>(board::kAudioDout),
              .din = I2S_GPIO_UNUSED,  // the microphone is not this module's
              .invert_flags = {.mclk_inv = false, .bclk_inv = false, .ws_inv = false},
          },
  };
  std.clk_cfg.mclk_multiple = I2S_MCLK_MULTIPLE_256;

  if (i2s_channel_init_std_mode(g_tx, &std) != ESP_OK) {
    std::printf("sound: the I2S standard mode did not take\n");
    return false;
  }
  if (i2s_channel_enable(g_tx) != ESP_OK) {
    std::printf("sound: the I2S channel would not start\n");
    return false;
  }
  return true;
}

// --- the words ------------------------------------------------------------
//
// ⚠️ These are choices, not measurements — the same standing as the twelve
//    LEDs' colours. Four words, four shapes: `hello` rises, `pip` is one bright
//    point, `chime` rises and rings, `fall` drops. ⛔ The table turns a word into
//    a tone only; it decides nothing about when a word is chosen.
struct Note {
  int hz;
  int ms;
};

constexpr Note kHello[] = {{659, 90}, {880, 150}};
constexpr Note kPip[] = {{1319, 70}};
constexpr Note kChime[] = {{880, 90}, {1319, 200}};
constexpr Note kFall[] = {{659, 110}, {440, 260}};

// 0.22 of full scale. ⛔ A comfortable choice on a 1 W speaker, not a measure-
//    ment of anything; the amplifier is at -10 dB above it.
constexpr float kAmplitude = 0.22f;
// ⛔ **`fall` is louder than the other three, and the reason is an ear, not a
//    measurement.** On 2026-10-19 the author heard the four words at one
//    amplitude and said **「4 が小さい」** — `fall` ends on 440 Hz, the lowest
//    note among them, and a 1 W speaker gives that frequency less than it
//    gives 880 or 1319. ⚠️ **The number below is the first value the ear was
//    asked about**, not a loudness measurement; if it is wrong, the ear says so
//    and this line moves.
constexpr float kAmplitudeFall = 0.34f;
constexpr int kFramesPerChunk = 240;  // 10 ms at 24 kHz
int16_t g_chunk[kFramesPerChunk * 2] = {};

void WriteNote(const Note& note, float amplitude) {
  const int frames = board::kAudioSampleRate * note.ms / 1000;
  constexpr int kAttackFrames = board::kAudioSampleRate * 4 / 1000;  // 4 ms
  const float step = 2.0f * 3.14159265f * static_cast<float>(note.hz) /
                     static_cast<float>(board::kAudioSampleRate);

  int done = 0;
  while (done < frames) {
    int count = frames - done;
    if (count > kFramesPerChunk) {
      count = kFramesPerChunk;
    }
    for (int i = 0; i < count; ++i) {
      const int t = done + i;
      float envelope = 1.0f;
      if (t < kAttackFrames) {
        envelope = static_cast<float>(t) / static_cast<float>(kAttackFrames);
      } else {
        const int left = frames - t;
        const int decay_from = frames - kAttackFrames;
        envelope = decay_from > 0
                       ? static_cast<float>(left) / static_cast<float>(decay_from)
                       : 0.0f;
      }
      const float sample = std::sin(step * static_cast<float>(t)) * amplitude * envelope;
      const int16_t value = static_cast<int16_t>(sample * 32767.0f);
      g_chunk[i * 2] = value;
      g_chunk[i * 2 + 1] = value;
    }
    size_t written = 0;
    if (i2s_channel_write(g_tx, g_chunk, static_cast<size_t>(count) * 2 * sizeof(int16_t),
                          &written, pdMS_TO_TICKS(500)) != ESP_OK) {
      return;
    }
    done += count;
  }
}

const Note* NotesFor(Sound word, int* count) {
  switch (word) {
    case Sound::kHello:
      *count = static_cast<int>(sizeof(kHello) / sizeof(kHello[0]));
      return kHello;
    case Sound::kPip:
      *count = static_cast<int>(sizeof(kPip) / sizeof(kPip[0]));
      return kPip;
    case Sound::kChime:
      *count = static_cast<int>(sizeof(kChime) / sizeof(kChime[0]));
      return kChime;
    case Sound::kFall:
      *count = static_cast<int>(sizeof(kFall) / sizeof(kFall[0]));
      return kFall;
    case Sound::kNone:
      break;
  }
  *count = 0;
  return nullptr;
}

}  // namespace

bool sound::begin() {
  if (g_ready) {
    return true;
  }
  if (!BringUpAmplifier()) {
    return false;
  }
  if (!BringUpI2s()) {
    return false;
  }
  // ⚠️ A little silence first, so the first note does not begin on a DC step.
  i2s_channel_write(g_tx, g_chunk, sizeof(g_chunk), nullptr, pdMS_TO_TICKS(200));
  g_ready = true;
  std::printf("sound: AW88298 up, I2S %d Hz, 16-bit stereo\n", board::kAudioSampleRate);
  return true;
}

void sound::play(Sound word) {
  if (!g_ready || word == Sound::kNone) {
    return;
  }
  int count = 0;
  const Note* notes = NotesFor(word, &count);
  const float amplitude = word == Sound::kFall ? kAmplitudeFall : kAmplitude;
  for (int i = 0; i < count; ++i) {
    WriteNote(notes[i], amplitude);
  }
}

bool sound::set_volume_percent(int percent) {
  if (g_amp == nullptr) {
    return false;
  }
  if (percent < 0) {
    percent = 0;
  }
  if (percent > 100) {
    percent = 100;
  }
  // ⚠️ The vendor's driver maps a percentage onto -96..0 dB, linearly.
  const int db = -96 + (percent * 96) / 100;
  return WriteVolumeField(VolumeField(db));
}
