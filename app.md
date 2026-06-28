Part 1 — The Evidence Base (why this method exists)

Decades of research converge on a short list of techniques that actually produce durable learning, and an equally important list of popular techniques that mostly produce the feeling of learning. The app's entire job is to push you toward the first list and away from the second.

1.1 The two highest-utility techniques: retrieval practice + spaced practice

The most-cited review of study techniques (Dunlosky, Rawson, Marsh, Nathan & Willingham, 2013) graded ten common strategies. Only two earned "high utility" across subjects, ages, and materials: practice testing (a.k.a. retrieval practice or active recall) and distributed practice (spacing study over time). A large meta-analysis replicated this conclusion (Hattie & Donoghue, 2021; 242 studies, ~169,000 participants): distributed practice and practice testing came out on top. Typical effect sizes are large for a learning intervention — practice testing around d ≈ 0.7.
 

Retrieval practice / active recall. Trying to pull information out of memory strengthens it far more than putting it back in by re-reading. Roediger & Karpicke (2006) showed that students who tested themselves retained much more a week later than students who restudied. Karpicke & Blunt (2011, Science) found retrieval practice beat elaborate concept-mapping — even when the final test was building a concept map. The act of retrieving is the mechanism, not just "engaging deeply."
Spaced / distributed practice. Reviewing material across several sessions beats cramming the same total time into one. This goes back to Ebbinghaus's forgetting curve: memory decays predictably, and each well-timed review flattens the curve. The ideal gap is long enough to make recall effortful but short enough that you still succeed.
They are two halves of one tool. The strongest results come from spaced retrieval practice — testing yourself, repeatedly, at increasing intervals. This is exactly what a spaced-repetition system automates (see §5.4 on the FSRS algorithm). Note an honest caveat for math specifically: meta-analyses find the spacing benefit is real but sometimes smaller in math than in other domains, and pure retrieval-practice evidence in math is thinner (fewer studies). For math the heavier lever is interleaving (next).


1.2 Interleaving (the single most important technique for math problem-solving)

Most textbooks are "blocked": a lesson on the quadratic formula, then twenty quadratic problems in a row. You already know the method before you read each problem, so you only practice executing a strategy — never choosing one. Interleaving mixes problem types within a session so each problem forces you to first ask "what kind of problem is this?" — which is the actual skill tested on exams and used in real work.

The evidence is unusually strong because it includes classroom randomized controlled trials (the gold standard). Rohrer, Dedrick, Hartwig & Cheung (2020) ran an RCT in real middle-school math classes: a heavier dose of interleaved practice produced 61% vs 38% on a later unannounced test (d ≈ 0.83 — very large). The mechanism is discrimination: you can't reliably pair a problem with the right strategy until you can tell that kind of problem apart from similar-looking ones (Rohrer, 2012; Foster et al., 2019). Interleaving costs nothing extra — it's just a reordering of the same problems.

1.3 Cognitive Load Theory and worked examples (how to learn a new skill efficiently)

Working memory is tiny — it holds only about 4 (Cowan, 2001) to 7 chunks of new information at once — while long-term memory is effectively unlimited. Learning fails when working memory is overloaded. Cognitive Load Theory (Sweller, 1988; Sweller, van Merriënboer & Paas, 2019) is the design rulebook for staying under that limit.


The worked-example effect. For a novice at a topic, studying fully worked-out solutions produces better learning and transfer — with less time and effort — than diving straight into solving problems (Sweller & Cooper, 1985). Throwing a beginner at unfamiliar problems forces inefficient trial-and-error ("means-ends analysis") that burns working memory on search instead of on building the mental schema. So: study a worked example, then solve a similar problem — and use example→problem pairs, not examples alone.
The expertise-reversal effect. This flips as you improve. Once a schema exists, continuing to study worked examples becomes redundant and even slows experts down; they should switch to solving problems themselves (Kalyuga & Renkl, 2009). The app must therefore fade support as competence grows (full example → partially worked "completion" problem → blank problem).
Self-explanation. Prompting yourself to explain why each step in an example works deepens learning substantially (self-explanation effect, g ≈ 0.55; Renkl). It's the difference between watching a solution and understanding it.
Split-attention. Keep related information together. A diagram with its labels integrated beats a diagram and a separate legend you must mentally cross-reference (Chandler & Sweller). The app should never make you hold one thing in mind to interpret another.


