#include "dial.h"

#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "dial_policy.h"
#include "lwip/inet.h"
#include "lwip/sockets.h"
#include "nvs.h"

// ⛔ The body's one door, and the mirror of a line, both owned by `main.cpp`.
//    Declared here rather than in a shared header because nothing else may use
//    them: a task that called `Dispatch` directly would be the second writer
//    this file exists to avoid.
void RunLine(const char* line, int length);

namespace {

constexpr const char* kNvsNamespace = "ekl";
constexpr const char* kHostKey = "host";
constexpr const char* kPortKey = "port";

constexpr int kMaxLine = 256;        // the console's bound; a link line is a console line
constexpr int kSendWaitMs = 500;     // ⛔ a stalled socket must not stop a pose stream
constexpr int kConnectWaitMs = 3000;
constexpr int kPollMs = 100;
constexpr int kStackBytes = 4096;
constexpr uint32_t kMinBackoffMs = 1000;
constexpr uint32_t kMaxBackoffMs = 10000;
//: ⚠️ A connection that lived this long begins its backoff again from the
//:    short end. Without it, one bad hour leaves the board waiting ten seconds
//:    between attempts long after the network came back.
constexpr uint32_t kSettledMs = 5000;

char g_host[20] = {0};
int g_port = 0;
bool g_named = false;

int g_sock = -1;
bool g_up = false;
SemaphoreHandle_t g_send = nullptr;

uint32_t g_dials = 0;
uint32_t g_connects = 0;
uint32_t g_lines_in = 0;
uint32_t g_lines_out = 0;
uint32_t g_drops = 0;
uint32_t g_refused = 0;

// ⚠️ Bounded by `select`, never by `SO_SNDTIMEO`: the socket stays non-blocking
//    so that no wait here depends on an option being compiled into lwIP. The
//    repository has already paid once for a default it had not read.
bool WriteAll(int fd, const char* data, size_t length) {
  size_t sent = 0;
  const TickType_t deadline = xTaskGetTickCount() + pdMS_TO_TICKS(kSendWaitMs);
  while (sent < length) {
    const TickType_t now = xTaskGetTickCount();
    if (now >= deadline) {
      return false;
    }
    fd_set writable;
    FD_ZERO(&writable);
    FD_SET(fd, &writable);
    timeval wait;
    wait.tv_sec = 0;
    wait.tv_usec = static_cast<long>((deadline - now) * portTICK_PERIOD_MS) * 1000L;
    const int ready = select(fd + 1, nullptr, &writable, nullptr, &wait);
    if (ready <= 0) {
      return false;
    }
    const int wrote = ::send(fd, data + sent, length - sent, 0);
    if (wrote < 0) {
      if (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR) {
        continue;
      }
      return false;
    }
    if (wrote == 0) {
      return false;
    }
    sent += static_cast<size_t>(wrote);
  }
  return true;
}

// ⚠️ Non-blocking for the whole life of the socket, including the connect:
//    a `connect` to an address with nobody behind it can sit for a minute, and
//    this task must still be able to notice the stop flag of the build above it.
int Dial(const char* host, int port) {
  sockaddr_in address;
  std::memset(&address, 0, sizeof(address));
  address.sin_family = AF_INET;
  address.sin_port = htons(static_cast<uint16_t>(port));
  if (inet_aton(host, &address.sin_addr) == 0) {
    printf("dial: \"%s\" is not an address\n", host);
    return -1;
  }

  const int fd = socket(AF_INET, SOCK_STREAM, 0);
  if (fd < 0) {
    return -1;
  }
  const int flags = fcntl(fd, F_GETFL, 0);
  fcntl(fd, F_SETFL, flags | O_NONBLOCK);

  if (connect(fd, reinterpret_cast<sockaddr*>(&address), sizeof(address)) != 0) {
    if (errno != EINPROGRESS) {
      close(fd);
      return -1;
    }
    fd_set writable;
    FD_ZERO(&writable);
    FD_SET(fd, &writable);
    timeval wait;
    wait.tv_sec = kConnectWaitMs / 1000;
    wait.tv_usec = (kConnectWaitMs % 1000) * 1000L;
    if (select(fd + 1, nullptr, &writable, nullptr, &wait) <= 0) {
      close(fd);
      return -1;
    }
    int error = 0;
    socklen_t length = sizeof(error);
    if (getsockopt(fd, SOL_SOCKET, SO_ERROR, &error, &length) != 0 || error != 0) {
      close(fd);
      return -1;
    }
  }
  return fd;
}

void Take(const char* line, int length) {
  if (dial_policy::console_only(line)) {
    ++g_refused;
    // ⛔ Kept to this side's own console as well. A refusal that only the far
    //    end saw would leave whoever is holding the board guessing.
    const char* answer = "dial: refused — that command is the console's\n";
    printf("%s", answer);
    dial::say(answer);
    return;
  }
  RunLine(line, length);
}

// ⚠️ One reader, one line buffer, and the console's own splitting rules: `\r`
//    dropped anywhere, a line ends at `\n`, and an over-long line is dropped
//    whole rather than cut into two lines that each look valid.
void Service(int fd) {
  char line[kMaxLine + 1];
  int length = 0;
  char chunk[64];
  while (true) {
    fd_set readable;
    FD_ZERO(&readable);
    FD_SET(fd, &readable);
    timeval wait;
    wait.tv_sec = 0;
    wait.tv_usec = kPollMs * 1000L;
    const int ready = select(fd + 1, &readable, nullptr, nullptr, &wait);
    if (ready == 0) {
      continue;
    }
    if (ready < 0) {
      if (errno == EINTR) {
        continue;
      }
      return;
    }
    const int got = recv(fd, chunk, sizeof(chunk), 0);
    if (got == 0) {
      return;  // ⚠️ The host let go. Not an error, and not filled in either.
    }
    if (got < 0) {
      if (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR) {
        continue;
      }
      return;
    }
    for (int i = 0; i < got; ++i) {
      const char c = chunk[i];
      if (c == '\r') {
        continue;
      }
      if (c == '\n') {
        if (length > 0) {
          line[length] = '\0';
          ++g_lines_in;
          Take(line, length);
          length = 0;
        }
        continue;
      }
      if (length < kMaxLine) {
        line[length++] = c;
      } else {
        printf("dial: line too long, dropped\n");
        length = 0;
      }
    }
  }
}

void Publish(int fd, bool up) {
  if (g_send == nullptr) {
    g_sock = fd;
    g_up = up;
    return;
  }
  xSemaphoreTake(g_send, portMAX_DELAY);
  g_sock = fd;
  g_up = up;
  xSemaphoreGive(g_send);
}

void DialTask(void*) {
  uint32_t backoff = kMinBackoffMs;
  while (true) {
    char host[sizeof(g_host)];
    int port = 0;
    bool named = false;
    if (g_send != nullptr) {
      xSemaphoreTake(g_send, portMAX_DELAY);
      std::memcpy(host, g_host, sizeof(host));
      port = g_port;
      named = g_named;
      xSemaphoreGive(g_send);
    }
    if (!named) {
      vTaskDelay(pdMS_TO_TICKS(kPollMs * 5));
      continue;
    }

    ++g_dials;
    const int fd = Dial(host, port);
    if (fd < 0) {
      vTaskDelay(pdMS_TO_TICKS(backoff));
      backoff = (backoff * 2 > kMaxBackoffMs) ? kMaxBackoffMs : backoff * 2;
      continue;
    }

    Publish(fd, true);
    ++g_connects;
    printf("dial: connected to %s:%d\n", host, port);
    const TickType_t started = xTaskGetTickCount();

    Service(fd);

    Publish(-1, false);
    close(fd);
    printf("dial: the host let go\n");

    const uint32_t lived =
        static_cast<uint32_t>(xTaskGetTickCount() - started) * portTICK_PERIOD_MS;
    backoff = (lived >= kSettledMs) ? kMinBackoffMs
                                    : ((backoff * 2 > kMaxBackoffMs) ? kMaxBackoffMs
                                                                     : backoff * 2);
    vTaskDelay(pdMS_TO_TICKS(backoff));
  }
}

}  // namespace

