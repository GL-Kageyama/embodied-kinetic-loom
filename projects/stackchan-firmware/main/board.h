// Board constants for machine 2 — the M5Stack Stack-chan (ESP32-S3).
//
// ⚠️ EVERY NUMBER BELOW IS THE VENDOR'S RECORD, read on 2026-10-18 from
//    m5stack/StackChan, branch firmware-dev, MIT. None of it is a measurement
//    made in this repository. The one exception is named where it is used: the
//    two zero positions are read at boot from this unit's own NVS, where the
//    vendor's setup wizard left them.
//
// ⛔ A number is named once, here, and used by name everywhere else. A default
//    cannot say whose number it is.
#pragma once

namespace board {

// --- the servo bus (vendor: hal_servo.cpp, `_scs_bus.begin(...)`) ---
constexpr int kServoUart = 1;      // UART_NUM_1
constexpr int kServoBaud = 1000000;
constexpr int kServoTx = 6;        // GPIO 6
constexpr int kServoRx = 7;        // GPIO 7

constexpr int kYawId = 1;
constexpr int kPitchId = 2;

// --- the I2C bus that carries the IO expander (vendor: stackchan.cc) ---
constexpr int kI2cPort = 1;
constexpr int kI2cSda = 12;             // GPIO 12
constexpr int kI2cScl = 11;             // GPIO 11
constexpr int kExpanderAddress = 0x6F;  // PY32IOExpander_Class::DEFAULT_ADDRESS

// --- the expander's pins (vendor: hal_io_expander.cpp) ---
constexpr int kServoPowerPin = 0;
// ⚠️ A pin number on the expander, not an ESP32 GPIO — the two numbers happen to
//    be 13 and mean different wires. GPIO 13 is the I2S data line, below.
constexpr int kLedDataPin = 13;
constexpr int kLedCount = 12;

// --- the display (vendor: hal/board/stackchan.cc, InitializeSpi and
//     InitializeIli9342Display; panel read off the unit's own boot log on
//     2026-10-18: `CIPHER:0x64 / FIRMID:0x10 / VENDID:0x11, panel:ILI9342C`) ---
constexpr int kDisplayMosi = 37;    // GPIO 37
constexpr int kDisplaySclk = 36;    // GPIO 36
constexpr int kDisplayCs = 3;       // GPIO 3
constexpr int kDisplayDc = 35;      // GPIO 35
constexpr int kDisplayWidth = 320;
constexpr int kDisplayHeight = 240;

// --- the two other devices on the I2C bus (vendor: stackchan.cc) ---
constexpr int kAw9523Address = 0x58;    // the display's reset line
constexpr int kAxp2101Address = 0x34;   // the backlight rail (DLDO1)

// --- the speaker (vendor: hal/board/config.h and cores3_audio_codec.cc) ---
// ⚠️ 24,000 Hz, 16-bit stereo, the ESP32-S3 as I2S master. These are the
//    vendor's numbers, read on 2026-10-18; ⛔ none of them was measured here.
constexpr int kAudioSampleRate = 24000;
constexpr int kAudioMclkMultiple = 256;  // I2S_MCLK_MULTIPLE_256
constexpr int kAudioMclk = 0;            // GPIO 0
constexpr int kAudioBclk = 34;           // GPIO 34
constexpr int kAudioWs = 33;             // GPIO 33
constexpr int kAudioDout = 13;           // GPIO 13
constexpr int kAudioDin = 14;            // GPIO 14 — the microphone; unused here
// ⚠️ The amplifier answers at 0x36 on the same bus as the display's two chips.
constexpr int kAw88298Address = 0x36;
// ⚠️ Its reset line is P0.2 on the AW9523 — the expander the display already
//    owns. ⛔ Not a GPIO: the pulse is an I2C write, and `display` holds the
//    handle. `sound::begin()` calls back into it rather than opening the
//    expander a second time.
constexpr int kAmpResetBit = 2;  // AW9523 port 0, bit 2

// --- the scale (vendor: hal_servo.cpp, `set_angle_impl`) ---
//   raw = zero + angle * 16 / 5 / 10,  with angle in 0.1 degree
//   => one servo count is 0.3125 degree
// ⚠️ The vendor's integer arithmetic truncates; this firmware keeps the angle in
//    0.1-degree units and recomputes from the zero each time, so it does not
//    compound the truncation across steps.

// --- the vendor's own limits, in 0.1-degree units ---
constexpr int kYawAngleLimitTenths = 1280;    // +/- 128.0 degrees
constexpr int kPitchAngleMinTenths = 30;      // +3.0 degrees
constexpr int kPitchAngleMaxTenths = 870;     // +87.0 degrees
constexpr int kRawMin = 0;
constexpr int kRawMax = 1000;

// --- the zeros, if NVS does not answer ---
// ⚠️ These are the vendor's defaults, not this unit's values. When they are
//    used, the boot log says so: the difference between a measured zero and a
//    default zero is the difference between a head and a guess.
constexpr int kYawZeroDefault = 460;
constexpr int kPitchZeroDefault = 620;

// --- the bench envelope (this repository's choice, not a measurement) ---
// ⚠️ Small on purpose: the first moves are meant to be watched.
// ⚠️ Raised from 200 to 450 on 2026-10-18, while the gesture -> angle table was
//    being measured: `perk` was judged at +8 and the next posture, +20, was
//    judged too small for `turn`. Still a bench bound — a third of the vendor's
//    +/-128.0 — and it is not a gesture's limit: the table names an angle, and
//    a gesture may sit inside this envelope or not.
constexpr int kBenchYawMaxTenths = 450;  // +/- 45.0 degrees

// --- timing ---
// ⚠️ The one recorded constraint on this machine: commands that involve
//    movement must be at least one second apart (docs/first-contact-stackchan.md).
constexpr int kStepIntervalMs = 1000;
constexpr int kStepCounts = 3;  // ~0.94 degree per step

}  // namespace board
