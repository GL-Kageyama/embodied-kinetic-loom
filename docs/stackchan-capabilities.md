<!-- i18n-version: 1.0.0 | canonical: docs/stackchan-capabilities.md | translated: 2026-10-24 -->

**Language:** [English](stackchan-capabilities.md) | [日本語](stackchan-capabilities-ja.md) | [中文](stackchan-capabilities-zh.md)

# What the body can do — the Stack-chan inventory

⛔ **This page is an inventory, not a score and not a record.** `docs/stackchan-progress.md` asks eight questions and says how far each has climbed; `projects/stackchan-firmware/records/` holds what was observed on a day; `HISTORY.md` holds the dated measurements. **What none of them holds is the surface itself** — every channel the body has, every word it understands, every verb it answers, every dial the host can turn. ⇒ **That union exists nowhere else, and that is the only reason this page exists.**

⚠️ **Where a row's number belongs to another page, that page is the source and this row is the copy** — the rule `docs/construction-memo.md` states for itself, applied here for the same reason. **If the two disagree, the source is right.**

**Checked 2026-10-24** against `projects/stackchan-firmware/` (image **935,488 bytes**, written at `0x20000`) and the job that is actually installed (`--listen 0.0.0.0:3333 --sound on --presence normal --meta quiet --voice on`, read from `ps`).

## How to read a row

| mark | meaning |
|---|---|
| ✅ | measured on the unit, or held by a test that runs |
| ⚠️ | built, and nobody has said it is right |
| ⛔ | named here as absent |

⚠️ **A test proves the code computes what it was told to compute, and nothing more.** ⇒ **A capability that has never been exercised on the unit says so, even when a test is green.**

## The body — four channels, one switch, and two wires

### The screen

✅ **An ILI9342C at 320 × 240 on SPI3**, drawing the vendor's own skin: an 8-bit coverage buffer, 8 × 8 supersampled, so the edges carry intermediate values rather than a staircase. The drawing is `face_bitmap.cpp`, and **fifteen** tests compile it on the host and ask the pixels — **six more** ask that the eight words be spelled the same in five places, and that the colour table keep the hue it gives the LEDs.

- **Eight faces, and `null`** — a frame may leave the `face` field `null`, which means *this frame says nothing about the face*. **Five are the Pet's** (`curious` `greeting` `happy` `angry` `sleepy`); **three are this body's own**, added on 2026-10-24 by the author's word 「3つ（＋失敗）」: `focused` (the eyes narrowed, the mouth a short line), `watching` (a wide bar), `startled` (a small mouth, tall). ⛔ **Not one of the three shapes has been judged by an eye** — `bench face <word> [light]` exists so that an eye can.
- ✅ **The drawing takes the light's colour** — one table, `main/light_colour.cpp`, read by the twelve LEDs and by the screen. ⛔ **A copy in each medium would drift in silence.** `off` is the exception and it is named: **black on the LEDs, a neutral grey on the screen**, because `resting` sends `off` every night and a face tinted black would erase the sleeping face the author watched stay lit. ⚠️ **The hue is the firmware's; the word is the host's** — no byte of colour crosses the wire.
- ✅ **`curious` is a plain disc** (`{100, 0}`), the one drawing here that is not the vendor's — the author's word of 2026-10-20 (「通常時の目の形は、単純な⚫︎がいいな」).
- ✅ **It blinks by itself**: both lids shut for **80 ms**, every **3.2–6.8 s**, from a list of seven gaps with no random number — a schedule that cannot be read out of the source cannot be checked. `sleepy` and *no face* do not blink.
- ✅ **`dim` undulates between 72 % and 100 % over 7 s**, inside the firmware, at no cost in frames or bytes.
- ⚠️ **An eye has reported the blink, the undulation and two work colours as visible** (「まばたきしてるよ」「見えた」「揺れていた」「青、紫」, 2026-10-20) — ⛔ **not one of those says the thing is alive**, and the questions were put in halves where the first half came back each time.

### The twelve LEDs

✅ **Eight words reach twelve pixels**, through the AW9523 expander. **The words are the host's; the colours are the firmware's** — ⛔ **not one colour was chosen by measurement.**

