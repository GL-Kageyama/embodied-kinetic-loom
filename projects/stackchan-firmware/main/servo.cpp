#include "servo.h"

#include "driver/uart.h"
#include "freertos/FreeRTOS.h"

#include "board.h"

namespace {

constexpr unsigned char kInstPing = 0x01;
constexpr unsigned char kInstRead = 0x02;
constexpr unsigned char kInstWrite = 0x03;
constexpr unsigned char kTorqueEnable = 40;      // SCSCL_TORQUE_ENABLE
constexpr unsigned char kGoalPositionL = 42;     // SCSCL_GOAL_POSITION_L
constexpr unsigned char kPresentPositionL = 56;  // SCSCL_PRESENT_POSITION_L

uart_port_t Port() { return static_cast<uart_port_t>(board::kServoUart); }

unsigned char Checksum(const unsigned char* bytes, int n) {
  unsigned short sum = 0;
  for (int i = 0; i < n; ++i) {
    sum += bytes[i];
  }
  return static_cast<unsigned char>(~sum);
}

}  // namespace

bool scs::begin() {
  uart_config_t cfg = {};
  cfg.baud_rate = board::kServoBaud;
  cfg.data_bits = UART_DATA_8_BITS;
  cfg.parity = UART_PARITY_DISABLE;
  cfg.stop_bits = UART_STOP_BITS_1;
  cfg.flow_ctrl = UART_HW_FLOWCTRL_DISABLE;
  cfg.rx_flow_ctrl_thresh = 0;
  cfg.source_clk = UART_SCLK_DEFAULT;

  const esp_err_t installed = uart_driver_install(Port(), 512, 512, 0, nullptr, 0);
  if (installed != ESP_OK && installed != ESP_ERR_INVALID_STATE) {
    return false;
  }
  if (uart_param_config(Port(), &cfg) != ESP_OK) {
    return false;
  }
  if (uart_set_pin(Port(), board::kServoTx, board::kServoRx, UART_PIN_NO_CHANGE,
                   UART_PIN_NO_CHANGE) != ESP_OK) {
    return false;
  }
  return true;
}

bool scs::write_position(int id, int raw, unsigned short time_ms, unsigned short speed) {
  if (raw < board::kRawMin) {
    raw = board::kRawMin;
  }
  if (raw > board::kRawMax) {
    raw = board::kRawMax;
  }

  unsigned char packet[13];
  packet[0] = 0xFF;
  packet[1] = 0xFF;
  packet[2] = static_cast<unsigned char>(id);
  packet[3] = 9;  // 2 + 6 data bytes + 1 address
  packet[4] = kInstWrite;
  packet[5] = kGoalPositionL;
  // ⚠️ High byte first, for all three words. The vendor's SCSCL driver is
  //    constructed with `End = 1` (`SCSCL::SCSCL() { End = 1; }`), and its
  //    `Host2SCS` writes `Data >> 8` into the first byte. Measured on this
  //    unit: a present position of 604 came back as 0x02, 0x5C. ⛔ A low-first
  //    write sends 604 as 0x02, 0x5C, which the servo reads as 23554 — a value
  //    it cannot reach, and one it would chase.
  packet[6] = static_cast<unsigned char>((raw >> 8) & 0xFF);
  packet[7] = static_cast<unsigned char>(raw & 0xFF);
  packet[8] = static_cast<unsigned char>((time_ms >> 8) & 0xFF);
  packet[9] = static_cast<unsigned char>(time_ms & 0xFF);
  packet[10] = static_cast<unsigned char>((speed >> 8) & 0xFF);
  packet[11] = static_cast<unsigned char>(speed & 0xFF);
  packet[12] = Checksum(packet + 2, 10);

  const int sent = uart_write_bytes(Port(), packet, sizeof(packet));
  if (sent != static_cast<int>(sizeof(packet))) {
    return false;
  }
  uart_wait_tx_done(Port(), pdMS_TO_TICKS(100));
  return true;
}

