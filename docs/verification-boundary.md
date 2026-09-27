<!-- i18n-version: 1.0.0 | canonical: docs/verification-boundary.md | translated: 2026-09-27 -->

**Language:** [English](verification-boundary.md) | [日本語](verification-boundary-ja.md) | [中文](verification-boundary-zh.md)

# The Verification Boundary

**This is the most load-bearing document in this repository.** Everything else here describes a mechanism. This one says **which claims the mechanism can support and which it cannot** — and the second list is longer than anyone wants it to be.

## The rule this document exists to hold

**Split the word "verified" in two before using it once.**

| name | what it rests on | what it licenses you to say |
|---|---|---|
| **verification of the mechanism** | deterministic trajectory computation, range checks, measured latency | **"the trajectory was computed as instructed"** |
| **verification of the goal** | ⚠️ nothing established — see the last ground below | **"there is something there"** |

⚠️ **These two must be called by different words.** "Everything passed in the Mock" is not to be read as "it works." Five green checks mean the mechanism computes what it was told to compute. **They mean nothing about whether anything is there.**

## The six grounds

**Why the two cannot be collapsed — six grounds.**

⚠️ **Sources are cited by author and year.** The design survey behind this project is not distributed with this repository, so the section numbers it uses are not repeated here; **each ground below can be checked against the source itself.**

1. **The leading figure in presence measurement wrote that it cannot be measured by questionnaire** (Slater 2004). Self-report is itself the disputed thing.
2. **And the standard presence scale could not distinguish the real from the virtual** (Usoh et al. 2000). **This is a measurement, not an aphorism.**
3. **Animacy is decided by local motion, not by the configuration of motion** (Troje & Westhoff 2006). **So "the trajectory is correct" is not evidence of animacy — that is a different level.** ⚠️ Note carefully what this does *not* say: it does not excuse the trajectory from being correct. It says correctness is not the currency the other account is kept in.
4. **The face alone does not determine the emotion** (Meeren 2005; Aviezer 2012). **And when face and body disagree, presence itself drops** (Bailenson et al. 2005). **So "the face rendered correctly" is not evidence that it reads as one creature** — and this repository's face is ASCII, driven by the same clock as the body.
5. ⚠️ **A candidate definition of the goal does exist** — Stern et al. 1985, "**qualities of feeling that distinguish animate from inanimate**". **But Stern left no instrument for it.** ⚠️ What did arrive is an observation, not a measurement: Hoffman, in IEEE Spectrum (2019), on a skilled engineering professor who smiled at his own robot's odd gesture and **"briefly suspended his belief that this was just a collection of motors and control signals"**. **⇒ behaviour, not scale. ⚠️ Not a controlled measurement.**
6. ⚠️ **And a study that measured the goal at N=1, in a home, was not found.** **Beyond the line, there is no established method.** **This is a blank in this project, and it is written here as a blank.**

⚠️ **Some of those sources were read in the original, some through an abstract, and some through secondary discussion.** **The strength of a ground is the strength of how it was read** — and where the reading was indirect, the ground is correspondingly weaker.

## Why the mechanism is the easy side

**Because a trajectory is a function.** The same input produces the same output, so the deterministic core — interpolation, easing, smoothing, limiting — can be checked exactly, and a failing check can be told apart from a passing one. Almost nothing else in this workshop is in that position.

⚠️ **But "easy" is not "done", and it is not "safe".** The mechanism's checks say what arithmetic was performed. They do not say what the machine did. **Only the machine says that, and it does not report back.**

## The sentence

**This sentence is placed on the first day, on purpose.** Added later, it would arrive after the checks had gone green — and a green check is read as "it works".

> **The goal of this Pet cannot be verified in this workshop. Only the mechanism can be verified. For the goal, only a record of observations remains.**

**It is fixed. It lives in `CLAUDE.md` and `CLAUDE-ja.md`, and it is what this document exists to be the reasoning for.**

⚠️ **The wording is load-bearing in one place:** the goal is **not** declared unreal, and it is **not** declared beyond measurement by anyone. It is declared **unmeasured here**. Those are three different claims, and only the third is made.

## What follows for the work

- **When you write "verified", name which of the two you mean.** Unqualified, the word is read as the second, and only the first is available.
- **Do not raise contingency as a goal.** A faster reply looks like an improvement, and can read as less autonomy (Yamaoka et al. 2007). ⚠️ That warning is a secondary reading, and this project's interaction is simple.
- **Latency is a design constraint, not a substitute for the goal.** The numbers collected are 200 ms (Stivers et al. 2009), 200–3000 ms (Fischer et al. 2013), −30 to +170 ms (the audio–video fusion window), and about 700 ms (the response delay felt as optimal). ⚠️ **None of them is a face-and-body value.** They constrain the design; they do not measure the goal.
- **The record is the method.** What remains for the goal is a dated record of observations, and the design of that record — what is written down, and on which day — is part of the apparatus, not an afterthought.

## What this document does not do

⚠️ **It does not conclude that the Pet is a machine and nothing more.** It concludes that **this workshop cannot settle the question**, and that pretending otherwise would be the one failure that is entirely within our control.

⚠️ **It does not verify anything either.** Nothing is implemented. There is no trajectory to check and no check to run — **and this document must not be read as evidence that there will be.**