- ✅ **`warm` is orange, `alert` is yellow, `breathe` is a breath**, and all three have been seen on the unit, including from the installed daemon through the transport.
- ✅ **`writing` and `busy`** were added on 2026-10-20 and shown to an eye: two colours came back, 「青、紫」. ⚠️ **Which colour is which word was not established** — the sequence was sent without saying what was coming.
- ⛔ **Nobody has named the twelve coming back from sleep.** The switch turns them off; the return has no eye on record.

### The neck

✅ **Two axes — yaw and pitch. No roll.** Degrees go in; the servo's own counts come out; the zeros are this unit's, held in NVS and printed by `bench zeros` — which says **`VENDOR DEFAULTS — not measured here`** when they are not.

- ✅ **One pose line per tick**, `pose <yaw_tenths> <pitch_tenths>*<CC>`, **20 ms apart**, tenths of a degree, both fields always present, one canonical spelling and a two-hex-digit sum. The board checks the sum, the spelling and this machine's limits, arms torque on the present positions, and releases torque after **500 ms** of silence.
- ✅ **Speed**: the firmware writes the stock call (`kPoseTimeMs = 20`, `kPoseSpeed = 0`), measured at about **175°/s**. ⚠️ **40°/s was never the servo's ceiling** — it was a `speed = 100` cap this repository was writing itself.
- ⚠️ **The head lands short in the direction of travel**: **6–8 counts on yaw, 1–3 on pitch**. The servo's own position is what reads short, so a gear train is not hiding it; ⛔ **deadband against friction is narrowed and not named**, and nothing is compensated.
- ✅ **The floor is measured, one goal at a time**: yaw asked 4 / 8 / 12 / 20 / 40 counts moved **0·0 / 0·2 / 6·5 / 13·13 / 34·33** (+ and −); pitch up **1 / 5 / 9 / 18 / 38**, down **5 / 6 / 12 / 20 / 40**. ⇒ **a plan that asks for nothing, or falls inside that floor, is not streamed at all.**
- ✅ **Five postures**, placed one at a time with `bench set` and judged by the author's eye: `look_up`, `look_side`, `nod`, `rest`, `recoil`. ⚠️ **They are absolute**, so what a gesture does depends on where the head already is.
- ✅ **A servo watchdog pings both ids every 5 s when idle**, and **three silences in a row** throw the rail for the measured **3,000 ms**, then write the present positions and release torque. ⚠️ **A recovery is not a diagnosis** — the trigger of a silence is still unnamed, and one bounded move has returned the bus to silence.
- ⛔ **The positions land and the schedule does not**: 21 of 22, 19 of 23, 10 of 11 and 72 of 79 poses were applied late across four measured runs. **Lateness is the schedule's; smoothness is the eye's** (「滑らかだった」).
- ⛔ **`bench power on|off` is the only stop this machine has.** There is no stop in the protocol.

### The speaker — four words, and a voice

✅ **An AW88298 at I²C `0x36`**, its reset on the display's own expander, streaming over I²S at **24 kHz, 16-bit stereo**. The boot volume is **−10 dB**; `fall` alone is written at **0.34** where the other three are 0.22 — the ear's judgement, not a measurement of the shapes. ⛔ **Not one tone is a measurement**; they are choices with the same standing as the twelve colours.

- ✅ **`null` is silence, not a repeat** — the `sound` field is an event, so a frame that says `null` is a frame that says nothing aloud.
- ✅ **And it speaks.** The same amplifier plays 16-bit PCM at 24 kHz: `audio <n>` announces a block, **4096 bytes = 85 ms**, and the board holds **eight of them ahead of the wire = 683 ms** and plays each one on a task of its own.
- ✅ **Measured, one sentence**: **41 blocks / 164,294 bytes**, the board **`not played` 0**, **3,330 ms** — and the author heard it (2026-10-21, 「聞こえた」). That is the only spoken sentence on record.
- ✅ **The quiet hours 21:00–06:00 close this channel and nothing else** — the face, the light, the gesture and the phase are the loud decision's word for word, because **quiet is not absence**.

