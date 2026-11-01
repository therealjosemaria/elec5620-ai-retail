# Unsupported constraints are a clarification outcome

Alignment: submitted Stage 1 §10.3 UC-M2-01 requires evidence-linked
recommendations and explicit no-recommendation outcomes instead of unsupported
suggestions. Missing evidence for a user constraint is a normal domain limitation,
not a network error or necessarily an invalid model-response schema.

Previously, a Qwen response linking products only to red wine, while omitting
evidence for "No merlot wine", raised GroundingError and became a generic 502.
The validator now withholds each candidate missing evidence for any hard constraint.
If none remain, it saves `unsupported_request` with the exact unresolved constraint
and an explanation asking for clarification/revision or operator catalogue verification.
The workflow returns `needs_clarification` and skips budget and stock checks.
Repeated clicks reuse the saved result; no additional model attempt is made.

Existing supported constraint rules continue to use actual catalogue facts.
This change does not introduce grape-composition metadata or infer ingredient
absence merely because a product name does not mention Merlot. Unsupported
allergen, composition or certification claims are not silently dropped. Some
otherwise valid candidates can be withheld while fully evidenced candidates remain.
Invented IDs/facts, unstated evidence, contradictory known constraints and malformed
response schemas retain their validation protections.

Earlier failed requests with complete retained output may be explicitly recovered
using `python -m backend.revalidate_recommendations REQUEST_UUID`. That existing
offline operation cannot call a model. It does not change the published user needs
or the retained catalogue snapshot. Historical workflow reports are not overwritten;
run the workflow again to create a report showing the clarified outcome.

No database schema, API field, agent responsibility or university quota policy changes.
