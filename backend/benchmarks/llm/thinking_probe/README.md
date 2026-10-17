# Thinking-mode probe (qwen3:4b), T1 evidence

The evidence behind the thinking-mode settings (`LLM_THINKING_MODEL`, `LLM_THINKING_TIMEOUT_S`,
`LLM_THINKING_KEEP_ALIVE`, and "thinking is uncapped"). Made by the backend lead on 2026-10-16 and copied here
**byte-identical** from `backendPlan/evidence/thinking_probe/` (nothing was reconstructed or re-run for T1):

- `qwen_think_probe.py`: the probe script.
- `qwen_think.json`: the capped runs, made by `qwen_think_probe.py qwen3:4b true 1500`.

**The probe used the r2 prompt; the service now serves r3 (plus the M1 conversation block).** These figures are
therefore a guide to the cost of thinking, not a measurement of the shipped prompt. Nothing in this folder
measures whether thinking replies are more accurate (n = 1 correct reply).

## The capped runs (`num_predict` 1500, 5 prompts)

0 of 5 produced any content. The whole budget went on thinking: walls of 39.8 to 45.6 s and 5.9k to 6.9k
characters of thinking each. So thinking is **not capped** in the service.

## The uncapped run (a single inline command; backend lead, 2026-10-16)

| | |
|---|---|
| model, call | `qwen3:4b`, `/api/chat`, `stream: false`, `think: true`, `num_predict` 6000 (never reached), `keep_alive: "0"` |
| prompt | the service's `build_prompt` at prompt revision **r2**: topic `inheritance`, strategy `theory`, cycle 1, student message "I don't understand how super works" |
| hardware | RTX 3050 6 GB laptop GPU, about 38 tok/s, `gpu_fraction` 1.0 (seen in the capped runs just before) |
| wall | **119.9 s** |
| eval_count | **4229** tokens, `done_reason` `stop` |
| thinking | 17,887 characters (discarded by the service) |
| content | **35 words**, `would_ship` true |
| GPU after | 85 C, `sw_thermal_slowdown` Not Active |

Content, verbatim:

    In Java, `super` accesses the parent class. It lets you call parent constructors and methods. For example, you use:

    ```java
    super(...);
    ```

    **Check:** How do you call the parent class constructor in a child class?

`LLM_THINKING_TIMEOUT_S` is that 120 s times 1.5 = 180 s, separate from `LLM_TIMEOUT_S` (18 s, not re-derived).
