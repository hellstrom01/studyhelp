# StudyHelp — Domain Glossary

Shared vocabulary for the project. Use these terms (not synonyms) in code, issues,
and docs. See `docs/adr/` for decisions.

## Terms

- **Subject** — the canonical term for a study area (open-ended and personal,
  e.g. "Linear Algebra"). "Course" is a deprecated synonym being renamed out of
  UI copy and parameters as code is touched.

- **Hours studied** — study-session work-interval time plus review-session
  active time. Breaks, calibration/setup chat, and post-timer card creation do
  not count.

- **Study day** — a calendar day with at least one study or review session;
  the streak counts consecutive study days, the heatmap shades days by total
  minutes.

- **Calibration** — the gap between *predicted recall* and *actual recall*. The
  core learning-quality metric (spec Part 4): is the user's sense of "I know this"
  becoming accurate? Measured as mean `|predicted − actual|`. Lower is better.

- **Predicted recall** — FSRS retrievability R for an item at review time (0–1),
  stored on each review as `predicted_recall`. The pre-attempt estimate.

- **Actual recall / outcome** — whether the retrieval attempt succeeded
  (`was_correct`), treated as 1.0 or 0.0 when paired against predicted recall.

- **Calibration bias** — signed mean of `(predicted − actual)`. Positive =
  **overconfident**; negative = **underconfident**; near zero = **well calibrated**.

- **Reliability diagram** — the calibration curve: predicted recall binned into
  deciles, each bin plotted as mean-predicted vs. actual accuracy against a 45°
  perfect-calibration line.

- **Review source** — where a review's rating came from: `CARD` (card-player flow)
  or `CHAT` (tutor chat). Records provenance and feeds coverage; trust is carried
  separately by the attribution flag. See ADR-0001, ADR-0003.

- **Attribution (exact)** — a review is *exactly attributed* when its predicted
  recall and outcome provably refer to the same item. Always true for `CARD`
  reviews and for `CHAT` reviews resolved to the item the tutor actually quizzed;
  false/absent for legacy approximate chat rows. Stored as `attribution_exact`.

- **Trustworthy review** — an exactly-attributed review with a non-null predicted
  recall; the only kind that counts toward calibration. Either source qualifies.

- **Coverage** — how many trustworthy reviews back the dashboard, and how many
  chat reviews were excluded (legacy/unattributed). Shown to the user so
  exclusions are transparent.

- **Item** — the canonical term for a reviewable unit (7 types: concept Q&A,
  theorem trigger, worked example, hidden problem, code-from-scratch, Feynman
  prompt, cloze). "Flashcard" is the user-facing synonym; code and docs say Item.

- **Self-assessment** — the user's own 4-grade rating of a retrieval attempt
  (Forgot / Struggled / Got it / Easy, mapping to FSRS Again/Hard/Good/Easy).
  In review sessions the user always decides the outcome; the LLM's feedback on
  a typed answer is commentary and never writes a rating. (In tutor chat, the
  tutor's eval decides — see Review source.)

- **Classification** — the LLM filing user-authored content: assigning an Item's
  topic (creating one if needed) and suggesting its type. Classification is not
  authoring; the user's words are never rewritten by it.

- **Topic** — the grouping level between Subject and Item. Maintained by
  classification, not by the user; exists to give interleaving its topic
  diversity signal.

- **Card draft** — an LLM-proposed Item generated from session notes/summary.
  A draft enters the deck only after the user edits/accepts it; nothing is
  reviewable without explicit user approval.

- **Study session** — the timed, Pomodoro-structured mode for encoding new
  material: tutor chat + notes + reflections. Produces no Review rows
  (ADR-0004).

- **Level check** — the untimed phase before a study session's timer starts.
  New subject: the tutor asks questions to gauge the student's level.
  Continuing subject: it recaps from subject memory and confirms today's focus.
  Never called "calibration" — that word is reserved for the recall metric.

- **Review session** — the retrieval-practice mode: typed answers to due Items,
  LLM commentary, user self-assessment. The only producer of new Review rows.

- **Reflection** — the closing minutes of each work interval, where the student
  recaps what they just learned and the tutor responds with probing questions,
  not corrections. Consolidation, not retrieval practice — never confuse with
  Review. The final interval's reflection covers the whole session and feeds
  the session summary.

- **Session summary** — a short LLM-written recap of one study session (from the
  transcript, the user's notes, and the user's own wind-down summary). Stored
  per session; surfaces in recent activity and in future recaps.

- **Subject memory** — the tutor's running private notes on the student for one
  subject: level, gaps, misconceptions, topics covered. LLM-written and
  LLM-read, rewritten (not appended) after each session, capped in length.
  Viewable by the user; not primarily user-edited.
