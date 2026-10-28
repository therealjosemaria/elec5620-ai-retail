# Standing project instructions

## Check the submitted Stage 1 report first

Before proposing behaviour, defining shared contracts, implementing a use case,
or asking the user to decide a requirement, inspect the relevant sections of the
authoritative submitted Stage 1 report, including its diagrams.

- Authoritative report: `❗️AI_Multi_Agent_Alcohol_Retail_Project_M5_Sequence_Fixed.docx.pdf`.
- Drive source: https://drive.google.com/file/d/1IkMlRMNZu36VanWrdGSnTbHgYw4fJGWu/view
- In this workspace session, an attached copy is available at:
  `/home/jmos0905/.codex/attachments/595ea06a-d1eb-42d5-a9a4-11c79e971fac/❗️AI_Multi_Agent_Alcohol_Retail_Project_M5_Sequence_Fixed.docx.pdf`.
- On 27 October 2026, the user confirmed that the local
  `/Users/cedar/Downloads/AIMultiAgentAlcoholRetail_Project-1.pdf`
  is that submitted report under a different filename. Use this accessible copy
  on this Mac. Its pagination differs from older alignment notes; cite sections
  and figure numbers after inspecting the source.
- Do not substitute the later “Critical Fixes” revision.
- If the source is unavailable, request access or an upload rather than inventing
  its requirements. Local alignment notes are aids, not replacements for the source.
- Preserve the submitted scope and agent boundaries. Do not ask the user to
  re-decide requirements that the report already specifies.
- Where a diagram omits behavioural details supplied by its written requirement
  or use-case specification, use the detailed text while retaining the architecture.
  This is the agreed interpretation for stock lookup authorization and status results.
- Flag genuine contradictions or details missing from all relevant sections;
  distinguish implementation choices from additional requirements.
- Record the relevant section/figure when documenting an implementation decision.

## Verification and credentials

Use mocked/fixture tests by default to conserve the university model allowance.
Distinguish fixture verification from live model verification. Keep credentials
in the private, ignored `.env`, never in source control or public documentation.