void dial::begin() {
  g_send = xSemaphoreCreateMutex();

  // ⚠️ NVS is opened read-only and never erased — the same house rule
  //    `zeros.cpp` and `wifi.cpp` follow, and the same namespace they use.
  nvs_handle_t handle = 0;
  const esp_err_t opened = nvs_open(kNvsNamespace, NVS_READONLY, &handle);
  if (opened == ESP_OK) {
    size_t length = sizeof(g_host);
    uint16_t port = 0;
    if (nvs_get_str(handle, kHostKey, g_host, &length) == ESP_OK &&
        nvs_get_u16(handle, kPortKey, &port) == ESP_OK && port != 0) {
      g_port = static_cast<int>(port);
      g_named = true;
    }
    nvs_close(handle);
  }

  if (g_named) {
    printf("dial: pointed at %s:%d\n", g_host, g_port);
  } else {
    printf("dial: nothing named — `bench dial <ip> <port>` points it at a host\n");
  }
  xTaskCreate(DialTask, "dial", kStackBytes, nullptr, 2, nullptr);
}

void dial::report() {
  if (g_named) {
    printf("dial: %s:%d, %s — %u dial(s), %u connect(s)\n", g_host, g_port,
           g_up ? "up" : "down", static_cast<unsigned>(g_dials),
           static_cast<unsigned>(g_connects));
  } else {
    printf("dial: nothing is named — `bench dial <ip> <port>`\n");
  }
  printf("dial: %u line(s) in, %u out, %u drop(s), %u refused\n",
         static_cast<unsigned>(g_lines_in), static_cast<unsigned>(g_lines_out),
         static_cast<unsigned>(g_drops), static_cast<unsigned>(g_refused));
}

