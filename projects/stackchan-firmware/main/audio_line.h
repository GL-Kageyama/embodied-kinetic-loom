// The head of an audio block: one line that says how many bytes follow.
//
// ⛔ Why a second grammar. The console's and the link's lines are text, and every
//    one of them is parsed as a command. Speech does not fit: 24 kHz, 16-bit,
//    mono is 48,000 bytes a second, and the console's line bound is 256 bytes —
//    five milliseconds. ⇒ one line announces a block, and the bytes after
//    it are **not a line at all**: no newline is read from them, and none can
//    appear, because a sample byte may hold 0x0A.
//
// ⚠️ The rule is written as one sentence and checked as one function, the same
//    shape `dial_policy` has: `audio_line.cpp` compiles on the host under
//    `tests/test_stackchan_audio_line.py` and takes no IDF header.
#pragma once

namespace audio_line {

//: The largest block a head may announce, **and it is even**. ⚠️ **This is the
//: board's buffer**, not the host's convenience: `dial.cpp` holds eight of them
//: in a queue. 4096 is **85 ms at 24 kHz** and eight of them are **683 ms** of
//: sound held ahead of the wire — which is what absorbs a dip, and the ear is
//: why the rate is 24 kHz at all (`board::kAudioSampleRate`).
//:
//: ⛔ **This number was 2048 for a reason, and the reason has to be checked at
//: boot.** In the first version the queue was **33 KB and did not fit**: the
//: heap held **36,512 bytes free** and `xQueueCreate` returned `none` without a
//: word, so every block was refused. The queue of eight 4096-byte blocks is
//: **32,800 bytes**. ⚠️ The same board reported **95,940 bytes free** with the
//: 2048 queue allocated on 2026-10-21 — so it fits now, and `dial.cpp` prints
//: `audio queue up` or `no memory` at boot to say which.
constexpr int kMaxBytes = 4096;

//: True when `line` is exactly `audio <n>`, `n` is between one and `kMaxBytes`,
//: **and `n` is even**. Writes `n` to `*bytes` and leaves it untouched when the
//: answer is false.
//:
//: ⚠️ **Two bytes are one sample.** The payload is 16-bit linear little-endian,
//: so an odd count is half a sample — a block that cannot be played whole, and
//: the one that would leave the next block starting mid-sample. `audio 0` is
//: refused: it says nothing to do, and a reader that obeyed it would be one
//: that can be made to do nothing forever.
bool parse(const char* line, int length, int* bytes);

}  // namespace audio_line
