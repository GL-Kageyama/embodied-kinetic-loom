#include "net.h"

#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "esp_netif.h"
// ⚠️ `esp_netif_get_netif_impl` moved out of `esp_netif.h` and into this header
//    by 5.5. It is the only public door to the lwIP `netif` behind an
//    `esp_netif_t`, and a gratuitous ARP needs that `netif` and nothing else.
#include "esp_netif_net_stack.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "lwip/inet.h"
#include "lwip/ip4_addr.h"
#include "lwip/etharp.h"
#include "lwip/netif.h"
#include "lwip/sockets.h"

namespace {

// ⚠️ A port that is written down once. 3333 is a choice, not a measurement —
//    nothing in this machine assigns ports, and the number is not a claim about
//    anything except which door to knock on.
constexpr int kPort = 3333;
constexpr int kMaxLine = 256;
constexpr int kBacklog = 1;

bool g_listening = false;
int g_served = 0;
int g_udp = 0;

// ⚠️ One connection at a time. A second one waits in the backlog rather than
//    being handed its own task: two readers of one console is the failure this
//    board has already paid for, and two readers of one socket would be the
//    same shape one layer out.
//
// ⛔ Nothing here reads a line and does something with it. The only thing that
//    leaves is a count, so a connection cannot move this machine.
void Serve(int fd, const char* peer) {
  printf("net: open from %s\n", peer);
  ++g_served;

  char line[kMaxLine + 1];
  int length = 0;
  char chunk[64];
  for (;;) {
    const int got = static_cast<int>(recv(fd, chunk, sizeof(chunk), 0));
    if (got <= 0) {
      break;
    }
    for (int i = 0; i < got; ++i) {
      const char c = chunk[i];
      if (c == '\r') {
        continue;
      }
      if (c == '\n') {
        if (length > 0) {
          // ⛔ The line is not printed and not run. Its length is the answer,
          //    and a line that could contain a psk is never echoed by a path
          //    whose whole job is to count bytes.
          char answer[24];
          const int n = snprintf(answer, sizeof(answer), "ok %d\n", length);
          send(fd, answer, static_cast<size_t>(n), 0);
          length = 0;
        }
        continue;
      }
      if (length < kMaxLine) {
        line[length++] = c;
      } else {
        printf("net: line too long, dropped\n");
        length = 0;
      }
    }
  }
  printf("net: closed\n");
  close(fd);
}

void NetTask(void*) {
  const int listener = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
  if (listener < 0) {
    printf("net: no socket (%d)\n", errno);
    vTaskDelete(nullptr);
    return;
  }

  const int reuse = 1;
  setsockopt(listener, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));

  sockaddr_in address;
  std::memset(&address, 0, sizeof(address));
  address.sin_family = AF_INET;
  address.sin_port = htons(kPort);
  address.sin_addr.s_addr = htonl(INADDR_ANY);

  if (bind(listener, reinterpret_cast<sockaddr*>(&address), sizeof(address)) < 0) {
    printf("net: the port was refused (%d)\n", errno);
    close(listener);
    vTaskDelete(nullptr);
    return;
  }
  if (listen(listener, kBacklog) < 0) {
    printf("net: the port will not listen (%d)\n", errno);
    close(listener);
    vTaskDelete(nullptr);
    return;
  }

  g_listening = true;
  printf("net: listening on %d\n", kPort);

  // ⚠️ A UDP ear on the same number, and it is the measurement rather than a
  //    feature. On 2026-10-21 a datagram the Mac sent *back* to a port this
  //    board had just opened arrived, while a cold connection from the same
  //    Mac failed with "No route to host" and an ARP entry that never once
  //    went incomplete. Those two cannot both be explained by the path being
  //    blocked, so the question had to be asked one layer simpler: does a
  //    datagram the Mac sends first arrive at all.
  const int ear = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
  if (ear >= 0) {
    const int reuse_ear = 1;
    setsockopt(ear, SOL_SOCKET, SO_REUSEADDR, &reuse_ear, sizeof(reuse_ear));
    if (bind(ear, reinterpret_cast<sockaddr*>(&address), sizeof(address)) < 0) {
      printf("net: no udp ear (%d)\n", errno);
      close(ear);
    }
  }

