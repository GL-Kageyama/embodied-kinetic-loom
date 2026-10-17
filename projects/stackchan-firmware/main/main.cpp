// Stack-chan — the device end of the wire, on the unit in hand.
//
// ⛔ What this firmware does NOT do:
//   - it has no gesture -> angle table, so every `gesture` in a frame is refused;
//   - it has no display renderer, so a `face` is logged as a meaning, not drawn;
//   - it does not move at boot, and it does not move unless a person types.
//
// ✅ What it does:
//   - reads the two zero positions out of this unit's NVS (the wizard's
//     measurement), or says loudly that it fell back to the vendor's defaults;
//   - lights twelve LEDs for the contract's `light` word;
//   - answers `bench` commands from the USB Serial/JTAG console, which is how the
//     first arrival is meant to be watched: one person types, one head turns.
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
    case Gesture::kPerk: return "perk";
    case Gesture::kNod: return "nod";
    case Gesture::kTurn: return "turn";
    case Gesture::kSettle: return "settle";
    case Gesture::kFlinch: return "flinch";
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
  printf("  bench pos                 present positions\n");
  printf("  bench scan                which servo ids answer, 1..12\n");
  printf("  bench read <id>           raw position of one id\n");
  printf("  bench zeros               the zeros this boot used, and where they came from\n");
  printf("  bench move <yaw_deg> [pitch_deg]   slow: about 1 degree per second\n");
  printf("  bench hold                hold the present positions (torque on)\n");
  printf("  bench release             torque off — the head goes limp\n");
  printf("  bench power on|off        the servo rail — the only stop this machine has\n");
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
    // ⛔ Not a placeholder for a missing line. It is the line, until the unit has
    //    been measured and a gesture -> angle table is written.
    printf("frame: gesture %s refused — no gesture -> angle table exists\n",
           GestureName(command.gesture));
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
  printf("⚠️ this firmware does not move at boot. nothing moves until a person types.\n\n");

  // ⛔ The console lives in its own task now. `app_main` keeps only the
  //    animation and a delay, so no path in this file can spin.
  xTaskCreate(ConsoleTask, "console", 4096, nullptr, 2, nullptr);
  while (true) {
    leds::tick();
    vTaskDelay(pdMS_TO_TICKS(20));
  }
}
