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