### The switch — sleep

✅ **Five minutes without the dial link, and the body goes dark**: the backlight off (**one bit**, AXP2101 `0x90` bit 7; `0x99` is untouched, because dimming would leave the panel glowing and what was asked for is 「真っ暗」), the twelve off, the neck limp.

- ⛔ **It is not a power cut and not deep sleep.** The radio, the sweep and the servo watchdog keep running, and **the panel keeps its drawing** — the lamp goes out over it.
- ✅ **Waking is a connection or a line on either wire**, counted **before** the body's mutex is taken, so a refused frame wakes it too; the last host light is remembered, or the body would come back in a darkness nobody asked for.
- ✅ **A half-open link is noticed in about 25 s** (`SO_KEEPALIVE` 10 / 5 / 3, plus `CONFIG_LWIP_TCP_KEEPALIVE=y`). ⛔ **It has never fired on the machine** — the one link that ended, ended closed.
- ✅ **Measured on the night of 2026-10-24**: the Mac itself was shut down, the eye saw the face go out after about five minutes, and the log puts the dark at **301 ± 1 s** after the host left. **125 s** after the host returned, the first line was `sleep: awake after 125 s — the host is back`, and **what came back was the face the panel had kept** (`records/2026-10-24-the-body-that-slept-itself.md`).
- ✅ **Two bench verbs let an eye look**: `bench sleep` holds the dark for **20 s** or until the next line, and `bench backlight on|off` takes the lamp alone — ⛔ *the write was taken* is not *the eye saw dark*.

### The two wires

**The console.** `{…}` frames, `pose …` lines, `bench …` verbs and `help`; `alive` printed every 3 s; **`bench` is refused while a pose stream runs** (a bench command blocks the task for seconds, and a pose that arrives late is not a pose). ⛔ **The console is the human's as well**, so no query is asked on a schedule — only at a moment a gesture needs one.

⛔ **On 2026-10-24 the console is gone**: `/dev/cu.usb*` does not exist at all. ⚠️ **Whether the cable was out or the port failed to re-enumerate is not established** — the same failure was recorded on 2026-10-21 — and **the next flash needs a physical replug.**

**The network.** ✅ **The station comes up from whatever the vendor's wizard left in NVS**, with WPA2-PSK; a dropped association is re-made after **2,000 ms, doubling to a 30,000 ms ceiling**, printing the first three attempts and then every tenth, and the drop's reason is printed once, on the first line. ✅ **Measured 2026-10-21**: carried about 50 m out of reach and back, `reason 200 (beacon timeout)` at 17:59:31.360, five attempts at 2 / 4 / 8 / 16 / 30 s, connected at 18:00:32.844, and the dial link back **6.24 s** after the address.

✅ **The board finds its host instead of assuming where it is**: the named address first, then its `/24` **nearest-first**, `.0` and `.255` skipped, **254 at most**, **30 s** between sweeps — and ⛔ **a missing route and a missing host are one failure to a socket**, so `kNoRoute` is answered first. **The host writes `loom\n` as the first line on every connection, and a candidate is accepted only if it greets** — because **the link is unauthenticated and an address is not an identity**.

⛔ **Which is the honest sentence: anything that can reach port 3333 and say `loom` can move the head, light the twelve and sound the speaker.** ✅ **`bench wifi …` and `bench dial …` are refused over the link** — a PSK on a plaintext socket is a PSK written on the wire.

⛔ **The board's `printf` lines do not cross the link; only `Say()` travels.** ⇒ **The host cannot hear the servo watchdog over the network** — its two numbers arrive only because `bench pos` answers carry a `servo` field.

## The host — one request, end to end

```
a hook event (33 of them)
  → /tmp/ekl-stackchan-next-<uid>.sock
  → the room → one Decision (phase, face, light, gesture, sound)
  → a frame {face, light, gesture, sound} on the board's own TCP connection
  → and, for the same `at`, a pose line streamed at 20 ms
  ← the board's own lines: `pose: N applied, M refused, K clamped`, `bench pos`, …
```

