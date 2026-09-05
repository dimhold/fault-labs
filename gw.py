# -*- coding: utf-8 -*-
u"""Gateway to Bailian ModelStudio models: 16 models from 6 labs.

Why a separate module. All earlier behavior measurements (`tool-honesty`,
`tool-failure`, `tool-reach`, `silent-books`) were taken inside one family:
opus, haiku, fable. Those are 3 sizes of one training recipe, and any claim of
the form "models behave like this" is fragile on such a sample: it may be a
property of the lab. Here Qwen, DeepSeek, Kimi, GLM and MiniMax are available
under one OpenAI compatible key, so the same method yields a different class of
claim.

The key and the model list come from the qwen CLI settings
(`~/.qwen/settings.json`) and never enter the repository.

The rules this module exists for, instead of calling curl:

- **every call is written to a JSONL journal in full**, together with the
  answer, usage and timing. The journal, not a retelling, is the source of truth
  of a measurement;
- **the name of the answering model is checked against the requested one.**
  A known trap: we have already been bitten by a model other than the requested
  one answering;
- retries on capacity refusals with exponential backoff;
- the `reasoning_content` field of thinking models is kept apart from `content`.
"""
import io
import json
import os
import random
import threading
import time

try:
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError
except ImportError:                                   # python 2
    from urllib2 import Request, urlopen, HTTPError, URLError

SETTINGS = os.path.expanduser('~/.qwen/settings.json')
BACKOFF = [4, 10, 25, 60]
DEFAULT_TIMEOUT = 300

_conf = [None]
_log_lock = threading.Lock()


def _settings():
    if _conf[0] is None:
        _conf[0] = json.load(io.open(SETTINGS, encoding='utf-8'))
    return _conf[0]


def _providers():
    return _settings().get('modelProviders', {}).get('openai', [])


def models():
    u"""List of model identifiers in the order given by the settings."""
    return [m['id'] for m in _providers()]


def model_meta(model):
    for m in _providers():
        if m['id'] == model:
            return m
    raise KeyError(u'model %s is not declared in %s' % (model, SETTINGS))


def _auth(meta):
    return _settings()['env'][meta['envKey']]


def lab(model):
    u"""The lab, from the model name. Needed to tell "a property of the model"
    apart from "a property of one lab's training recipe"."""
    m = model.lower()
    if m.startswith('qwen'):
        return 'Qwen'
    if m.startswith('deepseek'):
        return 'DeepSeek'
    if m.startswith('kimi'):
        return 'Moonshot'
    if m.startswith('glm'):
        return 'Zhipu'
    if m.startswith('minimax'):
        return 'MiniMax'
    return 'unknown'


class Journal(object):
    u"""Run journal. One JSON line per call, appended immediately."""

    def __init__(self, path):
        self.path = path
        d = os.path.dirname(os.path.abspath(path))
        if d and not os.path.isdir(d):
            os.makedirs(d)

    def write(self, rec):
        line = json.dumps(rec, ensure_ascii=False)
        with _log_lock:
            with io.open(self.path, 'a', encoding='utf-8') as f:
                f.write(line + u'\n')


