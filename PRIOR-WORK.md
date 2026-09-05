# Prior work: who did this already

Checked on 2026-09-05. Every link below was verified by querying the arXiv API
and the GitHub API, never from a summary of a summary.

**The niche is occupied end to end.** The question this repository asks has
been published at least 3 times in 2026. Both of its axes have been answered.
The fault injection tool it uses is not the first of its kind. Read this file
before the numbers in [RESULTS.md](RESULTS.md), because the numbers are a
replication and reading them first would misrepresent what they are.

## The main question has been published at least 3 times

**[arXiv:2606.05806](https://arxiv.org/abs/2606.05806), ToolMaze, "When Tools
Fail", June 2026.** A 2 by 2 taxonomy of tool failure: explicit against
implicit, crossed with transient against permanent. That is exactly our axis of
an announced failure against silent corruption, published months before this
run. Their conclusion, word for word: "systemic over-trust in
corrupted outputs". Their model list already contains DeepSeek-V4-Pro, GLM-5.1
and three Qwen models, which covers all 3 of the labs we ran.

**[arXiv:2607.19449](https://arxiv.org/abs/2607.19449), "Guardrails as
Scapegoats", July 2026.** They inject 4 profiles of silent failure, all of them
HTTP 200 with an empty, a null or a broken body, then classify the reply as
Honest Surrender, Fabrication or Unfaithful Safety Refusal. This is our design
with a finer scale on the outcome side.

**[arXiv:2609.00035](https://arxiv.org/abs/2609.00035), SilentProbe, August
2026.** 12 models from 8 families against live commercial APIs. The finding
that matters most to us: "constraint form, not vendor identity, predicts
honesty". Machine readable constraints produced an honest error in 111 cases
out of 111, while constraints written in prose silently failed in 44 out of 61.
That answers our lab axis and our format axis at once. Our own registered
expectation about prose constraints is borrowed from this result rather than
derived by us.

## The axis "lab or protocol" has been answered twice, in opposite directions

**[arXiv:2608.06790](https://arxiv.org/abs/2608.06790), AgentChaos, August
2026:** "ranking is consistent across models, robustness depends on system
implementation rather than model capability".

**[arXiv:2506.21967](https://arxiv.org/abs/2506.21967), June 2025:** open
models are more vulnerable than proprietary ones.

The disagreement between those two is a more interesting object than our
measurement is. We land on the side of AgentChaos without adding anything that
would settle the disagreement.

## Neither of the "new" failure kinds is new

**[arXiv:2601.06112](https://arxiv.org/abs/2601.06112), ReliabilityBench,
January 2026** already runs timeouts, rate limits, partial responses and schema
drift.

**[arXiv:2608.19303](https://arxiv.org/abs/2608.19303), Outcome Monitors,
August 2026** opens with our own thesis stated word for word, then fixes it
with an external contract monitor. Where we stop at a measurement, they ship a
remedy.

**[arXiv:2606.09863](https://arxiv.org/abs/2606.09863)** measures false claims
of success across 9876 trajectories from 8 families.

## Our tool is not the first

`fault-mcp`, the fault injector used here, has predecessors. All of the
following were created earlier and their dates were checked through the GitHub
API:

| repository | created | note |
|---|---|---|
| `Typewise/mcp-chaos-rig` | 2026-02-04 | 10 stars |
| `tchardonnens/chaos-mcp` | 2026-06-18 | |
| `SmartAI/mcp-chaos` | 2026-07-03 | 7 failure types against our 6, plus a published measurement across labs on 12 models |
| `seanrobmerriam/agentchaos` | 2026-07-20 | |
| `Shantam10p/ToolBreak` | 2026-07-28 | |
| `mpvasilis/toolfault` | 2026-08-03 | its README states outright that overtrusting a corrupted tool output is established prior work rather than its own finding |

## What stays ours, honestly and narrowly

One methodological refinement and one port.

**1. A paired design with an identical payload.** In every work found above,
the content of the failure changes together with its form. Nobody delivers the
same corrupted byte twice, once inside an error envelope and once silently,
leaving announcement as the only variable.

**2. A constraint on the OUTPUT rather than on the input.** SilentProbe
measures the form of a constraint on request parameters, where the constraint
makes the server answer honestly. We ask a different thing: will the model
itself check the returned value against a format declared in prose inside the
tool description? The answer is predictable from their result. The cost of
checking is zero.

## What may not be claimed in any form

That nobody does this. That we are first. That `fault-mcp` is the first fault
injector for MCP. Any public text about this measurement has to cite ToolMaze,
SilentProbe and Guardrails as Scapegoats **before** any number of its own.
