#!/usr/bin/env python3
"""Evaluate MedVision predictions against an externally annotated JSONL benchmark.

This script does not create ground truth and does not claim clinical validation.
Each JSONL row is one binary target for one case, for example:

{"case_id":"C001","specialty":"pulmo","target":"pneumothorax","y_true":1,"score_a":0.91,"score_b":0.83}
{"case_id":"C002","specialty":"pulmo","target":"pneumothorax","y_true":0,"score_a":0.12,"score_b":0.18}

Required: case_id, specialty, target, y_true (0/1), score_a (0..1)
Optional: score_b (0..1), critic_score (0..1)
"""

from __future__ import annotations
import argparse
import json
import math
from collections import defaultdict
from pathlib import Path


def div(a, b):
    return a / b if b else None


def clamp_score(x):
    x = float(x)
    if not 0 <= x <= 1:
        raise ValueError(f'score outside [0,1]: {x}')
    return x


def confusion(rows, score_key, threshold):
    tp = tn = fp = fn = 0
    scored = []
    for r in rows:
        if score_key not in r or r[score_key] is None:
            continue
        y = int(r['y_true'])
        p = clamp_score(r[score_key])
        pred = int(p >= threshold)
        scored.append((y, p, pred))
        if y == 1 and pred == 1: tp += 1
        elif y == 0 and pred == 0: tn += 1
        elif y == 0 and pred == 1: fp += 1
        else: fn += 1
    return tp, tn, fp, fn, scored


def ece(scored, bins=10):
    if not scored:
        return None
    total = len(scored)
    acc = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        bucket = [(y, p) for y, p, _ in scored if (p >= lo and (p < hi or (b == bins - 1 and p <= hi)))]
        if not bucket:
            continue
        mean_p = sum(p for _, p in bucket) / len(bucket)
        mean_y = sum(y for y, _ in bucket) / len(bucket)
        acc += len(bucket) / total * abs(mean_p - mean_y)
    return acc


def binary_metrics(rows, score_key, threshold):
    tp, tn, fp, fn, scored = confusion(rows, score_key, threshold)
    if not scored:
        return None
    sensitivity = div(tp, tp + fn)
    specificity = div(tn, tn + fp)
    ppv = div(tp, tp + fp)
    npv = div(tn, tn + fn)
    precision = ppv
    recall = sensitivity
    f1 = None if precision is None or recall is None or (precision + recall) == 0 else 2 * precision * recall / (precision + recall)
    accuracy = div(tp + tn, tp + tn + fp + fn)
    brier = sum((p - y) ** 2 for y, p, _ in scored) / len(scored)
    return {
        'n': len(scored), 'threshold': threshold,
        'tp': tp, 'tn': tn, 'fp': fp, 'fn': fn,
        'sensitivity': sensitivity, 'specificity': specificity,
        'ppv': ppv, 'npv': npv, 'f1': f1, 'accuracy': accuracy,
        'brier': brier, 'ece_10': ece(scored, 10),
    }


def cohen_kappa(rows, threshold):
    pairs = []
    for r in rows:
        if r.get('score_b') is None:
            continue
        a = int(clamp_score(r['score_a']) >= threshold)
        b = int(clamp_score(r['score_b']) >= threshold)
        pairs.append((a, b))
    if not pairs:
        return None
    n = len(pairs)
    agree = sum(a == b for a, b in pairs) / n
    pa = sum(a for a, _ in pairs) / n
    pb = sum(b for _, b in pairs) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    kappa = None if pe == 1 else (agree - pe) / (1 - pe)
    return {'n': n, 'raw_agreement': agree, 'cohen_kappa': kappa}


def validate_row(r, lineno):
    required = ['case_id', 'specialty', 'target', 'y_true', 'score_a']
    missing = [k for k in required if k not in r]
    if missing:
        raise ValueError(f'line {lineno}: missing {missing}')
    if int(r['y_true']) not in (0, 1):
        raise ValueError(f'line {lineno}: y_true must be 0 or 1')
    clamp_score(r['score_a'])
    if r.get('score_b') is not None:
        clamp_score(r['score_b'])
    if r.get('critic_score') is not None:
        clamp_score(r['critic_score'])


def main():
    ap = argparse.ArgumentParser(description='Evaluate MedVision against an externally annotated binary-target JSONL benchmark.')
    ap.add_argument('jsonl', type=Path)
    ap.add_argument('--threshold', type=float, default=0.5)
    ap.add_argument('--out', type=Path)
    args = ap.parse_args()
    if not 0 <= args.threshold <= 1:
        raise SystemExit('--threshold must be in [0,1]')

    rows = []
    with args.jsonl.open(encoding='utf-8') as f:
        for lineno, line in enumerate(f, 1):
            if not line.strip():
                continue
            r = json.loads(line)
            validate_row(r, lineno)
            rows.append(r)
    if not rows:
        raise SystemExit('No benchmark rows found. No clinical metric can be computed without annotated data.')

    groups = defaultdict(list)
    for r in rows:
        groups[(str(r['specialty']), str(r['target']))].append(r)

    report = {
        'disclaimer': 'Metrics are benchmark measurements only. Clinical validity depends on dataset provenance, annotation quality, prevalence, population and external validation.',
        'threshold': args.threshold,
        'rows': len(rows),
        'cases': len({str(r['case_id']) for r in rows}),
        'groups': {},
        'overall': {
            'reader_a': binary_metrics(rows, 'score_a', args.threshold),
            'reader_b': binary_metrics(rows, 'score_b', args.threshold),
            'critic': binary_metrics(rows, 'critic_score', args.threshold),
            'reader_agreement': cohen_kappa(rows, args.threshold),
        },
    }
    for (specialty, target), items in sorted(groups.items()):
        report['groups'][specialty + '/' + target] = {
            'reader_a': binary_metrics(items, 'score_a', args.threshold),
            'reader_b': binary_metrics(items, 'score_b', args.threshold),
            'critic': binary_metrics(items, 'critic_score', args.threshold),
            'reader_agreement': cohen_kappa(items, args.threshold),
        }

    text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    if args.out:
        args.out.write_text(text + '\n', encoding='utf-8')
        print(args.out)
    else:
        print(text)


if __name__ == '__main__':
    main()
