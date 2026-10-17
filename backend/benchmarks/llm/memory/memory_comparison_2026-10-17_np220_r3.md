# M1 memory A/B

A = no history, B = scripted 4-turn episode history. No pass bar.

| metric | A: no history | B: with history | B - A |
|---|---|---|---|
| median prompt characters | 1035 | 2084 | 1050 |
| wall p50 (s) | 4.67 | 4.25 | -0.42 |
| wall p95 (s) | 5.74 | 5.82 | 0.08 |
| wall max (s) | 5.77 | 5.95 | 0.18 |
| shippable in form (%) | 100.0 | 97.9 | -2.1 |
| median shipped words | 106 | 106 | 0 |
| untagged leak (%) | 0.0 | 0.0 | 0.0 |
| cap-stops (%) | 37.5 | 27.1 | -10.4 |
| median tok/s | 39.6 | 39.4 | -0.2 |