void dial::set(const char* spec) {
  char host[sizeof(g_host)] = {0};
  int port = 0;
  if (std::sscanf(spec, "%19s %d", host, &port) != 2 || port <= 0 || port > 65535) {
    printf("bench: dial needs an address and a port, e.g. `bench dial 192.168.0.103 3333`\n");
    return;
  }

  if (g_send == nullptr) {
    std::memcpy(g_host, host, sizeof(g_host));
    g_port = port;
    g_named = true;
    return;
  }

  xSemaphoreTake(g_send, portMAX_DELAY);
  std::memcpy(g_host, host, sizeof(g_host));
  g_port = port;
  g_named = true;
  // ⚠️ A connection to the old address is not a connection to this one. It is
  //    let go rather than kept, so that what is up is always what was named.
  if (g_sock >= 0) {
    shutdown(g_sock, SHUT_RDWR);
  }
  xSemaphoreGive(g_send);

  // ⛔ Written down because with the USB cable out there is no console to type
  //    it into again. ⚠️ Nothing goes to NVS when NVS is not there — the link
  //    still works for this boot, and the line says so.
  nvs_handle_t handle = 0;
  const esp_err_t opened = nvs_open(kNvsNamespace, NVS_READWRITE, &handle);
  if (opened != ESP_OK) {
    printf("bench: dial -> %s:%d, for this boot only (nvs %d)\n", host, port,
           static_cast<int>(opened));
    return;
  }
  nvs_set_str(handle, kHostKey, host);
  nvs_set_u16(handle, kPortKey, static_cast<uint16_t>(port));
  nvs_commit(handle);
  nvs_close(handle);
  printf("bench: dial -> %s:%d, kept across a reboot\n", host, port);
}

bool dial::up() { return g_up; }

void dial::say(const char* text) {
  if (text == nullptr || !g_up || g_send == nullptr) {
    return;
  }
  xSemaphoreTake(g_send, portMAX_DELAY);
  const int fd = g_sock;
  if (fd >= 0) {
    char line[kMaxLine + 2];
    size_t length = std::strlen(text);
    // ⛔ Cut, never split: a line longer than the bound is a line the far end
    //    would have dropped whole, and half of one is worse than none.
    if (length > static_cast<size_t>(kMaxLine)) {
      length = static_cast<size_t>(kMaxLine);
    }
    std::memcpy(line, text, length);
    if (length == 0 || line[length - 1] != '\n') {
      line[length++] = '\n';
    }
    if (WriteAll(fd, line, length)) {
      ++g_lines_out;
    } else {
      ++g_drops;
      g_up = false;
      shutdown(fd, SHUT_RDWR);
    }
  }
  xSemaphoreGive(g_send);
}