def chat(model, messages, tools=None, tool_choice=None, temperature=None,
         max_tokens=4096, timeout=DEFAULT_TIMEOUT, journal=None, meta=None,
         retries=len(BACKOFF)):
    u"""One call. Returns a dict with the parsed answer.

    Keys of the answer: ok, content, reasoning, tool_calls, finish_reason,
    usage, model_returned, error. When ok=False, look at error.
    """
    mm = model_meta(model)
    url = mm['baseUrl'].rstrip('/') + '/chat/completions'
    body = {'model': model, 'messages': messages, 'max_tokens': max_tokens}
    if tools:
        body['tools'] = tools
    if tool_choice is not None:
        body['tool_choice'] = tool_choice
    if temperature is not None:
        body['temperature'] = temperature
    gc = mm.get('generationConfig') or {}
    if gc.get('extra_body'):
        body.update(gc['extra_body'])

    started = time.time()
    last_err = None
    for attempt in range(retries + 1):
        req = Request(
            url,
            data=json.dumps(body).encode('utf-8'),
            headers={'Authorization': 'Bearer ' + _auth(mm),
                     'Content-Type': 'application/json'})
        try:
            raw = urlopen(req, timeout=timeout).read().decode('utf-8')
            d = json.loads(raw)
            out = _parse(model, d)
            out['attempts'] = attempt + 1
            out['seconds'] = round(time.time() - started, 2)
            _journal(journal, model, messages, tools, out, meta, d)
            return out
        except HTTPError as e:
            try:
                detail = e.read().decode('utf-8')[:600]
            except Exception:
                detail = ''
            last_err = u'HTTP %s %s' % (e.code, detail)
            # 400 is our own mistake in the request, retrying is pointless
            if e.code in (400, 401, 403, 404):
                break
        except (URLError, Exception) as e:            # timeouts and drops
            last_err = u'%s: %s' % (type(e).__name__, e)
        if attempt < retries:
            time.sleep(BACKOFF[attempt] + random.random())

    out = {'ok': False, 'model': model, 'lab': lab(model), 'error': last_err,
           'content': u'', 'reasoning': u'', 'tool_calls': [],
           'finish_reason': None, 'usage': {}, 'model_returned': None,
           'attempts': retries + 1, 'seconds': round(time.time() - started, 2)}
    _journal(journal, model, messages, tools, out, meta, None)
    return out


def _parse(model, d):
    ch = (d.get('choices') or [{}])[0]
    msg = ch.get('message') or {}
    returned = d.get('model')
    out = {
        'ok': True,
        'model': model,
        'lab': lab(model),
        'model_returned': returned,
        'content': msg.get('content') or u'',
        'reasoning': msg.get('reasoning_content') or u'',
        'tool_calls': msg.get('tool_calls') or [],
        'finish_reason': ch.get('finish_reason'),
        'usage': d.get('usage') or {},
        'error': None,
    }
    # A known trap: the model that answers may not be the one that was asked.
    # We do not require an exact match (the gateway appends suffixes), but a
    # divergence is recorded so that it does not pass silently.
    if returned and model.lower() not in str(returned).lower():
        out['model_mismatch'] = returned
    return out


def _journal(journal, model, messages, tools, out, meta, raw):
    if journal is None:
        return
    rec = {
        'ts': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'model': model,
        'lab': lab(model),
        'messages': messages,
        'tools': [t.get('function', {}).get('name') for t in (tools or [])],
        'result': dict((k, v) for k, v in out.items() if k != 'raw'),
    }
    if meta:
        rec['meta'] = meta
    if raw is not None:
        rec['raw_choice'] = (raw.get('choices') or [{}])[0]
    journal.write(rec)


def run_parallel(jobs, workers=4):
    u"""Runs a list of argument free functions in threads, keeping the order.

    Capacity refusals from the gateway are handled by the pause inside chat(),
    so only modest parallelism is needed here: 16 models at 1 trial is minutes.
    """
    results = [None] * len(jobs)
    lock = threading.Lock()
    nxt = [0]

    def worker():
        while True:
            with lock:
                i = nxt[0]
                nxt[0] += 1
            if i >= len(jobs):
                return
            try:
                results[i] = jobs[i]()
            except Exception as e:
                results[i] = {'ok': False, 'error': u'%s: %s' % (
                    type(e).__name__, e)}

    threads = [threading.Thread(target=worker) for _ in range(min(workers, len(jobs)))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


if __name__ == '__main__':
    import sys
    args = sys.argv[1:]
    if args and args[0] == 'list':
        for m in models():
            print(u'%-24s %s' % (m, lab(m)))
    else:
        print(u'usage: python gw.py list')