bool scs::read_position(int id, int* out_raw) {
  if (out_raw == nullptr) {
    return false;
  }

  unsigned char request[8];
  request[0] = 0xFF;
  request[1] = 0xFF;
  request[2] = static_cast<unsigned char>(id);
  request[3] = 4;  // 2 + 1 data byte count + 1 address
  request[4] = kInstRead;
  request[5] = kPresentPositionL;
  request[6] = 2;  // two bytes wanted
  request[7] = Checksum(request + 2, 5);

  uart_flush_input(Port());
  if (uart_write_bytes(Port(), request, sizeof(request)) != static_cast<int>(sizeof(request))) {
    return false;
  }
  uart_wait_tx_done(Port(), pdMS_TO_TICKS(100));

  unsigned char reply[16];
  const int read = uart_read_bytes(Port(), reply, sizeof(reply), pdMS_TO_TICKS(100));
  if (read < 7) {
    return false;
  }

  // The bus is dedicated, but a late reply from an earlier command can still be
  // in the buffer. Find the header rather than assuming byte zero.
  int start = -1;
  for (int i = 0; i + 1 < read; ++i) {
    if (reply[i] == 0xFF && reply[i + 1] == 0xFF) {
      start = i;
      break;
    }
  }
  if (start < 0 || start + 7 > read) {
    return false;
  }

  const unsigned char* packet = reply + start + 2;  // ID, LEN, STATUS, D0, D1, CS
  if (packet[0] != static_cast<unsigned char>(id)) {
    return false;
  }
  if (packet[1] != 4) {  // status + two data bytes
    return false;
  }
  if (packet[2] != 0) {  // the servo's own error byte
    return false;
  }
  if (Checksum(packet, 5) != packet[5]) {
    return false;
  }

  // ⚠️ High byte first — see the note in `write_position`. This read is what
  //    caught it: 604 arrived as 0x02, 0x5C and parsed as 23554.
  *out_raw = (static_cast<int>(packet[3]) << 8) | packet[4];
  return true;
}

bool scs::set_torque(int id, bool enabled) {
  unsigned char packet[8];
  packet[0] = 0xFF;
  packet[1] = 0xFF;
  packet[2] = static_cast<unsigned char>(id);
  packet[3] = 4;  // 2 + 1 data byte + 1 address
  packet[4] = kInstWrite;
  packet[5] = kTorqueEnable;
  packet[6] = enabled ? 1 : 0;
  packet[7] = Checksum(packet + 2, 5);

  const int sent = uart_write_bytes(Port(), packet, sizeof(packet));
  if (sent != static_cast<int>(sizeof(packet))) {
    return false;
  }
  uart_wait_tx_done(Port(), pdMS_TO_TICKS(100));
  return true;
}

bool scs::ping(int id) {
  unsigned char request[6];
  request[0] = 0xFF;
  request[1] = 0xFF;
  request[2] = static_cast<unsigned char>(id);
  request[3] = 2;
  // ⚠️ Three bytes, not four. A ping carries no parameters, so the checksum
  //    covers ID + LEN + INST and stops. The first build summed four and read
  //    the unwritten checksum byte as part of its own input — every ping was
  //    malformed and every servo ignored it, which read on screen as "no servo
  //    answers" while `read` on the same id worked.
  request[4] = kInstPing;
  request[5] = Checksum(request + 2, 3);

  uart_flush_input(Port());
  if (uart_write_bytes(Port(), request, sizeof(request)) != static_cast<int>(sizeof(request))) {
    return false;
  }
  uart_wait_tx_done(Port(), pdMS_TO_TICKS(100));

  unsigned char reply[8];
  const int read = uart_read_bytes(Port(), reply, sizeof(reply), pdMS_TO_TICKS(100));
  if (read < 6) {
    return false;
  }
  // ⚠️ Eight bytes are read and six are the packet, so a reply to an earlier
  //    command can be in front of it. Find the header, then check that the id
  //    and the length are the ones this ping asked for.
  for (int i = 0; i + 5 < read; ++i) {
    if (reply[i] == 0xFF && reply[i + 1] == 0xFF &&
        reply[i + 2] == static_cast<unsigned char>(id) && reply[i + 3] == 2) {
      return true;
    }
  }
  return false;
}
