# Package estimates and recommendation evidence

Alignment: submitted report §6.2.1 / §10.3 UC-M2-01 and its explainability NFR
in §11. The recommendation still needs evidence for the combined preferences
and constraints. Missing occasion/party suitability does not negate a supported
preference match. No match remains no match; no products or catalogue facts are
invented. This explicit prototype estimate is an implementation extension agreed
with the team, not a claim that serving rules were specified in Stage 1.

When party size is stated, application code adds a package estimate to each
supported recommendation. No database or API schema changes are required.

- Wine: assume 150 ml per pour; a named 750 ml bottle yields five pours.
- Beer: assume one container per serving. The seed Pale Ale 6-pack omits volume,
  so the displayed prototype assumption is six 375 ml containers, six servings.
  Other products require volume in the catalogue name; unknown sizes stay unknown.
- Spirits: assume 30 ml per pour. A named 700 ml bottle yields 23 full pours and
  10 ml remaining. Package names determine volume; category never implies 700 ml.

For party coverage, explicitly assume **one pour per person**. One 750 ml wine
bottle therefore covers a party of five at 150 ml each. The combined workflow
shows this assumption alongside each product's explanation. Occasion is retained
as context, not a claim that a product has verified birthday/event suitability.

The workflow can complete when preference evidence, budget and inventory checks
succeed and every displayed candidate's single package covers the party under
that assumption. Larger groups, unknown sizes and unknown inventory remain
partial; unsupported preference combinations still yield no match. No additional
package quantity or aggregate purchase cost is inferred.

These pours are **not Australian standard drinks**. A standard drink contains
10 g ethanol. Approximate package standard drinks use catalogue ABV:
`volume_ml / 1000 * ABV_percent * 0.789 * container_count`, rounded to one decimal.
Wine strengths therefore produce different standard-drink counts despite the
same number of assumed pours. The one-pour assumption is a prototype calculation,
not a health/safety recommendation. No extra stock or budget check is inferred
by the serving calculation; those remain separate workflow steps.

Sources:
- https://www.health.gov.au/topics/alcohol/about-alcohol/standard-drinks-guide
- https://www.wineaustralia.com/getmedia/d30d524e-8e65-4f04-bf4f-bce63e228533/REG_ComplianceGuide.pdf

Qwen identifies supported products; code performs the estimates. Saved results
are revalidated offline on first read (validation version 3), preserving original
IDs, timestamps and model provenance without spending another model attempt.
An older empty/no-match result is not turned into a recommendation without evidence.
