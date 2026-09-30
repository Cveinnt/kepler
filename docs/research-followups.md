# Post-release discovery experiments

Updated September 13, 2026. These development experiments are separate from
Kepler 1.0's frozen release boards. They do not change the published score,
selection policy or retained-run cost. Their costs are additional research
costs, not part of the $777.72 release-run estimate.

## Can rejected moves expose a missing rule?

An agent-written simulator can be wrong about which moves are possible. We
tested whether a simple program could select useful experiments from those
rejections without another model call.

We recovered the S5I5 solver and structured observation recorded before a
historical boundary discovery. All physical panel controls were available;
the search depth was fixed at four clicks. The search queued 718 states and
recorded 1,369 rejected proposals. Shortest-path and endpoint-distance rankings
selected six distinct probes across five rejection sites.

The native test executed the entire frozen set, not just the most promising
proposal. It used 170 setup actions, 12 probe clicks and five level resets:
187 actions total, with no model calls during selection or execution.
Researcher construction and analysis were additional work. Each setup
observation and inter-probe reset matched the recorded visible checkpoint.

| Final rejected click | Observed effect |
| --- | --- |
| Probes 1, 2 and 6 | No pixel or metadata change |
| Probes 3, 4 and 5 | Only pixel (63,63) changed; no metadata change |

No final rejected click moved a visible game object. No new level was completed,
and the experiment established no useful counterexample or learned repair.
The two-click boundary candidate did not demonstrate clipping. Both tested
rankings failed to produce a useful discovery result at this checkpoint.

This is a negative development test, not a general rejection of active
exploration. The investigator already knew the historical mechanic, the
checkpoint came from a public game used during development, and equal visible
reset observations do not prove equal hidden state. No unrestricted-agent
comparison or independent-case replication was run here.

## What remains supported

The release reached 100.00 on all 25 public games under one frozen Opus setup.
Its retained runs used fewer output tokens and had lower list-equivalent cost
than Tycho's reported Opus full-run aggregate. Those are descriptive results,
not proof of faster rule discovery, human-like cognition, or autonomous
harness self-improvement. See the [resource comparison](resource-comparison.md).

The final-board [trace dataset](https://huggingface.co/datasets/cveinnt/kepler-arc-agi-3-traces)
does not include this later pilot. The new experiment's full native ledger and
reconciliation are retained separately; this page summarizes them and does
not claim that readers can reproduce the pilot from the final-board dataset.
