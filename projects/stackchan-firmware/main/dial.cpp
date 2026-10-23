#include "dial.h"

#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "freertos/FreeRTOS.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "audio_line.h"
#include "dial_policy.h"
#include "dial_scan.h"
#include "wifi.h"
#include "lwip/inet.h"
#include "lwip/sockets.h"
#include "nvs.h"
#include "sound.h"

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
//: ⚠️ **A sweep candidate gets a shorter wait than the named address.** A host
//:    on the same segment answers in milliseconds; the 3,000 ms of the named
//:    address is there for a busy one. ⛔ At 254 candidates a long wait here
//:    would turn one failed sweep into many minutes of silence.
constexpr int kSweepWaitMs = 400;
//: ⚠️ **The host's first line, `loom`** (`projects/stackchan/daemon/__main__.py`).
//:    It identifies the far end before any line of it reaches `RunLine`.
constexpr int kHelloWaitMs = 1500;
constexpr int kPollMs = 100;
//: ⚠️ **8192 に上げた（2026-10-21）。** 読み手の `chunk` を 4096 にしたので、
//: 8192 の stack では 1 つの `recv` が任務ごと越える。
constexpr int kStackBytes = 16384;
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
//: ⚠️ **2026-10-23 に足した。** 名指しの住所が黙ったとき、板は自分の /24 を
//: 順に試す。`g_swept` は試した住所の数、`g_found` は挨拶で見つけた数である。
//: ⛔ **見つけた住所は NVS に書かない**——住所を書くのはコンソールの言葉であり、
//: 見つけた住所は1つのリースの事実である（`dial.h`）。
uint32_t g_swept = 0;
uint32_t g_found = 0;
//: ⚠️ **2026-10-23、掃き出しが「0件」とだけ言ったので足した。** 404 の住所を
//: 試して1つも繋がらなかった、という事実だけでは、**繋がらなかった理由**が
//: 分からない——`socket()` が取れなかったのか、`connect` が断られたのか、
//: 時間切れか。⛔ **数は、理由の代わりにならない。**
uint32_t g_connect_failed = 0;
int g_connect_errno = 0;
uint32_t g_greet_failed = 0;
//: ⛔ **`socket()` が取れなかった失敗は、住所の失敗ではない。** 掃き出しを続けても
//: 1つも繋がらないので、**掃き出しを止める理由**になる——2026-10-23 の実測では、
//: これを見分けられないあいだ、404 の住所が 3 秒足らずで「試された」ことになっていた。
uint32_t g_no_socket = 0;
//: ⛔ **掃き出しは、静かな間隔を置いてからである。** 経路の無い起動直後に
//: 一度走らせれば足りるものを、失敗のたびに 254 の住所へ繰り返すのは、
//: **回線の調子ではなく、こちらの焦りを測っている**。⚠️ 30 秒は選んだ数で
//: あり、測った数ではない。
constexpr int64_t kSweepEveryUs = 30 * 1000 * 1000;
int64_t g_last_sweep_us = 0;
uint32_t g_lines_in = 0;
uint32_t g_lines_out = 0;
uint32_t g_drops = 0;
uint32_t g_refused = 0;

// --- the audio block ------------------------------------------------------
//
//: ⛔ **Read here, played by another task.** The first version played each block
//: inside this reader, and it played at **about a third of real time**: 133,102
//: bytes took 9.61 s to feed, for a sound of 2.77 s. ⚠️ **The amplifier was
//: not the fault** — `bench audio 2000` measured **0.97x** — the shape was: a
//: reader that plays stops reading, so **reading and playing took turns**,
//: and the socket's window only opens while the reader reads.
//: ⇒ a queue and one task. ⚠️ The queue is also the flow control: when it is
//: full the reader waits, and a reader that waits opens no window, which slows
//: the host down — TCP's own back-pressure, with no drop rule to invent.
constexpr int kAudioBlocks = 8;  // 8 x 4096 bytes = 683 ms at 24 kHz

struct AudioBlock {
  int bytes;
  int16_t data[audio_line::kMaxBytes / 2];
};

