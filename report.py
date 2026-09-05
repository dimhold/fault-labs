# -*- coding: utf-8 -*-
u"""Summary of the fault-labs run. It recomputes nothing: it reads results.json.

Run:  python report.py [--in results.json]
"""
import argparse
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = HERE

GROUP = {
    'ok': u'control',
    'ok_spec': u'control',
    'error': u'loud failure',
    'empty': u'loud failure',
    'truncated': u'silent corruption',
    'wrong': u'silent corruption',
    'truncated_spec': u'corruption, format declared',
    'wrong_spec': u'corruption, format declared',
}
ORDER = ['ok', 'ok_spec', 'error', 'empty', 'truncated', 'wrong',
         'truncated_spec', 'wrong_spec']


def load(path):
    return json.load(io.open(path, encoding='utf-8'))


def usable(rs):
    return [r for r in rs if r.get('verdict') not in ('api_error', 'no_tool_call')]


def pct(a, b):
    return (100.0 * a / b) if b else 0.0


def tally(rows):
    n = len(rows)
    return {
        'n': n,
        'flagged': sum(1 for r in rows if r.get('flagged')),
        'disclosed': sum(1 for r in rows if r.get('disclosed')),
        'disclosed_orig': sum(1 for r in rows if r.get('disclosed_orig')),
        'spec': sum(1 for r in rows if r.get('spec_complaint')),
        'relayed': sum(1 for r in rows if r.get('verdict') == 'relayed'),
        'invented': sum(1 for r in rows if r.get('verdict') == 'invented'),
        'other': sum(1 for r in rows if r.get('verdict') == 'other'),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', default='results.json')
    a = ap.parse_args()
    rs = load(os.path.join(OUT, a.inp))
    dropped = [r for r in rs if r.get('verdict') in ('api_error', 'no_tool_call')]
    rows = usable(rs)

    models = sorted(set(r['model'] for r in rows))
    labs = sorted(set(r['lab'] for r in rows))
    print(u'calls %d, counted %d, dropped %d (api_error %d, no_tool_call %d)'
          % (len(rs), len(rows), len(dropped),
             len([r for r in dropped if r['verdict'] == 'api_error']),
             len([r for r in dropped if r['verdict'] == 'no_tool_call'])))
    print(u'models %d, labs %d: %s\n' % (
        len(models), len(labs), u', '.join(labs)))

    print(u'== by mode, all models together ==')
    print(u'%-16s %-28s %4s %8s %10s %9s %9s' % (
        u'mode', u'group', u'n', u'flagged', u'disclosed', u'relayed', u'invented'))
    summary = {}
    for m in ORDER:
        sub = [r for r in rows if r['mode'] == m]
        if not sub:
            continue
        t = tally(sub)
        summary[m] = t
        print(u'%-16s %-28s %4d %7.1f%% %8.1f%% %8.1f%% %8.1f%%' % (
            m, GROUP[m], t['n'], pct(t['flagged'], t['n']),
            pct(t['disclosed'], t['n']), pct(t['relayed'], t['n']),
            pct(t['invented'], t['n'])))

    print(u'\n== main contrast: the declared format ==')
    for base, spec in (('truncated', 'truncated_spec'), ('wrong', 'wrong_spec'),
                       ('ok', 'ok_spec')):
        b, s = summary.get(base), summary.get(spec)
        if not b or not s:
            continue
        print(u'%-16s flagged %5.1f%% (%d of %d)   ->  %-16s %5.1f%% (%d of %d)'
              % (base, pct(b['flagged'], b['n']), b['flagged'], b['n'],
                 spec, pct(s['flagged'], s['n']), s['flagged'], s['n']))

    print(u'\n== by lab: flagged, %% ==')
    hdr = u'%-16s' % u'mode' + u''.join(u'%12s' % l for l in labs)
    print(hdr)
    for m in ORDER:
        line = u'%-16s' % m
        for l in labs:
            sub = [r for r in rows if r['mode'] == m and r['lab'] == l]
            t = tally(sub)
            line += u'%11.1f%%' % pct(t['flagged'], t['n']) if t['n'] else u'%12s' % u'-'
        print(line)

    print(u'\n== by model: flagged on silent corruption against loud failure ==')
    print(u'%-24s %-9s %14s %18s %14s' % (
        u'model', u'lab', u'loud', u'silent corruption', u'with format'))
    for mo in models:
        loud = [r for r in rows if r['model'] == mo and r['mode'] in ('error', 'empty')]
        quiet = [r for r in rows if r['model'] == mo and r['mode'] in ('truncated', 'wrong')]
        spec = [r for r in rows if r['model'] == mo and r['mode'] in ('truncated_spec', 'wrong_spec')]
        tl, tq, ts = tally(loud), tally(quiet), tally(spec)
        print(u'%-24s %-9s %13.1f%% %17.1f%% %13.1f%%' % (
            mo, [r['lab'] for r in rows if r['model'] == mo][0],
            pct(tl['flagged'], tl['n']), pct(tq['flagged'], tq['n']),
            pct(ts['flagged'], ts['n'])))

    print(u'\n== question framing ==')
    for f in sorted(set(r['framing'] for r in rows)):
        loud = tally([r for r in rows if r['framing'] == f and r['mode'] in ('error', 'empty')])
        quiet = tally([r for r in rows if r['framing'] == f and r['mode'] in ('truncated', 'wrong', 'truncated_spec', 'wrong_spec')])
        print(u'%-8s loud %5.1f%% (n=%d), any corruption %5.1f%% (n=%d)' % (
            f, pct(loud['flagged'], loud['n']), loud['n'],
            pct(quiet['flagged'], quiet['n']), quiet['n']))

    print(u'\n== judge: the verbatim port against the extended one ==')
    t = tally(rows)
    print(u'disclosure by the old list %d, by the extended list %d, difference %d of %d'
          % (t['disclosed_orig'], t['disclosed'],
             t['disclosed'] - t['disclosed_orig'], t['n']))

    if dropped:
        print(u'\n== dropped ==')
        for mo in sorted(set(r['model'] for r in dropped)):
            sub = [r for r in dropped if r['model'] == mo]
            kinds = {}
            for r in sub:
                kinds[r['verdict']] = kinds.get(r['verdict'], 0) + 1
            print(u'%-24s %s' % (mo, kinds))

    io.open(os.path.join(OUT, 'summary.json'), 'w', encoding='utf-8').write(
        json.dumps({'by_mode': summary, 'models': models, 'labs': labs,
                    'usable': len(rows), 'dropped': len(dropped)},
                   ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
