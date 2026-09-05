# fault-labs

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22417812.svg)](https://doi.org/10.5281/zenodo.22417812)

When a model's tool breaks, does the reply report the breakage or silently pass
the corrupted value on?

560 calls answer that on 7 models from 3 labs: Qwen, DeepSeek and Zhipu.
8 tool modes, 2 question framings, 5 trials per cell. The tool is ours and
lives in the harness, so the source of truth is the call journal in
`calls.jsonl` rather than any model's account of what happened. Nobody dropped
out: the tool was called in all 560.

**Read [PRIOR-WORK.md](PRIOR-WORK.md) before the numbers below.** The niche is
occupied end to end. The main question of this measurement has been published
at least 3 times in 2026, the axis "is this a property of the lab or of the
protocol" has been answered twice in opposite directions and fault injection
tools for MCP were built before ours. This repository is a replication on a
minimal task. It is not a discovery.

## What came out

**Silent corruption is caught by nobody: 0 out of 140.** When the tool returns
a truncated or substituted token, says nothing about it and no answer format is
declared anywhere, all 7 models of all 3 labs pass the corrupted value on and
mark it with nothing at all. Not one exception.

**When the tool announces the failure itself, models talk about it.** `EACCES`
is disclosed in 87.1% of replies.

| mode | what the tool returned | n | flagged | relayed on |
|---|---|---:|---:|---:|
| `ok` | the correct token | 70 | 0.0% | 100% |
| `ok_spec` | the correct token, format declared | 70 | 0.0% | 100% |
| `error` | `EACCES: permission denied` | 70 | **87.1%** | 0% |
| `empty` | an empty string | 70 | 41.4% | 0% |
| `truncated` | the first 8 characters of the token | 70 | **0.0%** | 100% |
| `wrong` | a different well formed token | 70 | **0.0%** | 100% |
| `truncated_spec` | the first 8 characters, format declared | 70 | 10.0% | 87.1% |
| `wrong_spec` | a different well formed token, format declared | 70 | 0.0% | 100% |

**A declared format barely helps.** The truncated token breaks the declared
format visibly: 8 characters arrive where the tool description promises 12.
That was checked in 7 replies out of 70. The substituted token satisfies the
format and was flagged 0 times out of 70. Neither control mode produced a false
alarm.

**A rigid answer format halves disclosure.** Same broken tool, same models, the
only difference is whether the question asked for a strict shape of reply.

| framing | loud failure | any corruption |
|---|---:|---:|
| open question | **91.4%** | 5.0% |
| "reply with exactly one line, `TOKEN: <token>`" | **37.1%** | 0.0% |

Under the rigid format the model hands back an empty reply on an empty result.
There were 26 such replies out of 70 in mode `empty`, 23 of them under the
rigid framing and 3 under the open one. The practical conclusion worth more
than the rest: a line saying "reply strictly in this format" in a system prompt
switches off the agent's error reporting. The error does not disappear. What
disappears is the place to mention it.

**The lab did not turn out to be a variable.** The spread between labs inside
one mode runs from 82.5% to 100% on `error`, which is visibly narrower than the
spread between modes inside one lab, from 0% to 90% for DeepSeek. Behavior is
set by whether the tool announced the failure rather than by whose training
recipe answered.

## Files

**[CRITERIA.md](CRITERIA.md)** carries the question, the expectation, what
would refute it, the design and the judge. It was written before the first
number and was not rewritten afterwards.

**[RESULTS.md](RESULTS.md)** carries all the numbers, the tables per lab and
per model, the two fixes to the judge and the boundaries of what was measured.

**[PRIOR-WORK.md](PRIOR-WORK.md)** says who did this already. Every paper and
repository in it was checked through the arXiv API and the GitHub API on
2026-09-05.

Data:

* `calls.jsonl` holds every call with its full request, reply and usage. This
  is the source of truth.
* `results.json` holds the parsed rows with verdicts. Verdicts from the first
  version of the judge are kept alongside under keys with the suffix `_v1`.
* `probe.json` holds which models the gateway serves and which of them call a
  tool.

Code:

* `classify.py` is the deterministic judge, a line by line port of the judge
  from the earlier measurement, with the extension kept in a separate list.
* `run.py` is the run, `probe.py` the probe that preceded it, `report.py` the
  summary and `reclassify.py` the rejudging of saved replies.

## Running it

```
python report.py        # the summary above, straight from results.json
python reclassify.py    # rejudge the saved replies, no new calls
```

Both read the data files next to them and need nothing beyond the standard
library. `run.py` and `probe.py` are published as the record of what was
executed. They import a gateway helper module, `gw`, which is not part of this
repository, so repeating the run itself takes a key for the model gateway and
an OpenAI compatible client of your own.

## License

MIT, see [LICENSE](LICENSE). Citation metadata is in
[CITATION.cff](CITATION.cff).
