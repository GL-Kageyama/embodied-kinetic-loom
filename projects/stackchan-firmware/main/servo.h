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

// ⚠️ Written on 2026-10-19, after `bench scan` answered for both ids while
//    `bench read` did not. Those two are different answers and this made them
//    one. It prints every byte the servo sent back, the status byte by name,
//    and nothing is refused: ⛔ a servo that says "overheat" is present, and
//    `read_position` calls it absent.
void diagnose_position(int id);

// ⚠️ Written on 2026-10-19, to ask the servo what it is being fed. The SCSCL
//    table puts present voltage at register 62, temperature at 63 and load at
//    60..61, so one read of 56..63 answers in the servo's own words what no
//    number on this side of the wire could: the rail's volts, at the servo.
//    ⛔ It is the servo's measurement, not a meter's — if the servo is dark,
//    it says nothing.
void diagnose_state(int id);

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