- ⛔ **A frame carries words and never numbers**; the pose line carries tenths of a degree. They are two line types, separated on the first word so that the frequent line cannot bury the rare one.
- ✅ **Every decision is logged, and every frame is logged with `sent`** — and with no board named, `sent` is `false` and the row names why (`ENOENT`, `EBUSY`, `EIO`, `short`).
- ⛔ **`sent: true` means the host's tty took the line, not that the board received it.** Since 0.19.41 the frame's acceptance is **the board's own line**, as `accepted`: `true`, `false`, or **`null` for a board that said nothing — which is not a refusal**.

### Layer 1 — the room (`projects/stackchan/`)

✅ **Six phases**: `present`, `greeting`, `working`, `blocked`, `closing`, `resting`. **Three ways of receiving an event** — a transition, evidence, or nothing.

- ✅ **The client rebuilds exactly `session` and `event`**, so a prompt cannot ride along; it prints nothing and exits 0 whatever happens — **a missing daemon is not a hook failure**.
- ✅ **Four channels**: the face and the light on every frame, **the neck at transitions only**, and the sound at four of the six transitions.
- ✅ **The numbers, all chosen and none measured**: one body move per **1.0 s**; an expression lasts **3.0 s**; a long turn is **20 s**; resting after **90 s**; concern after **3** consecutive failures.
- ✅ **One neck stays on one window.** A background window's event is reported `distant`: it keeps the room awake and changes nothing.
- ✅ **The state lives in the daemon** — the socket is the lock, and a second instance exits 3.

### Layer 2 — the work words (`projects/stackchan_next/`)

✅ **Six words, read from `tool_name` and nothing else**, on `PreToolUse` and `PostToolUse` only: `read`, `write`, `run`, `search`, `plan`, `other`. ⛔ **A row that carries no word is not counted as `other`** — absent is not the same as a fourth kind of work.

- ✅ **`write` → `writing` and `focused`; `run` → `busy` and `watching`; everything else and *not told* → `dim` and `curious`.** ⚠️ **The light and the face move in one decision** — the dwell, the forgetting at the end of a chapter and the refusal to follow a background window are one rule over two fields, so a frame cannot carry `busy` beside `focused`.
- ✅ **One failure wears `startled` for the same 2 s its light is `alert`**, and then returns to **the face this layer was showing** — ⛔ not to the base layer's field, which is `null` on a first failure and would leave the board wearing `startled`.
- ✅ **The light never changes faster than once per `WORK_DWELL` (5 s)**; `lively` shortens it to 2 s, and `quiet` pins it to `dim`. ⚠️ **A light that changed on every tool would be a mirror, not a companion.**
- ✅ **The word belongs to the chapter** and is dropped at `closing`, `present`, `resting` and `greeting` — ⛔ **not at `blocked`**, because a permission wait is inside the chapter.
- ✅ **One failure is `alert` for 2 s; three in a row are the room's `concern`** — the word is not increased, the length is. **Waking after 90 s adds one `pip`** and no gesture, because a second body floor is not this layer's to hold.
- ✅ **`quiet` suppresses all three** — the work lights, the flash and the pip.
- ⚠️ **One word is one word for the room**: a window that steals with `UserPromptSubmit` can wear the previous window's word until its first tool.

### Layer 3 — the meta words (`projects/stackchan_meta/`)

✅ **A turn is counted**, three rules run over it, and at most one candidate per session is kept.

- **`failure-loop`** — two failures in a row. **`context-pressure`** — 25 wide tool calls. **`turn-review`** — a turn that closes at **180 s** or at **25 calls**.
- ✅ **A budget of 900 s**, a **TTL of 600 s**, and cooldowns of **600 / 3,600 / 1,800 s** per word. Four drop reasons: `budget`, `cooldown`, `expired`, `superseded` — ⛔ **their sum is not the candidate count**, because `superseded` counts a conflict and not a loss.
- ✅ **One sentence, under one prelude, delivered as `additionalContext` on the next `UserPromptSubmit`** — the quietest hand-over, which is the moment the user speaks. The other thirty-two events send and close, because reading would make the turn wait on the daemon's speed.
- ✅ **Measured on the installed log: 11,137 rows over 12.32 h → 12 candidates, 3 delivered, 8 dropped** ⇒ **about three sentences in a working day.**
- ⛔ **Whether any of those three was worth saying is not recorded.**
- ⛔ **`eager` changes nothing this version can see** — no row carries the strength, and a test asserts that, so the day one starts to, the test will ring.

