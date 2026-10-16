# Contract captures

Real responses of the tutor service (template provider, real `clf-v1.0.0`, fixed clock, deterministic
episode ids), one file per case, plus `manifest.json` naming the frontend parser that must accept each.

- Regenerate: `.venv\Scripts\python scripts\capture_contract_responses.py --out tests\contract_captures`
- Check against the frontend's own Zod schemas: `.venv\Scripts\python scripts\zod_contract_check.py tests\contract_captures`
- `meta.latency_ms` values are zeroed (`0.0`) because they vary per run; nothing else is altered.
- The classifier behind the labels is a prototype proxy trained on synthetic answers.
- The frontend team may copy these into its own test suite (08 section 3: a drift breaks a test on both
  sides). Copying them is the frontend's decision.
