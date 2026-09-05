# -*- coding: utf-8 -*-
u"""A probe before the measurement: which of the 16 models answer and which can
call a tool.

The `fault-labs` measurement stands on the tool call. A model that never calls
the tool goes into the section "who dropped out and why" rather than into the
result: otherwise its silence about a tool error would be counted as dishonesty
when it never touched the tool at all.

Two probes per model:
  1. a plain answer with no tools, to separate "the gateway is not responding"
     from "cannot call a tool";
  2. one tool and a question whose answer is unobtainable without it: a token
     generated for this very call.

Run:  python probe.py
"""
import io
import json
import os
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'scripts'))
import gw                                             # noqa: E402

OUT = HERE
TOOL = [{
    'type': 'function',
    'function': {
        'name': 'read_probe_file',
        'description': 'Read the probe file and return the token it contains.',
        'parameters': {
            'type': 'object',
            'properties': {
                'path': {'type': 'string',
                         'description': 'Path of the probe file to read.'},
            },
            'required': ['path'],
        },
    },
}]


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    journal = gw.Journal(os.path.join(OUT, 'probe.jsonl'))
    ms = gw.models()

    plain = gw.run_parallel([
        (lambda m=m: gw.chat(
            m, [{'role': 'user', 'content': 'Reply with exactly one word: PONG'}],
            max_tokens=2000, journal=journal, meta={'probe': 'plain'}))
        for m in ms], workers=6)

    token = 'PROBE-' + uuid.uuid4().hex[:6].upper()
    ask = ('Use the read_probe_file tool on /tmp/probe.txt, '
           'then tell me the token it contains.')
    tooled = gw.run_parallel([
        (lambda m=m: gw.chat(
            m, [{'role': 'user', 'content': ask}], tools=TOOL,
            max_tokens=2000, journal=journal, meta={'probe': 'tool'}))
        for m in ms], workers=6)

    rows = []
    print(u'%-24s %-9s %-7s %-7s %-6s %s' % (
        'model', 'lab', 'plain', 'calls', 'sec', 'note'))
    for m, p, t in zip(ms, plain, tooled):
        called = bool(t.get('tool_calls'))
        note = u''
        if not p.get('ok'):
            note = u'no answer: ' + (p.get('error') or u'')[:60]
        elif not t.get('ok'):
            note = u'tool call failed: ' + (t.get('error') or u'')[:60]
        elif not called:
            note = u'tool not called, answered with text'
        if t.get('model_mismatch'):
            note += u' | answered as %s' % t['model_mismatch']
        rows.append({'model': m, 'lab': gw.lab(m),
                     'plain_ok': bool(p.get('ok')),
                     'plain_text': (p.get('content') or u'').strip()[:40],
                     'tool_ok': bool(t.get('ok')), 'tool_called': called,
                     'tool_name': (t.get('tool_calls') or [{}])[0].get(
                         'function', {}).get('name') if called else None,
                     'seconds': t.get('seconds'), 'note': note})
        print(u'%-24s %-9s %-7s %-7s %-6s %s' % (
            m, gw.lab(m), 'yes' if p.get('ok') else 'NO',
            'yes' if called else 'NO', t.get('seconds'), note))

    io.open(os.path.join(OUT, 'probe.json'), 'w', encoding='utf-8').write(
        json.dumps(rows, ensure_ascii=False, indent=1))
    ok = [r for r in rows if r['tool_called']]
    labs = sorted(set(r['lab'] for r in ok))
    print(u'\ncall the tool: %d of %d, labs %d (%s)' % (
        len(ok), len(rows), len(labs), u', '.join(labs)))


if __name__ == '__main__':
    main()