### The voice edge (`projects/stackchan/voice/`)

✅ **`python3 -m projects.stackchan.voice "…"`** — `say -v Kyoko`, then `afconvert` to 24 kHz 16-bit mono.

- **`PITCH = 8` on the `pbas` scale** — ⚠️ **not semitones.** The sign is kept, so `+3` and `−3` do not collapse.
- ✅ **The peak is normalized to the ceiling first, then multiplied by `GAIN = 0.75`** — one number for the size, and the ear is what moved it (0.5 → 0.75).
- ✅ **The pauses are the rule's and nowhere else**: **600 ms after 。 and 300 ms after 、**, made by synthesizing each segment, trimming its ends at the same threshold the measuring instrument uses, and joining with exactly that many zero frames. ⛔ **`say` already pauses at its own punctuation, so laying the rule on top counts twice** — measured 243.8 / 286.7 ms bare against 816.3 / 387.4 ms with the rule on top. **The sentence now measures 600.0 / 300.0 ms.**
- ⛔ **`Kyoko` is provisional — the ear decides.** And ⚠️ **whether the meta candidate may be spoken at all is still an open decision** (§17.4): the mouth is built, and one ruling is not.

### The mouth tool (`projects/stackchan_next/mouth/`)

✅ **One sentence, at most 80 characters** (⚠️ **a chosen number, not a measured one**), **one line, never truncated** — a longer or a wrapped sentence is refused rather than cut, because a cut sentence is a different sentence.

- ✅ **It prints exactly one word** — `queued`, `night`, `no-board`, `busy`, `refused:<code>`, `no-daemon` — and **exits 0 only for `queued` and `night`**. ⛔ **The opposite of the hook, which is silent on failure**: this tool exists to report that nothing was said.
- ✅ **The order of refusal is a rule**: read → **no board** → night → speaker. *No board* is a fact and not a rule, and a missing line must not cost a three-second synthesis.
- ✅ **Measured**: `queued` in **0.055 s**; one spoken sentence, 41 blocks, 164,294 bytes, `not played` 0, and the author heard it.
- ⛔ **No day has been measured with the mouth open.** One sentence is not a habit, and the forecast of about three a day is a count of candidates, not of utterances.

### The day instrument (`projects/stackchan/day/`)

✅ **One path in, counts out** — no clock and no second file. It counts starts, decisions, frames (sent / accepted / refused / unheard), streams, poses (planned / applied / late / held), verdicts and the board's own applied / refused / clamped, read-backs (heard / positions), the board's servo numbers (reports / silent / rail cycles / rail resets), five meta counters, six voice counters, three link counters, and the words (phases / works / faces / lights / sounds / gestures).

- ⛔ **`rail cycles` and `rail resets` are the two columns that are not tallies**: a count that goes down is a board reboot whose earlier cycles are unobservable.
- ⚠️ **A row shape it does not know is counted as `unreadable`** — which is why **a new row and its counter arrive on the same day, the counter first**. A new shape without a counter turns every day into *the log is broken*.

## Every word the body understands

**The frame** — one line, at most 256 bytes, four keys, an unknown key refused:

| field | words | `null` means |
|---|---|---|
| `face` | `curious` `greeting` `happy` `angry` `sleepy` `focused` `watching` `startled` | this frame says nothing about the face |
| `light` | `off` `dim` `writing` `busy` `breathe` `warm` `alert` `error` | — (a light is always a word) |
| `gesture` | `look_up` `nod` `look_side` `rest` `recoil` | this frame does not move the neck |
| `sound` | `hello` `pip` `chime` `fall` | this frame is silent |

**The pose line** — `pose <yaw_tenths> <pitch_tenths>*<CC>`, tenths of a degree, one per tick.

**The room** — six phases: `present` `greeting` `working` `blocked` `closing` `resting`.

