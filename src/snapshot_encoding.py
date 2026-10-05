"""Detach mutable JSON containers and stream encoding without whole-text copies."""
import json


def detach_json(value, memo=None, active=None):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if not isinstance(value, (dict, list, tuple)):
        return None
    memo = {} if memo is None else memo
    active = set() if active is None else active
    marker = id(value)
    if marker in active:
        raise ValueError('Circular reference detected')
    if marker in memo:
        return memo[marker]
    out = {} if isinstance(value, dict) else []
    memo[marker] = out
    active.add(marker)
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                if key is not None and not isinstance(key, (int, float, bool)):
                    raise TypeError('Unsupported JSON key')
                key = json.dumps(key)
            out[key] = detach_json(item, memo, active)
    else:
        out.extend(detach_json(item, memo, active) for item in value)
    active.remove(marker)
    return out


def json_chunks(value, *, default=None):
    return json.JSONEncoder(ensure_ascii=False, default=default).iterencode(value)


def json_size(value, limit):
    size = 0
    for chunk in json_chunks(value):
        size += len(chunk.encode('utf-8'))
        if size > limit:
            break
    return size


def fits_json_budget(value, limit):
    return json_size(value, limit) <= limit