1.4 Desirable difficulties and the illusion of competence (why easy studying fails)

Robert and Elizabeth Bjork's central insight: the conditions that make studying feel easy and fluent are usually different from the conditions that make learning stick (Bjork & Bjork, 2011, 2020). They distinguish:


Storage strength (how well something is learned) vs retrieval strength (how easily you can access it right now). Re-reading pumps up retrieval strength temporarily, which feels like mastery, but barely touches storage strength — so it evaporates by exam day. This is the illusion of competence (Koriat & Bjork, 2005): fluency is mistaken for knowledge.
Performance ≠ learning. Doing well during a study session can be a bad predictor of long-term retention. Methods that make practice harder in the moment — spacing, interleaving, self-testing, varying conditions — depress short-term performance but boost long-term learning. These are the four desirable difficulties.
The Goldilocks rule. A difficulty is only desirable if you can ultimately overcome it. Make it too hard and it backfires (this is where Cognitive Load Theory and Bjork meet). The app's job is to keep you at the edge of your ability — effortful but achievable — not drowning.


Direct consequence for the app: re-reading, highlighting, and passively re-watching lectures are explicitly low-utility (Dunlosky, 2013) and should be designed out. Every interaction should require the user to generate, retrieve, or explain.

1.5 The neuroscience of consolidation (why sleep and spacing literally work)

Why does spacing work at the biological level? Because forgetting a little and then re-learning, with sleep in between, is how memories get physically consolidated.


Memory moves from hippocampus to cortex. A new memory is first encoded in the hippocampus, then gradually transferred to and stabilized in the neocortex for long-term storage (systems consolidation).
Sleep is when this happens. During slow-wave (NREM) sleep, the hippocampus "replays" the day's experiences during bursts called sharp-wave ripples, driving the hippocampal–cortical dialogue that converts fragile new traces into durable ones (Diekelmann & Born; recent reviews 2023–2025). The amount of learning during the day predicts the amount of replay at night. Sleep deprivation measurably disrupts this consolidation.
Therefore: spacing works partly because it inserts sleep between sessions. Practical rules the app should encode: study (especially review) shortly before sleep; protect 7–9 hours; treat an all-nighter as actively anti-learning, not neutral.
Body matters too. Aerobic exercise supports hippocampal health and memory; chronic stress and sleep loss impair it. Brief movement breaks are not wasted study time.


1.6 Focus, chunking, and procrastination (the practical layer)

Barbara Oakley's A Mind for Numbers / "Learning How to Learn" (the most-enrolled MOOC ever, co-taught with Terrence Sejnowski) packages much of the above for technical learners and adds a useful practical frame:


Focused vs diffuse mode. Tight concentration (focused) is needed to encode new material; a relaxed, mind-wandering state (diffuse — walks, showers, sleep) is when the brain connects ideas and cracks stuck problems. You need both, alternated. Practically: when stuck, stop grinding and step away — the diffuse mode keeps working in the background.
Chunking. Expertise is building ever-larger "chunks" — compact, automatic units of meaning (e.g., a fluent coder reads a whole loop as one idea). You build chunks by focused practice + understanding + retrieval, then assemble small chunks into bigger ones (bottom-up) while keeping the big picture in view (top-down).
Procrastination is pain avoidance. Anticipating an unpleasant task activates a pain-related response, so you flee to something comfortable. The fix is to focus on process, not product (commit to "25 focused minutes," not "ace the exam") and lower the activation energy to start. The Pomodoro Technique (Cirillo) — ~25 min focused work, distraction-free, then a short diffuse break — is the standard tool.
Mindset. Oakley's own arc (math-phobic linguist → engineering professor) is the case study for the well-known finding that strategy and persistence, not fixed "math genes," drive technical success.