**The work** — six words: `read` `write` `run` `search` `plan` `other`.

**The meta** — three words: `failure-loop` `context-pressure` `turn-review`.

**The mouth** — six answers: `queued` `night` `no-board` `busy` `refused:<code>` `no-daemon`.

**The console** — four line types (`{…}`, `pose …`, `bench …`, `help`), `alive` every 3 s, and **24 words after `bench`**: `pos` `zeros` `scan` `read` `raw` `state` `hold` `release` `sound` `audio` `volume` `leds` `backlight` `face` `sleep` `pmu` `level` `power` `timed` `wifi` `dial` `net` `set` `move`. ⚠️ **`help` prints 30 lines, not 24, because three of the words take a sub-verb** — `wifi` ×3 (`scan` / `join` / `addr`), `net` ×2 (`send` / `call`) and `dial` ×1 (`dial <ip> <port>`) — **six extra lines over three words, and 24 + 6 = 30 is the whole arithmetic** (counted in `main.cpp` on 2026-10-24, not recalled; the count moved from 23 to 24 when `face` arrived the same day).

## What it cannot do

1. ⛔ **It cannot promise the board answered.** `sent: true` is the tty taking the line. Acceptance is the board's own line, and it is sometimes `null`.
2. ⛔ **The servo bus silences itself with nothing asked of it.** Seven shapes were tried by command and all seven answered; the trigger is unnamed, and a recovery is not a diagnosis.
3. ⛔ **The positions land and the schedule does not** — most poses are applied late on every stream measured since 0.19.61.
4. ⛔ **The link is plaintext and unauthenticated.** Anything that reaches port 3333 and says `loom` can move the body.
5. ⛔ **The keepalive has never fired on the machine**, so *a half-open socket is noticed in about 25 s* is a reading of the source and not a measurement.
6. ⛔ **The twelve LEDs' return from sleep has no eye on record.**
7. ⚠️ **The USB console was gone on 2026-10-24 morning and is back** — `/dev/cu.usbmodem1101`, ⛔ **not the `.101` every record before it names**, because the port number moves with the port it is plugged into. **The rule stands: a flash is written only after `otadata` is read**, and the board can answer `bench pos` from an image that is not the one just written.
8. ⛔ **No day has been measured with the mouth open**, and whether a delivered meta sentence was worth saying is not recorded.
9. ⛔ **The goal is not verified.** One person in one room said 「そこに何かが居る」, at N=1, and ⚠️ **the session had offered that sentence a moment before** (`docs/verification-boundary.md`).
10. ⛔ **Nothing on this page says the body is alive.** Every ✅ above says a mechanism ran on the unit; ⛔ **not one of them is a judgement that anything is there.**

## Keeping this page true

⛔ **When a Stack-chan feature changes, this page changes in the same commit** — and it is named from `README.md` for that reason. **A capability documented a version late is a page that taught a reader the wrong surface.**

✅ **What rings**: `tools/check_i18n.py` holds the three mirrors together — existence, the version header, the `Language:` line, the heading sequence, and this page's presence in its `DOCS`. **The word sets themselves are held in code** by `tests/test_stackchan_wire.py`, which asserts that the codec, the contract and the firmware spell the same words.

⛔ **What does not ring**: the content of this page. **Nothing compares these tables with the tuples** — a word added to the code and not to this page leaves this page **green and wrong**, which is the shape this repository calls a defect. ⚠️ **The check that would catch it would have to parse prose**, and a checker that reads a copy is a checker that rings on the copy; so the cost is named here instead of paid.

**What was counted for this page.** The 24 dispatch words in `HandleBench` (and the 30 `help` lines, named above with their cut); the eight light words, eight faces, five gestures, four sounds, six phases, six work words, three meta words and six mouth answers, each read out of the source named beside it; the flags of the installed job, read from `ps`; and the three sockets, read from `ls`. **What was not counted**: any day of natural use, the room while the body works, and anything about whether it is alive.

⚠️ **This page holds no count of lines, rows or documents** — a count that nothing recomputes is a count that drifts, and the ones that must be re-counted already live in `CLAUDE.md`, `README.md` and `tests/README.md`.