QueueHandle_t g_audio = nullptr;
//: ⚠️ **Both are static, not on their task's stack** — `kStackBytes` is 16384
//: and one block is an eighth of it.
AudioBlock g_fill = {};     // the reader's; it is the only writer
AudioBlock g_playing = {};  // the audio task's; it is the only reader
uint32_t g_audio_blocks = 0;
uint32_t g_audio_bytes = 0;
uint32_t g_audio_failed = 0;
uint32_t g_audio_queued = 0;
//: ⚠️ **どこで時間が消えるかを分けるための2つ。** `played` の速さが 1.0x なら
//: 鳴り手は健全で、遅れは読む側に在る。`waited_us` は読み手が待ち行列で
//: 止まっていた時間である。
uint32_t g_audio_played_us = 0;
uint32_t g_audio_waited_us = 0;
//: ⚠️ **2026-10-21 に足した。** 65 の塊のうち 15 しか鳴らず、送る側からは
//: 「送った」と見えていた——**線が運ばなかったのか、読み手がずれたのか**を
//: 分けるために、`recv` が返したバイト数と、頭として通った数を数える。
uint32_t g_rx_bytes = 0;
uint32_t g_heads = 0;
//: ⚠️ 読む側が**凍っているのか、呼ばれて空なのか**。`recv` の回数、`select` が
//: 空で返った回数、最後にバイトを受けた時刻。
uint32_t g_recv_calls = 0;
uint32_t g_polls = 0;
int64_t g_last_rx_us = 0;

void AudioTask(void*) {
  while (true) {
    if (xQueueReceive(g_audio, &g_playing, portMAX_DELAY) != pdTRUE) {
      continue;
    }
    const int64_t began = esp_timer_get_time();
    //: ⚠️ **Two bytes are one sample** (16-bit linear, little-endian). The head's
    //: parser refuses an odd count, so this division loses nothing. 4096 bytes
    //: are 2048 samples, 85 ms of sound at 24 kHz.
    const bool whole = sound::play_pcm(g_playing.data, g_playing.bytes / 2);
    g_audio_played_us += static_cast<uint32_t>(esp_timer_get_time() - began);
    if (whole) {
      ++g_audio_blocks;
      g_audio_bytes += static_cast<uint32_t>(g_playing.bytes);
    } else {
      // ⚠️ The amplifier being down. Counted apart from a block that never
      //    arrived: this one is the board's own silence.
      ++g_audio_failed;
    }
  }
}

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
int Dial(const char* host, int port, int wait_ms) {
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
    ++g_connect_failed;
    ++g_no_socket;
    g_connect_errno = errno;
    return -1;
  }
  const int flags = fcntl(fd, F_GETFL, 0);
  fcntl(fd, F_SETFL, flags | O_NONBLOCK);

  if (connect(fd, reinterpret_cast<sockaddr*>(&address), sizeof(address)) != 0) {
    if (errno != EINPROGRESS) {
      ++g_connect_failed;
      g_connect_errno = errno;
      close(fd);
      return -1;
    }
    fd_set writable;
    FD_ZERO(&writable);
    FD_SET(fd, &writable);
    timeval wait;
    wait.tv_sec = wait_ms / 1000;
    wait.tv_usec = (wait_ms % 1000) * 1000L;
    const int ready = select(fd + 1, nullptr, &writable, nullptr, &wait);
    if (ready <= 0) {
      // ⚠️ **-1 (時間切れ) と、`select` 自身の失敗を、同じ数にしない。**
      //    `select` が 0 を返したのは「窓の中で何も起きなかった」であり、
      //    負を返したのは errno が動いたということである。
      ++g_connect_failed;
      g_connect_errno = (ready == 0) ? -1 : errno;
      close(fd);
      return -1;
    }
    int error = 0;
    socklen_t length = sizeof(error);
    if (getsockopt(fd, SOL_SOCKET, SO_ERROR, &error, &length) != 0 || error != 0) {
      ++g_connect_failed;
      g_connect_errno = (error != 0) ? error : errno;
      close(fd);
      return -1;
    }
  }
  return fd;
}