1.7 The full toolkit, ranked

TechniqueWhat it isEvidenceBuild priorityRetrieval practice / active recallRecall from memory instead of re-readingHigh utility (Dunlosky 2013); d ≈ 0.7CoreSpaced practice (FSRS)Review at expanding intervalsHigh utility; the spacing effectCoreInterleavingMix problem types in a sessionClassroom RCTs; d ≈ 0.83 in mathCore (esp. math)Worked examples → faded practiceStudy solutions, then solve, fading supportWorked-example & expertise-reversal effectsCoreSelf-explanation / FeynmanExplain why, in your own words; teach itg ≈ 0.55; generation effectHighDual codingPair words with visuals/diagramsPaivio (1986)MediumConcrete examplesTie abstractions to multiple examplesDunlosky (2013)MediumSleep / spacing-with-sleepConsolidate via NREM replayStrong neuroscienceCore (nudges)Pomodoro / focused-diffuseTime-boxed focus + diffuse breaksAttention & procrastination researchHigh (UX)Re-readingPassive reviewLow utilityDo not buildHighlighting / underliningMarking textLow utilityDo not buildCramming / massingOne long sessionLoses to spacingActively discourage


Part 2 — The Study Method (the loop the app runs)

This is the concrete procedure the app operationalizes. Think of it as four nested loops.

Loop A — Learning something new (a single concept or skill)


Prime (2 min). Skim the material once for structure only — headings, the shape of the argument, what questions it answers. Don't try to memorize. This builds a scaffold so new details have somewhere to attach.
Study a worked example. For a problem-solving skill, read a fully worked solution slowly. For a concept, read the explanation once.
Self-explain. Before moving on, force generation: explain each step's why in your own words. If you can't, that's a located gap — go back to just that piece.
Encode as retrievable items. Turn the material into things you can later be tested on (see item types in §5.2): concept Q&A, a theorem and when to use it, a worked example you can reproduce, a problem with a hidden solution.
First retrieval, closed-book. Immediately reproduce the example / answer the question without looking. Getting it wrong now is good and expected — error-driven correction is part of the mechanism.
Chunk it. Once you can reproduce it, name the pattern ("this is a "complete the square" problem") so it becomes one unit you can recognize later.


Loop B — The Feynman / gap-finding pass (for deep understanding)

For anything conceptual, run the Feynman Technique — it bundles retrieval, self-explanation, generation, and dual coding at once (and meta-analyses back each ingredient):


Pick one concept that fits on a page.
Explain it out loud / in writing as if teaching a beginner, from memory, no notes, no jargon. (Aim for ~60–120 seconds.)
Wherever you stall, hand-wave, or fall back on jargon you can't unpack — that's a blind spot. Mark it.
Go back to the source for only those spots, then re-explain. Repeat until it's simple and gap-free.
Add an analogy and a quick diagram (dual coding).


The app can act as the "student" you teach: you explain, it probes with "why" / "what if" / "explain that term" follow-ups and flags hand-waving. (This is essentially "Feynman 2.0" with an AI tutor.)

Loop C — The daily session (mixing it all together)

A single day's work = a short batch of new learning (Loop A/B) + a review queue of everything due today, interleaved.