  for (;;) {
    if (ear >= 0) {
      fd_set reading;
      FD_ZERO(&reading);
      FD_SET(listener, &reading);
      FD_SET(ear, &reading);
      timeval none;
      none.tv_sec = 0;
      none.tv_usec = 0;
      select(listener + 1, &reading, nullptr, nullptr, &none);

      if (FD_ISSET(ear, &reading)) {
        sockaddr_in from;
        socklen_t from_size = sizeof(from);
        char text[128];
        const int got = static_cast<int>(
            recvfrom(ear, text, sizeof(text) - 1, 0,
                     reinterpret_cast<sockaddr*>(&from), &from_size));
        if (got > 0) {
          text[got] = 0;
          char who[32] = {0};
          inet_ntoa_r(from.sin_addr, who, sizeof(who) - 1);
          printf("net: udp from %s — a datagram the Mac sent first arrived\n", who);
          sendto(ear, "heard", 5, 0, reinterpret_cast<sockaddr*>(&from),
                 from_size);
          ++g_udp;
        }
      }
    }

    sockaddr_in peer;
    socklen_t peer_size = sizeof(peer);
    const int fd = accept(listener, reinterpret_cast<sockaddr*>(&peer), &peer_size);
    if (fd < 0) {
      // ⚠️ A connection that never comes is the normal state of a listening
      //    port, so this is a poll interval and not an error path. It is kept
      //    short because the UDP ear above is only polled once per turn.
      if (ear >= 0) {
        vTaskDelay(pdMS_TO_TICKS(100));
        continue;
      }
      // ⚠️ A refused accept is not fatal: the address can change under a
      //    reassociation, and a listener that died on one errno would be a
      //    board that answers until it does not.
      printf("net: accept failed (%d)\n", errno);
      vTaskDelay(pdMS_TO_TICKS(250));
      continue;
    }
    char who[32] = {0};
    inet_ntoa_r(peer.sin_addr, who, sizeof(who) - 1);
    Serve(fd, who);
  }
}

}  // namespace

void net_probe::begin() {
  // ⚠️ 4096 and named, because a stack that is too small here fails the same
  //    way it failed in `wifi.cpp`: somewhere else, later, as a corrupt list.
  if (xTaskCreate(NetTask, "net", 4096, nullptr, 2, nullptr) != pdPASS) {
    printf("net: no task — no listener\n");
  }
}

void net_probe::report() {
  printf("net: %s on %d, %d connection(s) served, %d datagram(s) heard\n",
         g_listening ? "listening" : "not listening", kPort, g_served, g_udp);
}

void net_probe::send(const char* spec) {
  if (spec == nullptr) {
    printf("net: send needs <ip> <port> <text>\n");
    return;
  }
  while (*spec == ' ') {
    ++spec;
  }

  // ⚠️ The address is parsed by lwIP's own reader rather than by hand: a
  //    hand-rolled dotted-quad that accepted `999.1.1.1` would send to
  //    somewhere that is not what was typed.
  ip4_addr_t target;
  const char* port_text = nullptr;
  {
    char address[32] = {0};
    int n = 0;
    while (spec[n] != '\0' && spec[n] != ' ' && n < 31) {
      address[n] = spec[n];
      ++n;
    }
    if (!ip4addr_aton(address, &target)) {
      printf("net: \"%s\" is not an address\n", address);
      return;
    }
    port_text = spec + n;
  }
  while (*port_text == ' ') {
    ++port_text;
  }
  const int port = std::atoi(port_text);
  if (port <= 0 || port > 65535) {
    printf("net: the port was not a number in range\n");
    return;
  }
  const char* text = port_text;
  while (*text != '\0' && *text != ' ') {
    ++text;
  }
  while (*text == ' ') {
    ++text;
  }
  const size_t length = std::strlen(text);
  if (length == 0) {
    printf("net: there is nothing to send\n");
    return;
  }

  const int fd = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
  if (fd < 0) {
    printf("net: no socket (%d)\n", errno);
    return;
  }

  sockaddr_in to;
  std::memset(&to, 0, sizeof(to));
  to.sin_family = AF_INET;
  to.sin_port = htons(static_cast<uint16_t>(port));
  to.sin_addr.s_addr = target.addr;

  const int sent = static_cast<int>(
      sendto(fd, text, length, 0, reinterpret_cast<sockaddr*>(&to), sizeof(to)));
  if (sent < 0) {
    printf("net: sendto failed (%d)\n", errno);
    close(fd);
    return;
  }
  printf("net: sent %d byte(s) to %s:%d\n", sent, ip4addr_ntoa(&target), port);

  // ⚠️ Two seconds, and it blocks the console like `bench wifi scan` does.
  //    ⛔ A reply is the Mac's packet arriving at this board — that is the
  //    whole measurement, and silence is the answer "nothing came back".
  timeval wait;
  wait.tv_sec = 2;
  wait.tv_usec = 0;
  setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &wait, sizeof(wait));

  char reply[128];
  const int got = static_cast<int>(recvfrom(fd, reply, sizeof(reply) - 1, 0,
                                            nullptr, nullptr));
  if (got > 0) {
    reply[got] = 0;
    printf("net: reply \"%s\"\n", reply);
  } else {
    printf("net: no reply\n");
  }
  close(fd);
}

