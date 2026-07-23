# StudyHelp — Domain Glossary

Shared vocabulary for the project. Use these terms (not synonyms) in code, issues,
and docs. See `docs/adr/` for decisions.

## Terms

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

- **Review source** — where a review's rating came from: `CARD` (card-player flow,
  trustworthy for calibration) or `CHAT` (tutor chat, approximate). See ADR-0001.

- **Trustworthy review** — a `CARD` review with a non-null predicted recall; the
  only kind that counts toward calibration.

- **Coverage** — how many trustworthy reviews back the dashboard, and how many
  were excluded as chat-sourced. Shown to the user so exclusions are transparent.
