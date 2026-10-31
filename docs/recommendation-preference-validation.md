# Combined recommendation preferences — 28 October 2026

Authority: submitted Stage 1 §6.2.1, §10.3 steps 3–5 and extensions 4a/5a;
Figure 4 retains separate CustomerRequest and catalogue Product facts. The
report text and diagram were inspected. This corrects UC-M2-01 within its scope.

The reported request contained both `red wine` and `sweet`. Previously, Qwen's
dry reds and sweet white Moscato passed individual true-fact checks, despite none
satisfying the combination. The prompt now asks for combined suitability. A
validation guard withholds known contrary preferences and requires evidence for
each broader preference. It does not prove arbitrary natural-language semantics.
Recognised phrases include `sweet red wine` and `dry red wine`.

With no supported combined match, the result is `no_match` and the graph stops
before budget/inventory. It does not offer partial alternatives as suitable
recommendations. A true sweet red catalogue product still passes. Occasion and
party size remain captured; the warning now says catalogue data cannot assess
their suitability. This original correction added no catalogue fields or serving
calculations; the later [serving-estimate extension](serving-assumptions.md) adds
explicitly labelled application calculations without changing catalogue fields.

## Cache and model allowance

Old saved recommendations are checked once on their next read against published
saved needs and product facts already in that result. The corrected payload and
validation version are persisted, retaining generation timestamp/provider and
marking offline revalidation. Original private raw output remains intact. No
model is called, no failed attempt retried and no request recaptured. Missing
published needs block revalidation.

Saved workflow reports remain historical snapshots. Click **Run agent workflow**
to create a new report from the corrected cache; reload alone can still show an
older workflow. Budget and availability remain separate responsibilities.

## Contributions and checks

Based on main `81a27d2` / PR #10, including Lio's `193cda3` low-stock module/tests.
All fetched remote branches were ancestors of main; no open PR remained at review.
Contributor authorship is preserved.

- 290 backend fixture/mocked tests passed, including six combined-preference/cache
  regression tests and Lio's latest low-stock checks.
- Production TypeScript/Vite build and 12 fixture browser tests passed.
- Actual preview browser: reported request `6cb36e52-73e3-47b6-9cb9-50ee2f1bbca4`
  now returns cached `no_match`. Positive saved university request
  `1cca1bbd-aa78-40ff-9c64-9bab0b5ef659` retains its Customer–Inventory handoff.
  Both show the clarified warning. University attempt count was unchanged.

No fresh inference was performed. This checks validation and reuse of earlier
actual university output, not the changed prompt's live quality.