// ⚠️ **The first line belongs to the identification, not to the body.**
//
// ⛔ The host writes `loom` before anything else on every connection
//    (`projects/stackchan/daemon/__main__.py`, `Link.accept`). It is read here
//    and **never handed to `RunLine`** — a greeting that reached the dispatcher
//    is an unknown command printed back at the console, and a line the host
//    never meant as a command.
//
// ⚠️ **A connection that does not greet is not this host.** Without this rule
//    the sweep would drive the body from whatever holds port 3333 on the
//    segment — the link is not authenticated, and an address is not an
//    identity. ⛔ **The named address is held to the same rule**: a stale lease
//    can belong to a different machine holding the same number.
bool Greet(int fd, char* line, int size) {
  int length = 0;
  const TickType_t started = xTaskGetTickCount();
  while (true) {
    const uint32_t elapsed = static_cast<uint32_t>(
        xTaskGetTickCount() - started) * portTICK_PERIOD_MS;
    if (elapsed >= static_cast<uint32_t>(kHelloWaitMs)) {
      return false;
    }
    fd_set readable;
    FD_ZERO(&readable);
    FD_SET(fd, &readable);
    timeval wait;
    const uint32_t left = static_cast<uint32_t>(kHelloWaitMs) - elapsed;
    wait.tv_sec = left / 1000;
    wait.tv_usec = (left % 1000) * 1000L;
    if (select(fd + 1, &readable, nullptr, nullptr, &wait) <= 0) {
      // ⚠️ Nothing inside the window, or an error — the same answer to the
      //    same question, and both mean "try the next address".
      return false;
    }
    char c = 0;
    const int got = recv(fd, &c, 1, 0);
    if (got <= 0) {
      if (got < 0 && (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR)) {
        continue;
      }
      return false;
    }
    if (c == '\r') {
      continue;
    }
    if (c == '\n') {
      break;
    }
    if (length < size - 1) {
      line[length++] = c;
    } else {
      // ⛔ A greeting this long is not a greeting. Reading on would let a
      //    hostile or confused far end fill the buffer with anything.
      return false;
    }
  }
  line[length] = '\0';
  return dial_scan::is_loom(line, length);
}

