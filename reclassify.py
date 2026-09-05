# -*- coding: utf-8 -*-
u"""Rejudging the saved replies, without a single new call.

The raw replies are the data, the verdicts are derived. When the judge is
fixed, the derivative is recomputed rather than the run being taken again.
Otherwise a fix to the judge is indistinguishable from a different run.

The old verdicts are kept alongside under keys with the suffix `_v1`, so the
fix is visible row by row and not only in the summary.

Run:  python reclassify.py
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from classify import classify                        # noqa: E402

OUT = HERE


def main():
    path = os.path.join(OUT, 'results.json')
    rows = json.load(io.open(path, encoding='utf-8'))
    changed = 0
    for r in rows:
        if r.get('verdict') in ('api_error', 'no_tool_call'):
            continue
        if 'verdict_v1' not in r:
            for k in ('verdict', 'flagged', 'spec_complaint', 'disclosed'):
                r[k + '_v1'] = r.get(k)
        new = classify(r.get('reply') or u'', r.get('tool_returned') or u'')
        if (new['verdict'] != r.get('verdict')
                or new['flagged'] != r.get('flagged')):
            changed += 1
        r.update(new)

    io.open(path, 'w', encoding='utf-8').write(
        json.dumps(rows, ensure_ascii=False, indent=1))
    print(u'rows rejudged: %d, verdict or flag changed in %d'
          % (len(rows), changed))

    for mode in ('truncated_spec', 'wrong_spec', 'ok_spec'):
        sub = [r for r in rows if r.get('mode') == mode]
        print(u'%-16s flagged was %d, now %d | referred to the format %d' % (
            mode,
            sum(1 for r in sub if r.get('flagged_v1')),
            sum(1 for r in sub if r.get('flagged')),
            sum(1 for r in sub if r.get('spec_checked'))))


if __name__ == '__main__':
    main()