void net_probe::call(const char* spec) {
  if (spec == nullptr) {
    printf("net: call needs <ip> <port> <text>\n");
    return;
  }
  while (*spec == ' ') {
    ++spec;
  }
  ip4_addr_t target;
  char address[32] = {0};
  int n = 0;
  while (spec[n] != '\0' && spec[n] != ' ' && n < 31) {
    address[n] = spec[n];
    ++n;
  }
  if (!ip4addr_aton(address, &target)) {
    printf("net: \"%s\" is not an address\n", address);
    return;
  }
  const char* rest = spec + n;
  while (*rest == ' ') {
    ++rest;
  }
  const int port = std::atoi(rest);
  if (port <= 0 || port > 65535) {
    printf("net: the port was not a number in range\n");
    return;
  }
  const char* text = rest;
  while (*text != '\0' && *text != ' ') {
    ++text;
  }
  while (*text == ' ') {
    ++text;
  }
  const size_t length = std::strlen(text);
  if (length == 0) {
    printf("net: there is nothing to send\n");
    return;
  }

  const int fd = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
  if (fd < 0) {
    printf("net: no socket (%d)\n", errno);
    return;
  }
  timeval wait;
  wait.tv_sec = 3;
  wait.tv_usec = 0;
  setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &wait, sizeof(wait));
  setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &wait, sizeof(wait));

  sockaddr_in to;
  std::memset(&to, 0, sizeof(to));
  to.sin_family = AF_INET;
  to.sin_port = htons(static_cast<uint16_t>(port));
  to.sin_addr.s_addr = target.addr;

  if (connect(fd, reinterpret_cast<sockaddr*>(&to), sizeof(to)) != 0) {
    printf("net: connect to %s:%d failed (%d)\n", ip4addr_ntoa(&target), port,
           errno);
    close(fd);
    return;
  }
  printf("net: connected to %s:%d\n", ip4addr_ntoa(&target), port);

  char line[192];
  const int made = snprintf(line, sizeof(line), "%.*s\n",
                            static_cast<int>(length < 180 ? length : 180), text);
  // ⚠️ `::send`, because inside this namespace the name `send` means this
  //    file's own probe and would be called with the wrong arguments.
  if (::send(fd, line, static_cast<size_t>(made), 0) != made) {
    printf("net: the line did not go out (%d)\n", errno);
    close(fd);
    return;
  }

  // ⛔ The measurement is this read. A connection that opens and carries
  //    nothing back is a body that can speak but cannot be spoken to.
  char reply[128];
  const int got = static_cast<int>(recv(fd, reply, sizeof(reply) - 1, 0));
  if (got > 0) {
    reply[got] = 0;
    printf("net: the host said \"%s\"\n", reply);
  } else if (got == 0) {
    printf("net: the host closed without a word\n");
  } else {
    printf("net: nothing came back (%d)\n", errno);
  }
  close(fd);
}

void net_probe::announce() {
  esp_netif_t* handle = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
  if (handle == nullptr) {
    printf("net: no interface to announce\n");
    return;
  }
  netif* stack = static_cast<netif*>(esp_netif_get_netif_impl(handle));
  if (stack == nullptr) {
    printf("net: the interface has no stack behind it\n");
    return;
  }
  // ⚠️ Broadcast, to everyone, without being asked. It changes no state of
  //    this board and carries nothing but the address it already answers to.
  etharp_gratuitous(stack);
  printf("net: announced this address to the whole segment\n");
}