// ⛔ **A host that goes away without closing the socket is what this is for.**
//    On 2026-10-21 a daemon restart left the board's connection in `FIN_WAIT_1`
//    with no ACK for over a minute: `ping` failed, and `DialTask` has no read
//    timeout, so the body went on believing it was connected. ⚠️ Now that an
//    absent host puts the body to sleep, that belief would keep the screen lit
//    all night. ⇒ keepalive: 10 s idle, 5 s between probes, three probes —
//    about 25 s to a dead socket. ⛔ **These are chosen, not measured.**
//    ⛔ Requires `CONFIG_LWIP_TCP_KEEPALIVE` (`sdkconfig.defaults`); without it
//    lwIP accepts `SO_KEEPALIVE` and applies its own hours-long defaults.
void KeepAlive(int fd) {
  int on = 1;
  setsockopt(fd, SOL_SOCKET, SO_KEEPALIVE, &on, sizeof(on));
#ifdef TCP_KEEPIDLE
  int idle = 10;
  int interval = 5;
  int count = 3;
  setsockopt(fd, IPPROTO_TCP, TCP_KEEPIDLE, &idle, sizeof(idle));
  setsockopt(fd, IPPROTO_TCP, TCP_KEEPINTVL, &interval, sizeof(interval));
  setsockopt(fd, IPPROTO_TCP, TCP_KEEPCNT, &count, sizeof(count));
#endif
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
//
// ⛔ **Except for the audio block, which is the one thing on this wire that is
//    not text.** `audio <n>` is a head (`audio_line.h`), and the n bytes after
//    it are samples that are not split on `\n` — a sample byte may hold 0x0A.
void Service(int fd) {
  char line[kMaxLine + 1];
  int length = 0;
  int want = 0;   // bytes still owed for the block the last head named
  int have = 0;
  uint8_t* raw = reinterpret_cast<uint8_t*>(g_fill.data);
  //: ⛔ **4096。** 2026-10-21 の実測——**1回の `select`＋`recv` に約 6 ms** かかり、
  //: 512 バイトずつでは **84 KB/s** で頭打ちになった。往復は 17 ms である
  //: （基板の `bench pos` を TCP 越しに5回）ゆえ、遅いのは回線ではなく**呼び出しの数**。
  //: ⇒ 一度に多く読む。標本は1バイトずつ組み立てるので、塊の大きさは音に影響しない。
  //: ⚠️ 4096 で **121/40 KB/s** と振れたので、さらに倍にした（8192）。
  char chunk[8192];
  while (true) {
    fd_set readable;
    FD_ZERO(&readable);
    FD_SET(fd, &readable);
    timeval wait;
    wait.tv_sec = 0;
    wait.tv_usec = kPollMs * 1000L;
    const int ready = select(fd + 1, &readable, nullptr, nullptr, &wait);
    if (ready == 0) {
      ++g_polls;
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
    ++g_recv_calls;
    g_last_rx_us = esp_timer_get_time();
    g_rx_bytes += static_cast<uint32_t>(got);
    for (int i = 0; i < got; ++i) {
      const char c = chunk[i];
      if (want > 0) {
        raw[have++] = static_cast<uint8_t>(c);
        if (have == want) {
          g_fill.bytes = want;
          // ⚠️ Full queue = the reader waits here. That is the flow control,
          //    and it is why nothing has to be dropped.
          if (g_audio != nullptr) {
            const int64_t before = esp_timer_get_time();
            const bool sent = xQueueSend(g_audio, &g_fill, portMAX_DELAY) == pdTRUE;
            g_audio_waited_us += static_cast<uint32_t>(esp_timer_get_time() - before);
            if (sent) {
              ++g_audio_queued;
            }
          }
          want = 0;
          have = 0;
        }
        continue;
      }
      if (c == '\r') {
        continue;
      }
      if (c == '\n') {
        if (length > 0) {
          line[length] = '\0';
          if (audio_line::parse(line, length, &want)) {
            // ⚠️ A head is not a command and is not counted as a line. Its
            //    bytes are played where they land, below.
            have = 0;
            ++g_heads;
          } else {
            ++g_lines_in;
            Take(line, length);
          }
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
    char reached[sizeof(g_host)] = {0};
    char hello[64];
    // ⚠️ **窓を開けて、窓が閉じるまでの実時間を測る。** ⛔ 掃き出しが
    //    「3秒足らずで404の住所を試した」なら、窓は窓として働いていない。
    const int64_t began = esp_timer_get_time();
    int fd = Dial(host, port, kConnectWaitMs);
    if (fd < 0) {
      printf("dial: %s:%d gave nothing in %lld ms (errno %d)\n", host, port,
             static_cast<long long>((esp_timer_get_time() - began) / 1000),
             g_connect_errno);
    }
    if (fd >= 0) {
      if (Greet(fd, hello, sizeof(hello))) {
        std::memcpy(reached, host, sizeof(reached));
        KeepAlive(fd);
      } else {
        ++g_greet_failed;
        close(fd);
        fd = -1;
        printf("dial: %s:%d did not greet — not this host\n", host, port);
      }
    }

    // ⛔ **The named address answered nothing.** 2026-10-23: the Mac's lease
    //    moved and this board went on dialling a number nobody held. ⇒ look,
    //    rather than wait for a wrong number to become right again.
    //
    // ⛔ **But only if this body has somewhere to look FROM.** At boot this
    //    task runs before the station has an address, and then `connect`
    //    returns `ENETUNREACH` in 0 ms against every candidate: the sweep
    //    would "try" 254 addresses in three seconds and learn nothing, because
    //    a missing route and a missing host are one failure to a socket.
    //    ⇒ ask for the route first, and sweep on a quiet interval after.
    bool sweep = false;
    if (fd < 0) {
      const int64_t now_us = esp_timer_get_time();
      // ⚠️ The rule itself lives in `dial_scan::sweep_when`, where the host can
      //    compile and ask it. ⛔ This side only prints which way it went.
      switch (dial_scan::sweep_when(wifi_probe::routed(), now_us, g_last_sweep_us,
                                    kSweepEveryUs)) {
        case dial_scan::Sweep::kNoRoute:
          printf("dial: no route yet — %s:%d is not being looked for\n", host, port);
          break;
        case dial_scan::Sweep::kTooSoon:
          printf("dial: %s:%d is still silent; the last sweep was %lld s ago\n",
                 host, port,
                 static_cast<long long>((now_us - g_last_sweep_us) / 1000000));
          break;
        case dial_scan::Sweep::kNow:
          sweep = true;
          g_last_sweep_us = now_us;
          break;
      }
    }
    if (sweep) {
      uint32_t list[dial_scan::kMaxCandidates];
      const int count = dial_scan::candidates(host, list, dial_scan::kMaxCandidates);
      for (int i = 1; i < count; ++i) {
        char text[20];
        if (dial_scan::format(list[i], text, sizeof(text)) == 0) {
          continue;
        }
        ++g_swept;
        const uint32_t dead = g_no_socket;
        fd = Dial(text, port, kSweepWaitMs);
        if (fd < 0) {
          // ⛔ **ソケットが取れないなら、残りの住所も同じ理由で失敗する。**
          //    254 回同じことを試すのは、掃き出しではなく空回りである。
          if (g_no_socket != dead) {
            printf("dial: no socket to make — the sweep stops at %s\n", text);
            break;
          }
          // ⛔ **経路が途中で消えたなら、残りも同じ失敗である。**
          if (!wifi_probe::routed()) {
            printf("dial: the route went away — the sweep stops at %s\n", text);
            break;
          }
          continue;
        }
        if (!Greet(fd, hello, sizeof(hello))) {
          ++g_greet_failed;
          close(fd);
          fd = -1;
          continue;
        }
        KeepAlive(fd);
        ++g_found;
        std::memcpy(reached, text, sizeof(reached));
        printf("dial: found the host at %s:%d — %d address(es) past the named one\n",
               text, port, i);
        // ⚠️ Remembered for this boot, and only here: the sweep's answer is
        //    where the host is *now*, and NVS is still the console's to write.
        if (g_send != nullptr) {
          xSemaphoreTake(g_send, portMAX_DELAY);
          std::memcpy(g_host, text, sizeof(g_host));
          xSemaphoreGive(g_send);
        }
        break;
      }
    }

    if (fd < 0) {
      vTaskDelay(pdMS_TO_TICKS(backoff));
      backoff = (backoff * 2 > kMaxBackoffMs) ? kMaxBackoffMs : backoff * 2;
      continue;
    }

    Publish(fd, true);
    ++g_connects;
    printf("dial: connected to %s:%d\n", reached, port);
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
  g_audio = xQueueCreate(kAudioBlocks, sizeof(AudioBlock));
  if (g_audio != nullptr) {
    xTaskCreate(AudioTask, "audio", 3072, nullptr, 3, nullptr);
  } else {
    std::printf("dial: no audio queue — a block will be read and not played\n");
  }

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
  //: ⚠️ **0 は「走らなかった」であり、「探して見つからなかった」ではない**——
  //: それを分けるのは上の `dial(s)` と `connect(s)` である。
  printf("dial: %u address(es) swept, %u found by the sweep\n",
         static_cast<unsigned>(g_swept), static_cast<unsigned>(g_found));
  //: ⚠️ **`-1` は「窓の中で何も起きなかった」、正の数は `connect` の断りである。**
  //: ⛔ **0件という数だけでは、掃き出しが届かなかったのか、届いて名乗らなかったのか
  //: 分からない。**
  printf("dial: %u connect attempt(s) failed (last %d), %u opened without a greeting\n",
         static_cast<unsigned>(g_connect_failed), g_connect_errno,
         static_cast<unsigned>(g_greet_failed));
  //: ⛔ **`socket()` が 0 でないとき、住所の一覧は何も語らない。**
  printf("dial: %u attempt(s) had no socket to make\n",
         static_cast<unsigned>(g_no_socket));
  printf("dial: %u line(s) in, %u out, %u drop(s), %u refused\n",
         static_cast<unsigned>(g_lines_in), static_cast<unsigned>(g_lines_out),
         static_cast<unsigned>(g_drops), static_cast<unsigned>(g_refused));
  //: ⚠️ `not played` is the amplifier being down, and it is counted apart from
  //: a block that never arrived: the first is this board's silence, the second
  //: is the wire's.
  printf("dial: %u audio block(s), %u byte(s), %u not played\n",
         static_cast<unsigned>(g_audio_blocks),
         static_cast<unsigned>(g_audio_bytes),
         static_cast<unsigned>(g_audio_failed));
  //: ⚠️ **いま鳴っているかではなく、何が届いたかである。** `queued` と `played`
  //: が離れていれば、読み手は走っていて鳴り手が止まっている——そこが分かれ目である。
  printf("dial: audio played in %u ms, reader waited %u ms\n",
         static_cast<unsigned>(g_audio_played_us / 1000),
         static_cast<unsigned>(g_audio_waited_us / 1000));
  const int64_t now = esp_timer_get_time();
  printf("dial: link read %u byte(s), %u audio head(s), %u recv, %u poll(s), last %lld ms ago\n",
         static_cast<unsigned>(g_rx_bytes), static_cast<unsigned>(g_heads),
         static_cast<unsigned>(g_recv_calls), static_cast<unsigned>(g_polls),
         static_cast<long long>(g_last_rx_us == 0 ? -1 : (now - g_last_rx_us) / 1000));
  printf("dial: audio queue %s, %u waiting, %u queued, heap %u\n",
         g_audio != nullptr ? "up" : "none",
         static_cast<unsigned>(g_audio != nullptr ? uxQueueMessagesWaiting(g_audio) : 0),
         static_cast<unsigned>(g_audio_queued),
         static_cast<unsigned>(esp_get_free_heap_size()));
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
