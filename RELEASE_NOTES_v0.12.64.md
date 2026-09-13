# FlipFynd v0.12.64 — Autograph Authenticity Gate

- Printed/facsimile signatures can no longer enter the autograph premium path.
- Silver Script / Super Script are treated as script parallels, not certified autographs.
- Visual autograph evidence requires `autograph_type` on_card or sticker before `is_auto` becomes true.
- Unclear or listing-claimed signatures remain unverified until checklist/certification evidence exists.
- Regression tests cover Silver Script, printed facsimile and on-card visual signals.
