// Stack-chan — the device end of the wire, on the unit in hand.
//
// ⛔ What this firmware does NOT do:
//   - it has no display renderer, so a `face` is logged as a meaning, not drawn;
//   - it does not move at boot, and it does not move unless a line arrives.
//
// ✅ What it does:
//   - reads the two zero positions out of this unit's NVS (the wizard's
//     measurement), or says loudly that it fell back to the vendor's defaults;
//   - lights twelve LEDs for the contract's `light` word;
//   - plays the contract's `gesture` word from a table measured on this unit
//     with the author's eye (2026-10-18) — one posture per gesture, and `nod`
//     goes down and comes back;
//   - answers `bench` commands from the USB Serial/JTAG console, which is how the
//     first arrival is meant to be watched: one person types, one head turns;
//   - applies the second line type, `pose <yaw_tenths> <pitch_tenths>*<CC>`, one
//     per tick — the host interpolates and this end applies, and 500 ms of
//     silence releases torque. ⛔ It has never been streamed to this unit yet.
//
// ⚠️ `bench` is not part of the wire and is not a vocabulary. It is the bench.
#include <sys/select.h>
#include <unistd.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "esp_ota_ops.h"
#include "esp_rom_sys.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "board.h"
#include "command_frame.h"
#include "leds.h"
#include "servo.h"
#include "zeros.h"

