# Optional browser dictation

The Speak request button uses the browser Web Speech API (`SpeechRecognition`
or its prefixed equivalent), with language `en-AU`. It is a UI input aid for
UC-M1-01 (§10.1), not a new extraction agent or a change to the submitted
CustomerRequest contract. The university Qwen service is not used for transcription.

The user explicitly starts dictation, grants microphone access, then reviews or
edits the resulting text before choosing Capture and save. Dictation never submits
the form or creates an AI attempt automatically. Existing text is preserved;
final recognised text is appended. Interim words are shown only as listening
feedback. The existing 1,500-character limit is retained, with explicit truncation
feedback. Stop listening ends recognition; navigating away aborts it.

Availability varies by browser and requires a secure context (including localhost).
Browser recognition can send audio to its provider's online service, so it may
need internet even when the app is available locally. Unsupported browsers,
permission denial, missing microphone, network failure and no speech are reported
without blocking typed input. No app-managed audio recording, database field,
backend endpoint, API key or package dependency is added.

Reference: https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition

Verify with a real microphone in the demo browser: Speak request → allow microphone
→ speak → Stop listening if necessary → review the textbox → Capture and save.
Fixture/mock checks validate UI handling but cannot guarantee browser speech-service
availability, recognition accuracy or actual microphone permission on another device.
