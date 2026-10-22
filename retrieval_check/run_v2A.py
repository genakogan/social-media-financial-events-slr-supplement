#!/usr/bin/env python3
"""Known-item retrieval check, protocol version 2, variant A: the version-1 query unchanged,
with the language filter language:en added (PROTOCOL_v2.md, variant A).

  python3 run_v2A.py --mailto you@example.org [--api-key KEY]

Run it in the v2_full folder. The version-1 query is read from run_output/ and checked against its
SHA-256 before running. About 3 OpenAlex requests. Results are added to run_output_v2/.
"""
import argparse, csv, datetime, hashlib, json, os, sys, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify_corpus as vc                           # noqa: E402
from run_validation import DATE, TYPES, wilson       # noqa: E402

LANG = 'language:en'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--mailto', required=True)
    ap.add_argument('--api-key', default=None)
    ap.add_argument('--v1', default=os.path.join(HERE, 'run_output'))
    ap.add_argument('--out', default=os.path.join(HERE, 'run_output_v2'))
    args = ap.parse_args()
    vc.API_KEY = args.api_key
    os.makedirs(args.out, exist_ok=True)

    log1 = json.load(open(os.path.join(args.v1, 'protocol_log.json'), encoding='utf-8'))
    qfile = os.path.join(args.v1, 'query_validation.txt')
    if hashlib.sha256(open(qfile, 'rb').read()).hexdigest() != log1['query_sha256']:
        sys.exit('version-1 query differs from the frozen query - stopping')
    query = open(qfile, encoding='utf-8').read().strip()

    split = {r['bibkey']: r for r in csv.DictReader(open(os.path.join(HERE, 'split.csv'), encoding='utf-8'))}
    ids = {r['bibkey']: r['openalex_id'] for r in csv.DictReader(open(os.path.join(HERE, 'corpus_ids.csv'), encoding='utf-8')) if r['openalex_id']}
    assert len(ids) == 80

    flt = f'title.search:{urllib.parse.quote(query)},{DATE},{TYPES},{LANG}'
    hits = vc.get_json(f'{vc.OPENALEX}/works?filter={flt}&per-page=1&select=id', args.mailto)['meta']['count']
    found, idl = set(), list(ids.values())
    for i in range(0, len(idl), 50):
        d = vc.get_json(f'{vc.OPENALEX}/works?filter={flt},ids.openalex:{"|".join(idl[i:i + 50])}&per-page=50&select=id', args.mailto)
        found |= {vc.short_id(w['id']) for w in (d or {}).get('results', [])}

    rows = []
    for k, s in sorted(split.items(), key=lambda x: (x[1]['set'], x[1]['prisma_box'], x[0])):
        oid = ids.get(k, '')
        rows.append({'bibkey': k, 'set': s['set'], 'prisma_box': s['prisma_box'], 'theme': s['theme'],
                     'openalex_id': oid, 'indexed': bool(oid), 'retrieved': bool(oid and oid in found)})
    with open(os.path.join(args.out, 'retrieval_v2A.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    res, lines = {}, []
    for st in ('development', 'validation'):
        a = [r for r in rows if r['set'] == st]
        k = sum(r['retrieved'] for r in a)
        for lab, base in (('all', a), ('indexed', [r for r in a if r['indexed']])):
            p, lo, hi = wilson(k, len(base))
            res[f'{st}_{lab}'] = {'retrieved': k, 'n': len(base), 'share': round(p, 3), 'ci95': [round(lo, 3), round(hi, 3)]}
            lines.append(f'  {st:<11} {lab:<8} {k}/{len(base)} = {p:.1%}  (95% CI {lo:.1%}-{hi:.1%})')
    missed = [f"{r['bibkey']} ({r['prisma_box']}){'' if r['indexed'] else ' - not indexed in OpenAlex'}"
              for r in rows if r['set'] == 'validation' and not r['retrieved']]
    lost = [r['bibkey'] for r in rows if r['retrieved'] is False and r['indexed']]
    entry = {'variant': 'A', 'description': 'version-1 query unchanged + language:en', 'query_sha256': log1['query_sha256'],
             'filters': f'{DATE},{TYPES},{LANG}', 'run': datetime.datetime.now().isoformat(timespec='seconds'),
             'records': hits, 'results': res, 'validation_missed': missed}
    lp = os.path.join(args.out, 'protocol_log_v2.json')
    log2 = json.load(open(lp, encoding='utf-8')) if os.path.exists(lp) else {'variants': {}}
    log2.setdefault('variants', {})['A'] = entry
    json.dump(log2, open(lp, 'w', encoding='utf-8'), indent=2)
    summary = '\n'.join([f'variant A (version-1 query, English only): {hits:,} records', *lines,
                         '  validation studies not retrieved:', *[f'    {m}' for m in missed]])
    open(os.path.join(args.out, 'summary_v2A.txt'), 'w', encoding='utf-8').write(summary + '\n')
    print(summary)


if __name__ == '__main__':
    main()