Reviews come first or are interleaved with new material — never skipped. The scheduler (FSRS) decides what's due.
Interleave deliberately. The review queue mixes item types and topics. For problem sets, never serve many of the same problem type back-to-back; shuffle so the user must identify the type each time.
Closed-book retrieval, then self-grade. For each item: attempt from memory → reveal answer → rate how it went (this rating feeds the scheduler).
Time-box with Pomodoros. ~25 min focused, distraction-free, then a 5-min diffuse break (walk, look out a window — not social media, which doesn't engage diffuse mode). When stuck on a hard problem, take the break deliberately to let diffuse mode work.
Effort calibration. The session should feel effortful but not crushing (desirable-difficulty zone). If everything is trivially easy, intervals are too short or material is too easy; if you're failing most items, slow down and add worked-example support.


Loop D — The long game (weeks to a course)


Trust the spacing schedule. Items you find hard come back sooner; easy items drift to weeks/months out. Over a term this replaces cramming entirely.
Sleep is part of the protocol. Do a light review near bedtime; protect 7–9 hours; never trade sleep for a cram session — you'd be deleting the consolidation that makes the studying count.
Cumulative interleaving before exams. Instead of re-reading, do mixed problem sets spanning the whole course so you keep practicing strategy-selection across all topics.
Track calibration, not just streaks. The valuable metric is the gap between predicted recall and actual recall — i.e., is the user's sense of "I know this" becoming accurate? Shrinking that gap is real learning (and directly attacks the illusion of competence).



Part 3 — How the Three Subjects Differ

The core engine is shared, but weight the techniques differently per subject.

Math (and proof-heavy / theoretical courses)


Interleaving is the top priority. Build mixed problem sets where consecutive problems require different methods (see §1.2). This is the highest-leverage single feature for math.
Worked examples → faded steps. Math is where the worked-example and completion-problem progression matters most. Show full derivations, then blank out steps progressively.
Cards for the conceptual layer. Definitions, theorems, and when each theorem applies (the "trigger condition") work well as spaced-repetition items. Memorizing a theorem's statement is useless without practicing recognizing when to reach for it.
Re-derive, don't re-read. Treat key formulas/proofs as things to reproduce from scratch on a blank page (retrieval), not to look over.


Computer Science / Programming


Beware "tutorial hell." Watching tutorials and following along feels productive but is passive re-reading in disguise. The retrieval equivalent is writing code from scratch, closed-editor, then checking. Build this in.
Two distinct skills, two modes. (a) Knowledge — syntax, APIs, data structures, algorithm patterns, complexity, vocab — is perfect for spaced-repetition cards. (b) Skill — designing and writing working programs — needs deliberate practice: study a worked solution, reproduce it, then solve variations. Interleave problem patterns (don't grind 20 of the same LeetCode category in a row).
Debugging = self-explanation. "Rubber-duck debugging" (explaining your code line-by-line to an inanimate listener) is literally the self-explanation effect. The app can be the duck.
Projects for transfer + motivation. Spaced cards keep fundamentals sharp; small projects force you to assemble chunks and stay motivated. The instant feedback of a compiler/test suite is built-in retrieval feedback — lean on it.


Physics / Engineering / other quantitative science


Concepts before plug-and-chug. Many students memorize equations and fail transfer. Prioritize self-explanation of the underlying principle and why an equation applies before drilling.
Dual coding is high-value. Free-body diagrams, circuit sketches, field lines — pair every concept with its canonical diagram; integrate labels into the figure (avoid split-attention).
Interleave problem types exactly as in math, and use worked-example fading for multi-step derivations.



Part 4 — Design Principles for the App

Encode these as non-negotiable product rules:


Every interaction is active. No screen rewards passive consumption. The default verb is retrieve / generate / explain, never re-read.
Make the right thing the easy thing. The scheduler decides what's due so the user never has to plan what to review. Lower activation energy to start (one tap to begin today's session) to fight procrastination.
Surface difficulty honestly. Show calibration (predicted vs actual recall), not just streaks and XP, so users learn to distrust the fluency illusion. Celebrate effortful sessions, not easy ones.
Fade support automatically. Track per-skill competence and move users along the worked-example → completion → blank-problem ladder. Don't keep showing experts beginner scaffolding (expertise reversal).
Interleave by default. The queue mixes topics and item types unless the user is in an explicit "first acquisition" drill.
Respect the body. Pomodoro timing with enforced diffuse breaks; bedtime-review nudges; "you've studied 2h, sleep beats one more rep" prompts. Gentle, not nagging.
Errors are data, not failures. Framing of wrong answers is encouraging and corrective; a miss schedules the item sooner rather than punishing the user.



Part 5 — App Specification (build this)

This is the buildable spec. It is intentionally implementation-agnostic; pick a stack you like (a sensible default is suggested in §5.7).

5.1 Core objects / data model

User
  id, displayName, settings(targetRetention=0.90, dailyNewLimit, dailyReviewLimit,
    pomodoroFocusMin=25, breakMin=5, sleepReminderTime), createdAt

Subject            // e.g. "Calculus II", "Algorithms"
  id, userId, name, type(MATH | CS | SCIENCE | OTHER), color

Topic              // e.g. "Integration by parts" — used for interleaving + analytics
  id, subjectId, name, parentTopicId(nullable)   // tree for prerequisites

Item               // the atomic unit of study (see types in 5.2)
  id, topicId, type, front, back, workedSteps[](ordered, each hideable),
    diagramUrl(nullable), difficultyTag, sourceRef
  // FSRS memory state lives here:
  fsrs: { stability, difficulty, due, lastReview, reps, lapses, state }

Review             // one logged retrieval attempt (append-only; trains FSRS + analytics)
  id, itemId, userId, ratingGiven(AGAIN|HARD|GOOD|EASY),
    predictedRecall, wasCorrect(bool), responseMs, reviewedAt

Session
  id, userId, startedAt, endedAt, itemsSeen, newCount, reviewCount,
    pomodorosCompleted, avgCalibrationError

ExplanationLog     // for Feynman / self-explanation mode
  id, itemId, userId, transcript, gapsFlagged[], reviewedAt

5.2 Item types (what a "card" can be)

The app is not just flashcards. Support at least:


Concept Q&A — front question, back answer. (definitions, facts, vocab)
Theorem / rule + trigger — front: a situation; back: which theorem/method applies and why. (trains strategy selection — critical for math/physics)
Worked example (reproducible) — an ordered list of solution steps, each individually hideable. Used for faded practice: reveal 100% → 50% → 0% of steps as competence rises.
Problem with hidden solution — a full problem; user solves closed-book, then reveals and self-grades. The backbone of interleaved problem sets.
Code-from-scratch — a spec/signature; user writes code without the answer visible; optional auto-check against tests; then reveal reference solution. (CS)
Self-explanation / Feynman prompt — "Explain X to a beginner." Free-text or voice; the app (optionally via an LLM tutor) probes for gaps and logs them.
Cloze / step-deletion — a derivation or code block with blanks to fill (completion problems; the middle rung of the fading ladder).


5.3 The daily session flow (the heart of the app)

START SESSION
  1. Build today's queue:
       due_reviews   = all Items where fsrs.due <= now  (capped at dailyReviewLimit)
       new_items     = up to dailyNewLimit new Items, prereqs satisfied
  2. INTERLEAVE the queue:
       - shuffle so no two consecutive items share the same Topic (when possible)
       - mix item types; never serve a run of the same problem type
       - new items are introduced via Loop A (worked example -> self-explain -> first retrieval)
  3. Run Pomodoro timer (focusMin). For each item:
       a. Present prompt. Hide the answer/steps. (closed-book retrieval)
       b. User attempts from memory (types, writes, codes, or explains).
       c. Reveal answer / reference / remaining steps.
       d. User self-rates: AGAIN / HARD / GOOD / EASY.
            (optionally auto-grade code items via tests -> map to rating)
       e. Log a Review row. Update Item.fsrs via the scheduler (5.4).
       f. Record predictedRecall (pre-attempt) vs wasCorrect for calibration.
  4. On focus-timer end -> enforce a DIFFUSE break (breakMin): suggest walk/stretch,
       block doom-scroll. Resume for another Pomodoro or end.
END SESSION -> write Session summary (calibration, counts) + schedule next.

Hard problems get a "stuck" button → offers a hint, or suggests taking the diffuse break and returning (don't reward grinding). Fading is automatic: as an Item's stability/competence grows, worked-example items reveal fewer steps up front.

5.4 The scheduling engine — use FSRS (do not hand-roll SM-2)

The review timing is the most important algorithm in the app. Use FSRS (Free Spaced Repetition Scheduler), not the legacy SM-2 algorithm. FSRS is the current state of the art: on benchmarks over hundreds of millions of real reviews it needs ~20–30% fewer reviews than SM-2 for the same retention, and it avoids SM-2's well-known "ease hell" failure mode. It became Anki's default in late 2023.

How FSRS models memory (the "DSR" model):


Difficulty (D): how intrinsically hard this item is for this user (≈1–10), updated each review (uses mean-reversion, which is what kills "ease hell").
Stability (S): number of days for recall probability to fall to the target retention. Grows after correct reviews, drops after lapses.
Retrievability (R): predicted probability you can recall the item right now, ≈ R = 0.9 ^ (days_since_review / S) at a 90% target.
You set a target retention (default 0.90). FSRS schedules each item's next due date for the moment R is predicted to hit that target — i.e., right as you're about to forget.


Implementation guidance — don't reinvent it. Use the maintained open-source libraries:


Python: py-fsrs (pip install fsrs)
TypeScript/JS: ts-fsrs (npm i ts-fsrs)
Rust: fsrs-rs


The flow per review: pass the item's current memory state + the user's rating (Again/Hard/Good/Easy) + elapsed time to the library; it returns the updated {stability, difficulty, due}. Persist that on the Item. Once a user has accumulated enough reviews (~1,000+), optionally run the library's optimizer on their Review history to fit personalized parameters; until then, ship the well-trained defaults (FSRS-6 default parameters were trained on ~700M reviews and already beat SM-2 for ~99% of users).


One subtlety worth honoring: FSRS is validated mainly on recall-style flashcards. For multi-step problem-solving items, treat the user's self-rating as the signal and still let FSRS schedule them — but lean harder on interleaving (5.5) for those, since that's where the math-specific evidence is strongest.



5.5 The interleaving engine

A distinct, deliberate piece of logic (this is what makes it a STEM app, not generic flashcards):


Tag every Item with a Topic and type.
When assembling any queue (reviews or a generated practice set), maximize topic/type alternation: greedily order items so adjacent items differ in topic and type whenever the due-set allows.
Provide a "mixed problem set" generator: pick N due/eligible problem-items spanning many topics, shuffle, present with type hidden so the user must identify the method themselves. This is the exam-simulation and pre-test mode.
Avoid the trap of "blocked review" where one topic's cards all cluster because they were learned together — shuffle across creation order.


5.6 Screens (minimum viable set)


Today / Home — one big "Start session" button (low activation energy), today's due count, new-items count, a calm streak/calibration summary.
Session player — the 5.3 flow: prompt → input → reveal → self-rate, with the Pomodoro timer and break enforcement.
Add / import material — create Items by type; ideally bulk import; optionally an "AI generate items from notes/PDF" helper (turn pasted notes into concept Q&A, theorem-trigger, and problem items).
Feynman / Explain mode — pick a concept, explain from memory (text or voice), get probing follow-ups, log flagged gaps as new Items.
Mixed practice / exam sim — generate an interleaved problem set across chosen topics.
Insights — retention over time, calibration (predicted vs actual recall), topics that need work, upcoming review load, sleep/consistency nudges. Emphasize calibration and effort over raw streaks.
Settings — target retention, daily limits, Pomodoro lengths, sleep-reminder time, subject management.


5.7 Suggested stack (optional, swap freely)


Frontend: React/Next.js or React Native (mobile matters for daily-habit apps).
Backend/DB: SQLite/Postgres; the schema in 5.1 maps cleanly to either.
Scheduler: ts-fsrs (if TS app) or py-fsrs (if Python backend) — see 5.4.
Optional LLM tutor: powers Feynman-mode follow-ups, gap detection, and "generate items from notes." Keep it optional; the core method works fully offline.
Build order for Claude Code: (1) data model + FSRS scheduler + a single review loop you can run in a terminal/test; (2) the daily-session player with interleaving + Pomodoro; (3) item creation/import; (4) Feynman mode; (5) insights/calibration; (6) polish + mobile.



Part 6 — Anti-Patterns (do NOT build these)

Building the wrong features actively teaches users the illusion of competence. Avoid:


Passive re-reading / re-watching as a "study" action. Low utility (Dunlosky, 2013). If you must show reference material, it's only ever after a retrieval attempt.
Highlighting/underlining tools framed as studying. Low utility; feels productive, isn't.
Blocked practice by default (all of one topic in a row). It inflates in-session performance and wrecks transfer. Interleave.
Cram mode / "review everything before the exam." Don't optimize for massing. If a user is behind, surface the most-overdue, highest-value items via the scheduler, and nudge toward spacing earlier next time.
Pure streak/XP gamification with no calibration. Rewarding daily streaks alone can reward easy, low-value sessions. Always pair engagement metrics with a learning metric (calibration, retention).
Hand-rolled SM-2 or naive "show again in 1/3/7 days" boxes. Strictly worse than FSRS and prone to ease-hell. Use a maintained FSRS library.
Punishing wrong answers. Errors drive learning; the UX should treat a miss as "scheduled sooner," not as a loss.
Letting easy = good. If a user breezes through, that's a signal intervals are too short or material too easy — not a success to celebrate.



References (key sources)


Dunlosky, J., Rawson, K. A., Marsh, E. J., Nathan, M. J., & Willingham, D. T. (2013). Improving Students' Learning With Effective Learning Techniques. Psychological Science in the Public Interest.
Hattie, J., & Donoghue, G. (2021). A Meta-Analysis of Ten Learning Techniques (replicating Dunlosky et al.).
Roediger, H. L., & Karpicke, J. D. (2006). Test-Enhanced Learning. Psychological Science.
Karpicke, J. D., & Blunt, J. R. (2011). Retrieval Practice Produces More Learning Than Elaborative Studying. Science.
Rohrer, D., Dedrick, R. F., Hartwig, M. K., & Cheung, C. N. (2020). A Randomized Controlled Trial of Interleaved Mathematics Practice. Journal of Educational Psychology.
Rohrer, D. (2012). Interleaving Helps Students Distinguish Among Similar Concepts. Educational Psychology Review.
Sweller, J. (1988). Cognitive Load During Problem Solving. Cognitive Science. + Sweller & Cooper (1985) on worked examples; Sweller, van Merriënboer & Paas (2019).
Kalyuga, S., & Renkl, A. (2009). Expertise reversal effect.
Bjork, E. L., & Bjork, R. A. (2011). Making Things Hard on Yourself, But in a Good Way: Creating Desirable Difficulties to Enhance Learning. + Bjork & Bjork (2020); Koriat & Bjork (2005) on illusions of competence.
Cowan, N. (2001). The magical number 4 in short-term memory.
Diekelmann, S., & Born, J. (2010). The memory function of sleep (systems consolidation, NREM replay); plus recent (2023–2025) sharp-wave-ripple consolidation work.
Slamecka, N. J., & Graf, P. (1978). The generation effect.
Paivio, A. (1986). Dual coding theory.
Oakley, B. (2014). A Mind for Numbers; Oakley & Sejnowski, Learning How to Learn (Coursera/UC San Diego).
FSRS: open-spaced-repetition project (Jarrett Ye et al.); FSRS-6; libraries py-fsrs, ts-fsrs, fsrs-rs. Anki adopted FSRS as default scheduler in v23.10 (2023).