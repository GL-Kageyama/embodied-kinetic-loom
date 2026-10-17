// The Feetech SCS-series bus, as the vendor's firmware drives it.
//
// ⚠️ The packet layout is the Feetech SCSCL protocol, read from the vendor's
//    bundled driver (m5stack/StackChan, MIT): `FF FF ID LEN INST ADDR data... CS`,
//    with the checksum the bitwise complement of the byte sum.
//
// ⛔ This is a bench driver, not a motion pipeline. It sends a goal position
//    when it is told to, and it sends nothing otherwise. There is no stream, no
//    loop, and no interpolation here — those live upstream of the wire.
#pragma once

namespace scs {

bool begin();

// Reads the servo's present position. A read that does not answer, does not
// parse, or carries a non-zero status byte is refused — not guessed.
bool read_position(int id, int* out_raw);

// Writes a goal position. The value is clamped to the vendor's raw range
// (board::kRawMin..kRawMax) before it leaves the host.
bool write_position(int id, int raw, unsigned short time_ms, unsigned short speed);

bool ping(int id);

// Torque on drives the servo toward its goal; torque off leaves it limp.
// ⚠️ The vendor's own motion layer releases torque at rest (Servo::init), so
//    this firmware does the same. ⛔ Write the present position as the goal
//    BEFORE enabling torque, or the servo drives to whatever goal it last held.
bool set_torque(int id, bool enabled);

}  // namespace scs