namespace {

constexpr int kMaxLine = 256;

// --- the pose line: machine 2's second line type --------------------------
// ⚠️ `engine/backend/protocol_stackchan_pose.py` is the spelling; this is the
//    other end of it. ⛔ Degrees, not servo counts: the zeros are this unit's,
//    read from its own NVS at boot, and they stay on this side of the wire.
constexpr int kPoseMaxTenths = 1800;        // the protocol's sanity bound
constexpr int kPoseMaxLine = 64;            // the protocol's line bound, not the console's
constexpr int64_t kPoseSilenceUs = 500000;  // 500 ms of silence releases torque
// ⚠️ Measured on this unit, 2026-10-18 (0.19.5): speed=100 moved about
//    127 counts/s, roughly 40 deg/s. ⛔ The speed is the servo's ceiling, not the
//    trajectory: the host's goals arrive every 20 ms and are the governor.
constexpr int kPoseSpeed = 100;

bool g_streaming = false;
int64_t g_last_pose_us = 0;
int g_pose_count = 0;
int g_pose_refused = 0;
int g_pose_clamped = 0;
unsigned int g_pose_codes = 0;  // which refusal codes have been printed this stream

char g_line[kMaxLine + 1];
int g_line_len = 0;

int g_yaw_zero = board::kYawZeroDefault;
int g_pitch_zero = board::kPitchZeroDefault;
bool g_zeros_from_nvs = false;

bool g_servos_ready = false;

int RawFromAngle(int zero, int angle_tenths) {
  // The vendor's own formula, in 0.1-degree units.
  return zero + angle_tenths * 16 / 5 / 10;
}

int Clamp(int value, int low, int high) {
  if (value < low) return low;
  if (value > high) return high;
  return value;
}

const char* FaceName(Face face) {
  switch (face) {
    case Face::kNone: return "none";
    case Face::kCurious: return "curious";
    case Face::kGreeting: return "greeting";
    case Face::kHappy: return "happy";
    case Face::kAngry: return "angry";
    case Face::kSleepy: return "sleepy";
  }
  return "?";
}

const char* LightName(Light light) {
  switch (light) {
    case Light::kOff: return "off";
    case Light::kDim: return "dim";
    case Light::kBreathe: return "breathe";
    case Light::kWarm: return "warm";
    case Light::kAlert: return "alert";
    case Light::kError: return "error";
  }
  return "?";
}

const char* GestureName(Gesture gesture) {
  switch (gesture) {
    case Gesture::kNone: return "none";
    case Gesture::kLookUp: return "look_up";
    case Gesture::kNod: return "nod";
    case Gesture::kLookSide: return "look_side";
    case Gesture::kRest: return "rest";
    case Gesture::kRecoil: return "recoil";
  }
  return "?";
}

const char* ParseResultName(ParseResult result) {
  switch (result) {
    case ParseResult::kOk: return "ok";
    case ParseResult::kTooLong: return "too long";
    case ParseResult::kMalformed: return "malformed";
    case ParseResult::kNotAnObject: return "not an object";
    case ParseResult::kUnknownKey: return "unknown key";
    case ParseResult::kMissingKey: return "missing key";
    case ParseResult::kBadType: return "bad type";
    case ParseResult::kUnknownValue: return "unknown value";
  }
  return "?";
}

void PrintHelp() {
  printf("commands\n");
  printf("  {\"face\":...,\"light\":...,\"gesture\":...}  one frame from the wire\n");
  printf("  pose <yaw_tenths> <pitch_tenths>*<CC>   one pose per tick; 500 ms of silence releases torque\n");
  printf("  bench pos                 present positions\n");
  printf("  bench scan                which servo ids answer, 1..12\n");
  printf("  bench read <id>           raw position of one id\n");
  printf("  bench zeros               the zeros this boot used, and where they came from\n");
  printf("  bench move <yaw_deg> [pitch_deg]   slow: about 1 degree per second\n");
  printf("  bench set <yaw_deg> <pitch_deg> [speed]   one goal to both axes, then held\n");
  printf("  bench timed <yaw_deg> <time> [speed]   one goal with time and speed; reads back every 200 ms\n");
  printf("  bench hold                hold the present positions (torque on)\n");
  printf("  bench release             torque off — the head goes limp\n");
  printf("  bench power on|off        the servo rail — the only stop this machine has\n");
  printf("  bench leds                read the expander back, then set all twelve full red\n");
  printf("  help\n");
}

// One axis, about one degree per second, at least one second between packets.
bool MoveAxis(int id, int target_raw, int current_raw, const char* name) {
  while (current_raw != target_raw) {
    int delta = target_raw - current_raw;
    if (delta > board::kStepCounts) delta = board::kStepCounts;
    if (delta < -board::kStepCounts) delta = -board::kStepCounts;
    current_raw += delta;
    if (!scs::write_position(id, current_raw, 0, 100)) {
      printf("bench: write to %s failed; stopped at raw %d\n", name, current_raw);
      return false;
    }
    printf("bench: %s -> raw %d\n", name, current_raw);
    vTaskDelay(pdMS_TO_TICKS(board::kStepIntervalMs));
  }
  return true;
}

bool ParseDegrees(const char** text, int* tenths) {
  char* end = nullptr;
  const float value = std::strtof(*text, &end);
  if (end == *text) {
    return false;
  }
  *text = end;
  *tenths = static_cast<int>(value * 10.0f + (value >= 0.0f ? 0.5f : -0.5f));
  return true;
}

void BenchPos() {
  int yaw = -1;
  int pitch = -1;
  const bool yaw_ok = scs::read_position(board::kYawId, &yaw);
  const bool pitch_ok = scs::read_position(board::kPitchId, &pitch);
  printf("bench: yaw=%s pitch=%s\n", yaw_ok ? "ok" : "no answer",
         pitch_ok ? "ok" : "no answer");
  if (yaw_ok) {
    printf("bench: yaw raw %d, angle %d.%d deg (zero %d)\n",
           yaw, (yaw - g_yaw_zero) * 5 * 10 / 16 / 10,
           std::abs((yaw - g_yaw_zero) * 5 * 10 / 16) % 10, g_yaw_zero);
  }
  if (pitch_ok) {
    printf("bench: pitch raw %d, angle %d.%d deg (zero %d)\n",
           pitch, (pitch - g_pitch_zero) * 5 * 10 / 16 / 10,
           std::abs((pitch - g_pitch_zero) * 5 * 10 / 16) % 10, g_pitch_zero);
  }
}

void BenchMove(int yaw_tenths, bool has_pitch, int pitch_tenths) {
  if (!g_servos_ready) {
    printf("bench: refused — the servo bus did not come up\n");
    return;
  }

  const int yaw_wanted = yaw_tenths;
  yaw_tenths = Clamp(yaw_tenths, -board::kBenchYawMaxTenths, board::kBenchYawMaxTenths);
  if (yaw_tenths != yaw_wanted) {
    printf("bench: yaw clamped to %d.%d deg\n", yaw_tenths / 10,
           std::abs(yaw_tenths) % 10);
  }

  int yaw_now = -1;
  int pitch_now = -1;
  if (!scs::read_position(board::kYawId, &yaw_now)) {
    printf("bench: refused — yaw (id 1) did not answer\n");
    return;
  }
  if (!scs::read_position(board::kPitchId, &pitch_now)) {
    printf("bench: refused — pitch (id 2) did not answer\n");
    return;
  }

  // ⛔ Both goals are set to where the servos already are before torque comes
  //    on. A torque-enabled servo drives to its goal; if that goal were stale,
  //    the first step would be a jump, and this machine's failure mode is the
  //    rail dropping, not a slow move.
  scs::write_position(board::kYawId, yaw_now, 0, 0);
  scs::write_position(board::kPitchId, pitch_now, 0, 0);
  scs::set_torque(board::kYawId, true);
  scs::set_torque(board::kPitchId, true);
  vTaskDelay(pdMS_TO_TICKS(200));

  const int yaw_target = Clamp(RawFromAngle(g_yaw_zero, yaw_tenths),
                               board::kRawMin, board::kRawMax);
  printf("bench: yaw %d -> %d (raw), one step per second\n", yaw_now, yaw_target);
  bool ok = MoveAxis(board::kYawId, yaw_target, yaw_now, "yaw");

  if (ok && has_pitch) {
    const int pitch_wanted = pitch_tenths;
    pitch_tenths = Clamp(pitch_tenths, board::kPitchAngleMinTenths,
                         board::kPitchAngleMaxTenths);
    if (pitch_tenths != pitch_wanted) {
      printf("bench: pitch clamped to the vendor's %d.%d..%d.%d deg\n",
             board::kPitchAngleMinTenths / 10, board::kPitchAngleMinTenths % 10,
             board::kPitchAngleMaxTenths / 10, board::kPitchAngleMaxTenths % 10);
    }
    const int pitch_target = Clamp(RawFromAngle(g_pitch_zero, pitch_tenths),
                                   board::kRawMin, board::kRawMax);
    printf("bench: pitch %d -> %d (raw), one step per second\n", pitch_now, pitch_target);
    ok = MoveAxis(board::kPitchId, pitch_target, pitch_now, "pitch");
  }

  // ⚠️ Released whatever happened, so a failed move does not leave the servo
  //    holding a pose with current running through it.
  scs::set_torque(board::kYawId, false);
  scs::set_torque(board::kPitchId, false);
  printf("bench: torque released — the head is limp again\n");
  printf("bench: %s\n", ok ? "done" : "stopped early");
}

// ⚠️ A measurement, not a smooth mover. `bench move` rewrites a goal once a second
//    and stops between steps; this writes ONE goal carrying a time field and then
//    reads the shaft every 200 ms, so both the duration and the shape of the travel
//    are recorded rather than remembered. ⛔ `time_ms` is named on an assumption —
//    the unit has never been measured on this unit, and a wrong unit is a jump, not
//    a slow move. That is why the amplitude stays small and the observation is the
//    point. Speed is 0 so that, if the time field is honoured, nothing else moves it.
void BenchTimed(int yaw_tenths, int time_field, int speed) {
  if (!g_servos_ready) {
    printf("bench: refused — the servo bus did not come up\n");
    return;
  }
  const int yaw_wanted = yaw_tenths;
  yaw_tenths = Clamp(yaw_tenths, -board::kBenchYawMaxTenths, board::kBenchYawMaxTenths);
  if (yaw_tenths != yaw_wanted) {
    printf("bench: yaw clamped to %d.%d deg\n", yaw_tenths / 10,
           std::abs(yaw_tenths) % 10);
  }

  int yaw_now = -1;
  int pitch_now = -1;
  if (!scs::read_position(board::kYawId, &yaw_now) ||
      !scs::read_position(board::kPitchId, &pitch_now)) {
    printf("bench: refused — a servo did not answer\n");
    return;
  }

  // ⚠️ Same rule as `bench move`: both goals sit on the present positions before
  //    torque comes on, so nothing drives to a stale goal.
  scs::write_position(board::kYawId, yaw_now, 0, 0);
  scs::write_position(board::kPitchId, pitch_now, 0, 0);
  scs::set_torque(board::kYawId, true);
  scs::set_torque(board::kPitchId, true);
  vTaskDelay(pdMS_TO_TICKS(200));

  const int yaw_target = Clamp(RawFromAngle(g_yaw_zero, yaw_tenths),
                               board::kRawMin, board::kRawMax);
  const bool written = scs::write_position(
      board::kYawId, yaw_target, static_cast<unsigned short>(time_field & 0xFFFF),
      static_cast<unsigned short>(speed & 0xFFFF));
  printf("bench: timed yaw %d -> %d, time=%d speed=%d (units not measured); "
         "reading every 200 ms\n",
         yaw_now, yaw_target, time_field, speed);
  if (!written) {
    printf("bench: the write failed\n");
  }

  int last = yaw_now;
  int same = 0;
  int elapsed = 0;
  for (int i = 0; i < 350; ++i) {  // 70 s of watching, then give up
    vTaskDelay(pdMS_TO_TICKS(200));
    elapsed += 200;
    int now = -1;
    if (!scs::read_position(board::kYawId, &now)) {
      printf("bench: t=%d ms no answer\n", elapsed);
      continue;
    }
    if (now == last) {
      ++same;
    } else {
      same = 0;
      last = now;
    }
    printf("bench: t=%d ms raw %d\n", elapsed, now);
    if (now == yaw_target && same >= 5) {  // arrived and settled for a second
      break;
    }
  }

  scs::set_torque(board::kYawId, false);
  scs::set_torque(board::kPitchId, false);
  printf("bench: torque released — the head is limp again\n");
  printf("bench: done\n");
}


// ⚠️ A posture, held — the command a gesture table is measured with. One goal to
//    each axis, armed on the present positions exactly as `bench timed` does, and
//    then torque stays on. ⛔ The angles are the host's instruction, not a
//    measurement: what is measured is which posture the eye calls a `perk`.
void BenchSet(int yaw_tenths, int pitch_tenths, int speed) {
  if (!g_servos_ready) {
    printf("bench: refused — the servo bus did not come up\n");
    return;
  }
  const int yaw_wanted = yaw_tenths;
  yaw_tenths = Clamp(yaw_tenths, -board::kBenchYawMaxTenths, board::kBenchYawMaxTenths);
  if (yaw_tenths != yaw_wanted) {
    printf("bench: yaw clamped to %d.%d deg\n", yaw_tenths / 10,
           std::abs(yaw_tenths) % 10);
  }
  const int pitch_wanted = pitch_tenths;
  pitch_tenths = Clamp(pitch_tenths, board::kPitchAngleMinTenths,
                       board::kPitchAngleMaxTenths);
  if (pitch_tenths != pitch_wanted) {
    printf("bench: pitch clamped to %d.%d deg\n", pitch_tenths / 10,
           pitch_tenths % 10);
  }

  int yaw_now = -1;
  int pitch_now = -1;
  if (!scs::read_position(board::kYawId, &yaw_now) ||
      !scs::read_position(board::kPitchId, &pitch_now)) {
    printf("bench: refused — a servo did not answer\n");
    return;
  }

  // ⚠️ Same arming rule as the other bench movers: both goals sit on the present
  //    positions before torque comes on, so nothing drives to a stale goal.
  scs::write_position(board::kYawId, yaw_now, 0, 0);
  scs::write_position(board::kPitchId, pitch_now, 0, 0);
  scs::set_torque(board::kYawId, true);
  scs::set_torque(board::kPitchId, true);
  vTaskDelay(pdMS_TO_TICKS(200));

  const int yaw_target = Clamp(RawFromAngle(g_yaw_zero, yaw_tenths),
                               board::kRawMin, board::kRawMax);
  const int pitch_target = Clamp(RawFromAngle(g_pitch_zero, pitch_tenths),
                                 board::kRawMin, board::kRawMax);
  const unsigned short sp = static_cast<unsigned short>(speed & 0xFFFF);
  const bool wrote_yaw = scs::write_position(board::kYawId, yaw_target, 0, sp);
  const bool wrote_pitch = scs::write_position(board::kPitchId, pitch_target, 0, sp);
  printf("bench: set -> raw yaw=%d pitch=%d, speed=%d\n", yaw_target,
         pitch_target, speed);
  if (!wrote_yaw || !wrote_pitch) {
    printf("bench: the write failed\n");
  }

  int last_yaw = yaw_now;
  int last_pitch = pitch_now;
  int same = 0;
  for (int i = 0; i < 75; ++i) {  // 15 s to arrive and settle, then hold
    vTaskDelay(pdMS_TO_TICKS(200));
    int y = -1;
    int p2 = -1;
    if (!scs::read_position(board::kYawId, &y) ||
        !scs::read_position(board::kPitchId, &p2)) {
      continue;
    }
    same = (y == last_yaw && p2 == last_pitch) ? same + 1 : 0;
    last_yaw = y;
    last_pitch = p2;
    if (same >= 5) {
      break;
    }
  }
  printf("bench: held at raw yaw=%d pitch=%d — torque on\n", last_yaw, last_pitch);
  printf("bench: done\n");
}

// --- the gesture -> angle table, measured 2026-10-18 -------------------------
// ⛔ Until this table existed, every gesture a frame carried was refused,
//    because a guessed angle is indistinguishable from a measured one in the
//    source. These five postures were placed with `bench set` and judged with
//    the author's eye, one at a time. The record is
//    projects/stackchan-firmware/records/2026-10-18-the-gestures.md.
// ⚠️ A posture is (yaw, pitch) in 0.1 degrees. The raw positions each one held
//    are beside it, because the angle that was sent and the position the servo
//    settled at are not the same number — every held read-back was a few counts
//    off, in both directions.
struct GesturePosture {
  int yaw_tenths;
  int pitch_tenths;
};

constexpr GesturePosture kLookUpPosture = {80, 500};     // held raw 491 / 778
constexpr GesturePosture kLookSidePosture = {350, 500};    // held raw 566 / 778
constexpr GesturePosture kRestPosture = {0, 30};     // held raw 466 / 630
constexpr GesturePosture kNodDownPosture = {80, 30};   // held raw 478 / 630
constexpr GesturePosture kRecoilPosture = {-80, 700};  // held raw 442 / 842

// ⚠️ The speed is the one the postures were measured at. ⛔ It is not a
//    trajectory: nothing interpolates upstream of the wire, so this drives the
//    neck from wherever it is to one posture and lets the servo's own speed
//    field do the rest.
constexpr int kGestureSpeed = 80;

// Waits until both positions stop changing, or the budget runs out.
void WaitSettled(int max_ticks) {
  int last_yaw = -1;
  int last_pitch = -1;
  int same = 0;
  for (int i = 0; i < max_ticks; ++i) {
    vTaskDelay(pdMS_TO_TICKS(100));
    int yaw = -1;
    int pitch = -1;
    if (!scs::read_position(board::kYawId, &yaw) ||
        !scs::read_position(board::kPitchId, &pitch)) {
      continue;
    }
    same = (yaw == last_yaw && pitch == last_pitch) ? same + 1 : 0;
    last_yaw = yaw;
    last_pitch = pitch;
    if (same >= 3) {
      return;
    }
  }
}

// Arms both goals on the present positions, then drives to one posture.
bool MoveToPosture(const GesturePosture& posture) {
  int yaw_now = -1;
  int pitch_now = -1;
  if (!scs::read_position(board::kYawId, &yaw_now) ||
      !scs::read_position(board::kPitchId, &pitch_now)) {
    return false;
  }
  // ⚠️ Same arming rule as the bench movers: the goals sit on the present
  //    positions before torque comes on, so nothing drives to a stale goal.
  scs::write_position(board::kYawId, yaw_now, 0, 0);
  scs::write_position(board::kPitchId, pitch_now, 0, 0);
  scs::set_torque(board::kYawId, true);
  scs::set_torque(board::kPitchId, true);
  vTaskDelay(pdMS_TO_TICKS(200));

  const int yaw_raw = Clamp(RawFromAngle(g_yaw_zero, posture.yaw_tenths),
                            board::kRawMin, board::kRawMax);
  const int pitch_raw = Clamp(RawFromAngle(g_pitch_zero, posture.pitch_tenths),
                              board::kRawMin, board::kRawMax);
  const unsigned short sp = static_cast<unsigned short>(kGestureSpeed);
  return scs::write_position(board::kYawId, yaw_raw, 0, sp) &&
         scs::write_position(board::kPitchId, pitch_raw, 0, sp);
}

// ⚠️ A gesture is one posture, except `nod`: it was measured as a down point
//    and a place to come back to, and the place it comes back to is the posture
//    the down point was measured from.
void PlayGesture(Gesture gesture) {
  if (!g_servos_ready) {
    printf("frame: gesture %s refused — the servo bus did not come up\n",
           GestureName(gesture));
    return;
  }
  bool wrote = false;
  switch (gesture) {
    case Gesture::kLookUp:
      wrote = MoveToPosture(kLookUpPosture);
      break;
    case Gesture::kLookSide:
      wrote = MoveToPosture(kLookSidePosture);
      break;
    case Gesture::kRest:
      wrote = MoveToPosture(kRestPosture);
      break;
    case Gesture::kRecoil:
      wrote = MoveToPosture(kRecoilPosture);
      break;
    case Gesture::kNod:
      wrote = MoveToPosture(kNodDownPosture);
      WaitSettled(20);
      wrote = MoveToPosture(kLookUpPosture) && wrote;
      break;
    case Gesture::kNone:
      return;
  }
  WaitSettled(30);
  int yaw = -1;
  int pitch = -1;
  if (!wrote) {
    printf("frame: gesture %s — the write failed\n", GestureName(gesture));
    return;
  }
  if (scs::read_position(board::kYawId, &yaw) &&
      scs::read_position(board::kPitchId, &pitch)) {
    printf("frame: gesture %s -> raw yaw=%d pitch=%d (measured posture)\n",
           GestureName(gesture), yaw, pitch);
  }
}

// ⚠️ A bus scan, not a guess. `pitch = no answer` says only that id 2 is quiet;
//    this says which ids are not quiet, and that is what decides whether the
//    servo is missing, renumbered, or the bus itself is half there.
void BenchScan() {
  printf("bench: scanning ids 1..12 at %d baud\n", board::kServoBaud);
  int found = 0;
  for (int id = 1; id <= 12; ++id) {
    int answered = 0;
    for (int attempt = 0; attempt < 2; ++attempt) {
      if (scs::ping(id)) {
        ++answered;
      }
      vTaskDelay(pdMS_TO_TICKS(30));
    }
    if (answered > 0) {
      printf("bench: id %d answered %d/2\n", id, answered);
      ++found;
    }
  }
  printf("bench: scan done, %d id(s) answered\n", found);
}

void BenchRead(int id) {
  int raw = -1;
  if (scs::read_position(id, &raw)) {
    printf("bench: id %d raw %d\n", id, raw);
  } else {
    printf("bench: id %d no answer\n", id);
  }
}

void BenchHold() {
  int yaw = -1;
  int pitch = -1;
  if (!scs::read_position(board::kYawId, &yaw) ||
      !scs::read_position(board::kPitchId, &pitch)) {
    printf("bench: refused — a servo did not answer\n");
    return;
  }
  scs::write_position(board::kYawId, yaw, 0, 0);
  scs::write_position(board::kPitchId, pitch, 0, 0);
  scs::set_torque(board::kYawId, true);
  scs::set_torque(board::kPitchId, true);
  printf("bench: holding the present positions (yaw %d, pitch %d)\n", yaw, pitch);
}

void BenchRelease() {
  scs::set_torque(board::kYawId, false);
  scs::set_torque(board::kPitchId, false);
  printf("bench: torque released — the head is limp\n");
}

void HandleBench(const char* args) {
  // ⛔ A `bench` command blocks this task for seconds, and every pose that
  //    arrives while it runs is read late. A pose that arrives late is not a
  //    pose. The stream has to be silent for 500 ms before the bench is usable.
  if (g_streaming) {
    printf("bench: refused — a pose stream is running; wait for 500 ms of silence\n");
    return;
  }
  while (*args == ' ') {
    ++args;
  }

  if (std::strncmp(args, "pos", 3) == 0) {
    BenchPos();
    return;
  }
  if (std::strncmp(args, "zeros", 5) == 0) {
    printf("bench: zeros yaw=%d pitch=%d (%s)\n", g_yaw_zero, g_pitch_zero,
           g_zeros_from_nvs ? "from this unit's NVS" : "VENDOR DEFAULTS — not measured here");
    return;
  }
  if (std::strncmp(args, "scan", 4) == 0) {
    BenchScan();
    return;
  }
  if (std::strncmp(args, "read", 4) == 0) {
    char* end = nullptr;
    const long id = std::strtol(args + 4, &end, 10);
    if (end == args + 4) {
      printf("bench: read needs an id\n");
      return;
    }
    BenchRead(static_cast<int>(id));
    return;
  }
  if (std::strncmp(args, "hold", 4) == 0) {
    BenchHold();
    return;
  }
  if (std::strncmp(args, "release", 7) == 0) {
    BenchRelease();
    return;
  }
  if (std::strncmp(args, "leds", 4) == 0) {
    // ⚠️ Reads the expander back, then writes full red to all twelve. Neither
    //    answer is a claim: the registers say what the expander holds, and only
    //    the eye says whether a pixel is lit.
    leds::probe();
    printf("bench: twelve set to full red — if nothing is lit, say so; the registers above still count\n");
    return;
  }
  if (std::strncmp(args, "power", 5) == 0) {
    const char* value = args + 5;
    while (*value == ' ') {
      ++value;
    }
    if (std::strncmp(value, "off", 3) == 0) {
      leds::servo_power(false);
      printf("bench: servo power OFF — the head is limp\n");
    } else if (std::strncmp(value, "on", 2) == 0) {
      leds::servo_power(true);
      printf("bench: servo power ON — the head holds nothing until a goal is written\n");
    } else {
      printf("bench: power needs `on` or `off`\n");
    }
    return;
  }
  if (std::strncmp(args, "timed", 5) == 0) {
    const char* cursor = args + 5;
    int yaw_tenths = 0;
    if (!ParseDegrees(&cursor, &yaw_tenths)) {
      printf("bench: timed needs a yaw angle in degrees\n");
      return;
    }
    char* end = nullptr;
    const long time_field = std::strtol(cursor, &end, 10);
    if (end == cursor) {
      printf("bench: timed needs a time field after the angle\n");
      return;
    }
    cursor = end;
    long speed = 0;
    const long parsed_speed = std::strtol(cursor, &end, 10);
    if (end != cursor) {
      speed = parsed_speed;
    }
    BenchTimed(yaw_tenths, static_cast<int>(time_field), static_cast<int>(speed));
    return;
  }
  // ⚠️ `set`, not `pose`: `pos` is three characters and its check runs first,
  //    so any subcommand starting with `pos` is read as `bench pos`.
  if (std::strncmp(args, "set", 3) == 0) {
    const char* cursor = args + 4;
    int yaw_tenths = 0;
    int pitch_tenths = 0;
    if (!ParseDegrees(&cursor, &yaw_tenths) ||
        !ParseDegrees(&cursor, &pitch_tenths)) {
      printf("bench: set needs a yaw angle and a pitch angle in degrees\n");
      return;
    }
    char* end = nullptr;
    long speed = 100;
    const long parsed_speed = std::strtol(cursor, &end, 10);
    if (end != cursor) {
      speed = parsed_speed;
    }
    BenchSet(yaw_tenths, pitch_tenths, static_cast<int>(speed));
    return;
  }
  if (std::strncmp(args, "move", 4) == 0) {
    const char* cursor = args + 4;
    int yaw_tenths = 0;
    int pitch_tenths = 0;
    if (!ParseDegrees(&cursor, &yaw_tenths)) {
      printf("bench: move needs a yaw angle in degrees\n");
      return;
    }
    const bool has_pitch = ParseDegrees(&cursor, &pitch_tenths);
    BenchMove(yaw_tenths, has_pitch, pitch_tenths);
    return;
  }

  printf("bench: unknown subcommand (try `help`)\n");
}

// --- the pose line --------------------------------------------------------
//
// ⚠️ One pose per tick, from a host that is interpolating. This end does not
//    smooth, ease or plan: it applies what it is told, and the only thing it
//    decides is what to do when the host stops. That decision is torque off.
//
// ⛔ Violations are refused per line, but printed once per code per stream.
//    A print per refused pose would flood the console at 50 Hz and bury the one
//    line that matters — the one that says the stream was lost.

unsigned int PoseCodeBit(const char* code) {
  if (std::strcmp(code, "malformed") == 0) return 1u << 0;
  if (std::strcmp(code, "bad-checksum") == 0) return 1u << 1;
  if (std::strcmp(code, "out-of-range") == 0) return 1u << 2;
  if (std::strcmp(code, "no-answer") == 0) return 1u << 3;
  if (std::strcmp(code, "no-bus") == 0) return 1u << 4;
  if (std::strcmp(code, "write-failed") == 0) return 1u << 5;
  if (std::strcmp(code, "too-long") == 0) return 1u << 6;
  return 1u << 8;
}

void PoseRefuse(const char* code) {
  ++g_pose_refused;
  const unsigned int bit = PoseCodeBit(code);
  if ((g_pose_codes & bit) != 0) {
    return;
  }
  g_pose_codes |= bit;
  printf("pose: refused (%s)\n", code);
}

enum class TenthsResult { kOk, kMalformed, kOutOfRange };

// ⚠️ The same rules as the Python decoder: one leading sign, one to four digits,
//    and one canonical spelling. ⛔ `05` and `-0` are refused here for the same
//    reason they are refused there — the sum cannot see a transposition, so the
//    spelling is pinned to leave the checksum fewer ways to be fooled.
TenthsResult ParseTenths(const char* text, int length, int* out) {
  if (length <= 0 || length > 4) {
    return TenthsResult::kMalformed;
  }
  int i = 0;
  bool negative = false;
  if (text[0] == '-') {
    negative = true;
    i = 1;
  }
  if (i >= length) {
    return TenthsResult::kMalformed;
  }
  int value = 0;
  for (; i < length; ++i) {
    if (text[i] < '0' || text[i] > '9') {
      return TenthsResult::kMalformed;
    }
    value = value * 10 + (text[i] - '0');
  }
  if (negative) {
    if (value == 0) {
      return TenthsResult::kMalformed;  // "-0" is a second spelling of 0
    }
    value = -value;
  } else if (length > 1 && text[0] == '0') {
    return TenthsResult::kMalformed;  // "05" is a second spelling of 5
  }
  if (value < -kPoseMaxTenths || value > kPoseMaxTenths) {
    return TenthsResult::kOutOfRange;
  }
  *out = value;
  return TenthsResult::kOk;
}

int PoseChecksum(const char* body, int length) {
  int sum = 0;
  for (int i = 0; i < length; ++i) {
    sum += static_cast<unsigned char>(body[i]);
  }
  return sum & 0xFF;
}

void HandlePose(const char* line, int length) {
  if (length > kPoseMaxLine) {
    PoseRefuse("too-long");
    return;
  }
  int star = -1;
  for (int i = length - 1; i >= 0; --i) {
    if (line[i] == '*') {
      star = i;
      break;
    }
  }
  if (star < 0 || length - star != 3) {
    PoseRefuse("malformed");
    return;
  }

  char expected[3];
  std::snprintf(expected, sizeof expected, "%02X", PoseChecksum(line, star));
  if (line[star + 1] != expected[0] || line[star + 2] != expected[1]) {
    PoseRefuse("bad-checksum");
    return;
  }

  // "pose" is at 0..3 and the first space at 4 — Dispatch checked that. What is
  // left is exactly one space between the two fields, and no third.
  int space = -1;
  for (int i = 5; i < star; ++i) {
    if (line[i] == ' ') {
      if (space >= 0) {
        PoseRefuse("malformed");
        return;
      }
      space = i;
    }
  }
  if (space < 0) {
    PoseRefuse("malformed");
    return;
  }

  int yaw = 0;
  int pitch = 0;
  const TenthsResult yaw_result = ParseTenths(line + 5, space - 5, &yaw);
  const TenthsResult pitch_result = ParseTenths(line + space + 1, star - space - 1, &pitch);
  if (yaw_result == TenthsResult::kMalformed || pitch_result == TenthsResult::kMalformed) {
    PoseRefuse("malformed");
    return;
  }
  if (yaw_result == TenthsResult::kOutOfRange || pitch_result == TenthsResult::kOutOfRange) {
    PoseRefuse("out-of-range");
    return;
  }

  // ⛔ Clamped against THIS machine's numbers, not the protocol's. The host does
  //    not know these limits from the wire; the board is the only end that does.
  const int yaw_wanted = yaw;
  const int pitch_wanted = pitch;
  if (yaw > board::kYawAngleLimitTenths) yaw = board::kYawAngleLimitTenths;
  if (yaw < -board::kYawAngleLimitTenths) yaw = -board::kYawAngleLimitTenths;
  pitch = Clamp(pitch, board::kPitchAngleMinTenths, board::kPitchAngleMaxTenths);
  if (yaw != yaw_wanted || pitch != pitch_wanted) {
    ++g_pose_clamped;
    if ((g_pose_codes & (1u << 7)) == 0) {
      g_pose_codes |= 1u << 7;
      printf("pose: clamped to this machine's limits (yaw +/-%d.%d, pitch %d.%d..%d.%d deg)\n",
             board::kYawAngleLimitTenths / 10, board::kYawAngleLimitTenths % 10,
             board::kPitchAngleMinTenths / 10, board::kPitchAngleMinTenths % 10,
             board::kPitchAngleMaxTenths / 10, board::kPitchAngleMaxTenths % 10);
    }
  }

  if (!g_streaming) {
    if (!g_servos_ready) {
      PoseRefuse("no-bus");
      return;
    }
    int yaw_now = -1;
    int pitch_now = -1;
    if (!scs::read_position(board::kYawId, &yaw_now) ||
        !scs::read_position(board::kPitchId, &pitch_now)) {
      PoseRefuse("no-answer");
      return;
    }
    // ⚠️ The same rule as the bench: both goals sit on the present positions
    //    before torque comes on, so the first pose is a move and not a jump.
    scs::write_position(board::kYawId, yaw_now, 0, 0);
    scs::write_position(board::kPitchId, pitch_now, 0, 0);
    scs::set_torque(board::kYawId, true);
    scs::set_torque(board::kPitchId, true);
    vTaskDelay(pdMS_TO_TICKS(200));
    g_streaming = true;
    g_pose_codes = 0;
    g_pose_count = 0;
    g_pose_refused = 0;
    g_pose_clamped = 0;
    g_last_pose_us = esp_timer_get_time();
    printf("pose: stream started — goals on the present positions (yaw %d, pitch %d), torque on\n",
           yaw_now, pitch_now);
  }

  const int yaw_raw = Clamp(RawFromAngle(g_yaw_zero, yaw), board::kRawMin, board::kRawMax);
  const int pitch_raw = Clamp(RawFromAngle(g_pitch_zero, pitch), board::kRawMin, board::kRawMax);
  const bool written = scs::write_position(board::kYawId, yaw_raw, 0, kPoseSpeed) &&
                       scs::write_position(board::kPitchId, pitch_raw, 0, kPoseSpeed);
  if (!written) {
    // ⚠️ The clock is not advanced. A failed write is silence, and silence is
    //    what the watchdog is for.
    PoseRefuse("write-failed");
    return;
  }
  g_last_pose_us = esp_timer_get_time();
  ++g_pose_count;
}

// ⚠️ Called from the main loop, which is the only task that is never blocked.
//    ⛔ "The machine stopped" is not what this says, and not what it means: the
//    torque is released, and a released servo is limp, not stopped.
void PoseWatchdog() {
  if (!g_streaming) {
    return;
  }
  if (esp_timer_get_time() - g_last_pose_us < kPoseSilenceUs) {
    return;
  }
  g_streaming = false;
  scs::set_torque(board::kYawId, false);
  scs::set_torque(board::kPitchId, false);
  printf("pose: stream lost after 500 ms — torque released\n");
  printf("pose: %d applied, %d refused, %d clamped\n", g_pose_count, g_pose_refused,
         g_pose_clamped);
}

void HandleFrame(const char* line, int length) {
  Command command;
  const ParseResult result = parse_command(line, length, &command);
  if (result != ParseResult::kOk) {
    printf("frame: refused (%s)\n", ParseResultName(result));
    return;
  }

  leds::set_light(command.light);
  printf("frame: light=%s face=%s%s\n", LightName(command.light), FaceName(command.face),
         command.face == Face::kNone ? "" : " (no renderer yet)");

  if (command.gesture != Gesture::kNone) {
    PlayGesture(command.gesture);
  }
}

void Dispatch(const char* line, int length) {
  if (length <= 0) {
    return;
  }
  if (line[0] == '{') {
    HandleFrame(line, length);
    return;
  }
  if (std::strncmp(line, "pose ", 5) == 0) {
    HandlePose(line, length);
    return;
  }
  if (std::strncmp(line, "bench", 5) == 0 && (length == 5 || line[5] == ' ')) {
    HandleBench(line + 5);
    return;
  }
  if (std::strncmp(line, "help", 4) == 0) {
    PrintHelp();
    return;
  }
  printf("console: unknown command (try `help`)\n");
}

// ⚠️ A beacon, not a feature. The first two flashes ran and said nothing, and
//    silence from a console is indistinguishable from a console that was never
//    reached. This prints whether or not anything is typed, so that "the app is
//    running" becomes an observation instead of an assumption.
void HeartbeatTask(void*) {
  while (true) {
    vTaskDelay(pdMS_TO_TICKS(3000));
    printf("alive\n");
  }
}

// ⛔ The console reads in its own task, and every attempt is followed by a
//    delay whether or not bytes arrived. Two builds before this one did it
//    in `app_main`: the first with `fgets`, which blocked and never let the
//    idle task run; the second with `select`, which the USB Serial/JTAG VFS
//    does not implement — that one spun, starved IDLE0, and reset the chip
//    faster than anything could be typed into it. A delay after each read
//    makes the loop incapable of starving anyone.
void ConsoleTask(void*) {
  while (true) {
    char chunk[32];
    const int got = static_cast<int>(read(STDIN_FILENO, chunk, sizeof(chunk)));
    if (got <= 0) {
      vTaskDelay(pdMS_TO_TICKS(50));
      continue;
    }
    for (int i = 0; i < got; ++i) {
      const char c = chunk[i];
      if (c == '\r') {
        continue;
      }
      if (c == '\n') {
        if (g_line_len > 0) {
          g_line[g_line_len] = '\0';
          Dispatch(g_line, g_line_len);
          g_line_len = 0;
        }
        continue;
      }
      if (g_line_len < kMaxLine) {
        g_line[g_line_len++] = c;
      } else {
        printf("console: line too long, dropped\n");
        g_line_len = 0;
      }
    }
  }
}

int PingCount(int id) {
  int answered = 0;
  for (int attempt = 0; attempt < 3; ++attempt) {
    if (scs::ping(id)) {
      ++answered;
    }
    vTaskDelay(pdMS_TO_TICKS(100));
  }
  return answered;
}

}  // namespace

