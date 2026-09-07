# FlipFynd v0.11.69 – Temporal Holdout Integrity

- Holdout-delningen använder nu endast `prediction_timestamp_at_capture`.
- Discovery = tidigare prognoser; holdout = senare prognoser.
- Saknad eller ogiltig prognostidpunkt ger fail-closed status `MISSING_DATES`.
- `sale_date`, `updated_at`, `created_at` och `id` används aldrig längre som fallback.
- Mindre än 10 relevanta rader ger `INSUFFICIENT_DATA`.
- Inga automatiska modelländringar aktiveras.
- Den futuristiska terminaldesignen från v0.11.68 behålls.
