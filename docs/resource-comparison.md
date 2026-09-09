# Kepler and Tycho: retained-run resource comparison

Both reported Opus 5 runs score 100 on the 25 public ARC-AGI-3 games.
Kepler's retained run generated 61.7% fewer output tokens and used 36.1%
fewer tokens overall than Tycho's published full-run aggregate. Its
list-equivalent cost is 74.0% lower with the reported cache mix.

This is a descriptive comparison of two retained runs. It does not isolate
the harness's causal effect, establish faster convergence, include either
project's full research spend, or rank all competing systems. Tycho's figures
are its authors' published aggregates, not provider records we independently
audited. Kepler's cost is reconstructed from retained provider usage, not an
invoice. Both systems used public games during development.

## Exact inputs

| Token category | Kepler | Tycho |
| --- | ---: | ---: |
| Fresh input | 11,464 | 321,864,558 |
| Cache reads | 835,488,978 | 947,433,620 |
| Cache writes | 13,574,918, one-hour | 50,747,962, five-minute |
| Output | 8,966,566 | 23,433,077 |
| Total | 858,041,926 | 1,343,479,217 |

Kepler source: [release metadata](../release.json) and
[provider-record accounting implementation](../scripts/cost_report.py).
Its retained accounting covers 142 session files and 5,732 distinct usage
records. Full provider histories are not distributed as part of the final-board
trace corpus. The public counters permit arithmetic reproduction, not an
independent audit of every billable provider event.

Tycho source: [figure_data.json](https://raw.githubusercontent.com/NIMI-research/Tycho/main/artifacts/figure_data.json),
`runs["Opus 5 (selected orchestrator)"]`, retrieved September 9, 2026.
SHA-256: `507946809f7ea4d4d66090fddf843d22ed2db3ff01bfaec83055b1ab90a6f398`.
See also [Tycho's paper](https://arxiv.org/html/2607.28287).

## Reproduce the arithmetic

Rates per million tokens are $5 for fresh input, $25 for output, $0.50 for
cache reads, $10 for one-hour writes and $6.25 for five-minute writes.
These retain the release comparison's pricing basis, not a promise about
future provider prices.

```python
from decimal import Decimal as D

# fresh input, cache reads, cache writes, output
kepler = (11464, 835488978, 13574918, 8966566)
tycho = (321864558, 947433620, 50747962, 23433077)

def price(tokens, write_rate):
    fresh, reads, writes, output = map(D, tokens)
    return (fresh * 5 + reads * D("0.5") + writes * write_rate
            + output * 25) / 1_000_000

def uncached_repricing(tokens):
    return (D(sum(tokens[:3])) * 5 + D(tokens[3]) * 25) / 1_000_000

def reduction(a, b):
    return 100 * (1 - D(a) / D(b))

print(price(kepler, D(10)), price(tycho, D("6.25")))
print(reduction(kepler[3], tycho[3]))
print(reduction(sum(kepler), sum(tycho)))
print(uncached_repricing(kepler), uncached_repricing(tycho))
print(reduction(uncached_repricing(kepler), uncached_repricing(tycho)))
```

Expected rounded results: $777.72 versus $2,986.04; 61.74% fewer output
tokens; 36.13% fewer total tokens. Repricing the same volumes without cache
discounts gives $4,469.54 versus $7,186.06, a 37.80% reduction. This
sensitivity calculation does not simulate disabling caching, changed agent
behavior, or latency on a rerun.

## What this does not answer

Fewer generated tokens can reflect fewer model responses, different tool
habits, batching, run selection or other differences. It does not by itself
show quicker rule discovery or fewer environment actions. Tycho's reported
model-call count and Kepler's usage-record count may cover retries and failures
differently, so we do not headline their ratio.

Tycho's budget-sensitivity table has a different realized-cost denominator
from its full-run aggregate. We have not reconciled that difference and do
not compare score-versus-cost curves across the two systems. A controlled
Kepler batching pilot is separate work, with no outcome claimed here.
