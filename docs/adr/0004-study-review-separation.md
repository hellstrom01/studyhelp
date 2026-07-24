# ADR-0004: Study and review are separate modes; chat no longer logs reviews

Status: Accepted (2026-07-24)

Amends ADR-0001 and ADR-0003.

## Context

The tutor chat has doubled as the review mechanism: due items were injected into
the study chat's context, the tutor quizzed them, and its hidden `<eval>` block
was logged as an FSRS review (source `CHAT`). ADR-0001 and ADR-0003 exist to
make those chat-originated reviews trustworthy via exact attribution.

The app is being reshaped around two distinct modes: **study sessions** (Pomodoro
+ Socratic tutor + notes, for encoding new material) and **review sessions**
(typed-answer flashcards with user self-assessment, for retrieval practice).

## Decision

Clean separation: **study chat teaches, review sessions retrieve.**

- The study-session tutor no longer receives due items and no longer emits
  `<eval>` blocks; no FSRS reviews are written from chat.
- All new scheduling and calibration data comes from review sessions
  (source `CARD`, exactly attributed by construction). The user's 4-grade
  self-assessment is the rating; the LLM's feedback on a typed answer is
  commentary and never writes a rating.
- `Review.source == CHAT` and the ADR-0003 attribution machinery
  (`item_ref` resolution, `attribution_exact` on chat rows) become legacy:
  existing rows keep their meaning, but no new CHAT reviews are produced.

## Considered options

Keeping the hybrid (tutor weaves due items into study chat) preserved the
ADR-0003 investment, but muddied both modes: the tutor juggling "teach today's
material" and "quiz the due deck" in one conversation is precisely what made
attribution painful, and it left calibration data with two trust classes.

## Consequences

- Calibration data becomes uniformly trustworthy; the coverage split
  (trusted vs excluded-chat) stops growing on the excluded side.
- ADR-0003's resolver and eval parsing can be deleted from the chat path once
  the new review flow lands; the `attribution_exact` flag stays (CARD reviews
  still set it) and legacy rows stay excluded, unmigrated.
- Retrieval practice only happens when the user runs review sessions, so the
  dashboard should keep due counts visible to prompt them.