extern "C" void app_main() {
  // ⚠️ This bypasses the VFS, the driver and every lock above them: it is the
  //    ROM writing the character itself. If this line does not appear, the app
  //    never reached app_main and no amount of console work will help.
  esp_rom_printf("\nprobe: app_main entered\n");

  setvbuf(stdout, nullptr, _IONBF, 0);

  // ⚠️ The first line is printed before anything else can fail, so that a boot
  //    that stops has a last line to point at. Two builds before this one ran and
  //    printed nothing; silence said only that something was wrong, never what.
  printf("\nstackchan-vessel — the device end of the wire\n");
  printf("built %s %s\n", __DATE__, __TIME__);

  // ⚠️ The console is the VFS console the ESP-IDF startup already installed for
  //    USB Serial/JTAG — the same path the vendor's firmware uses. ⛔ An earlier
  //    build installed the raw driver on top of it; that build enumerated,
  //    answered nothing, and could not be reset into download mode. The supported
  //    path costs a blocking read, and it is the one that talks.
  vTaskDelay(pdMS_TO_TICKS(500));
  printf("waypoint: console\n");

  // ⚠️ A no-op unless the bootloader on flash has rollback enabled. The unit in
  //    hand boots the vendor's bootloader, which does.
  esp_ota_mark_app_valid_cancel_rollback();
  printf("waypoint: ota marked valid\n");

  xTaskCreate(HeartbeatTask, "beat", 3072, nullptr, 1, nullptr);

  if (!leds::begin()) {
    printf("leds: the IO expander did not answer — no LEDs, no servo power\n");
  } else {
    leds::set_light(Light::kDim);
  }

  if (!zeros::read(&g_yaw_zero, &g_pitch_zero, &g_zeros_from_nvs)) {
    printf("zeros: NO ANSWER FROM NVS — using the vendor's defaults %d / %d\n",
           board::kYawZeroDefault, board::kPitchZeroDefault);
    printf("zeros: ⛔ these were not measured on this unit\n");
  } else {
    printf("zeros: yaw=%d pitch=%d, from this unit's NVS\n", g_yaw_zero, g_pitch_zero);
  }

  if (!scs::begin()) {
    printf("servo: the UART did not come up\n");
  } else {
    // ⚠️ Counted, not sampled. Three tries each, 100 ms apart: one missing reply
    //    is a race, three is a servo that is not there.
    const int yaw_ping = PingCount(board::kYawId);
    const int pitch_ping = PingCount(board::kPitchId);
    printf("servo: ping yaw=%d/3 pitch=%d/3\n", yaw_ping, pitch_ping);

    int yaw = -1;
    int pitch = -1;
    if (scs::read_position(board::kYawId, &yaw) &&
        scs::read_position(board::kPitchId, &pitch)) {
      // ⛔ The goals are set to the positions the servos are already in, so that
      //    nothing moves when torque is applied.
      scs::write_position(board::kYawId, yaw, 0, 0);
      scs::write_position(board::kPitchId, pitch, 0, 0);
      // ⚠️ Torque off at rest, as the vendor's motion layer does. The goals are
      //    already the present positions, so the move that comes later starts
      //    from a known place.
      scs::set_torque(board::kYawId, false);
      scs::set_torque(board::kPitchId, false);
      g_servos_ready = true;
      printf("servo: present yaw=%d pitch=%d; goals set; torque off; ready\n", yaw, pitch);
    } else {
      printf("servo: a position did not read — nothing will move\n");
    }
  }

  printf("\nready. type `help`.\n");
  printf("⚠️ this firmware does not move at boot. nothing moves until a line arrives.\n\n");

  // ⛔ The console lives in its own task now. `app_main` keeps only the
  //    animation, the pose watchdog and a delay, so no path in this file can
  //    spin. ⚠️ The watchdog is here and not in the console task because the
  //    console's read blocks: a task blocked in `read` cannot notice that its
  //    stream has gone quiet.
  xTaskCreate(ConsoleTask, "console", 4096, nullptr, 2, nullptr);
  while (true) {
    leds::tick();
    PoseWatchdog();
    vTaskDelay(pdMS_TO_TICKS(20));
  }
}
