#!/usr/bin/env python3
"""Re-execute steps 3-4 of run_validation.py with the SAME frozen query.

Why: in the first run the register file had no openalex_id values, so the frozen query could not be
matched against the included studies (every study was reported as "not indexed"). The terms, the
threshold and the query are not changed: the script checks the SHA-256 of query_validation.txt against
protocol_log.json and stops if they differ. The OpenAlex IDs come from corpus_ids.csv (column
openalex_id of Supplementary Table S1). The deviation is recorded in protocol_log.json.

  python3 run_step3.py --run validation_run --mailto you@example.org --api-key YOUR_KEY
"""
import argparse, csv, datetime, hashlib, json, os, sys, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify_corpus as vc                      # noqa: E402
from run_validation import DATE, TYPES, wilson  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--run', default='validation_run', help='folder of the first run')
    ap.add_argument('--mailto', required=True)
    ap.add_argument('--api-key', default=None)
    ap.add_argument('--pause', type=float, default=0.35)
    args = ap.parse_args()
    vc.API_KEY, vc.PAUSE = args.api_key, args.pause

    log_path = os.path.join(args.run, 'protocol_log.json')
    log = json.load(open(log_path, encoding='utf-8'))
    qpath = os.path.join(args.run, 'query_validation.txt')
    sha = hashlib.sha256(open(qpath, 'rb').read()).hexdigest()
    if sha != log['query_sha256']:
        sys.exit('query_validation.txt differs from the frozen query - stopping')
    query = open(qpath, encoding='utf-8').read().strip()
    assert query == log['query']

    split = {r['bibkey']: r for r in csv.DictReader(open(os.path.join(HERE, 'split.csv'), encoding='utf-8'))}
    ids = {r['bibkey']: r['openalex_id'] for r in csv.DictReader(open(os.path.join(HERE, 'corpus_ids.csv'), encoding='utf-8'))
           if r['openalex_id']}
    assert set(ids) <= set(split) and len(ids) == 80, len(ids)

    print('3/4 running the frozen query (unchanged, sha256 %s...) against the included studies ...' % sha[:12], flush=True)
    flt = f'title.search:{urllib.parse.quote(query)},{DATE},{TYPES}'
    hits = vc.get_json(f'{vc.OPENALEX}/works?filter={flt}&per-page=1&select=id', args.mailto)['meta']['count']
    found, idl = set(), list(ids.values())
    for i in range(0, len(idl), 50):
        d = vc.get_json(f'{vc.OPENALEX}/works?filter={flt},ids.openalex:{"|".join(idl[i:i + 50])}&per-page=50&select=id',
                        args.mailto)
        found |= {vc.short_id(w['id']) for w in (d or {}).get('results', [])}

    rows = []
    for k, s in sorted(split.items(), key=lambda x: (x[1]['set'], x[1]['prisma_box'], x[0])):
        oid = ids.get(k, '')
        rows.append({'bibkey': k, 'set': s['set'], 'prisma_box': s['prisma_box'], 'theme': s['theme'],
                     'openalex_id': oid, 'indexed': bool(oid), 'retrieved': bool(oid and oid in found)})
    with open(os.path.join(args.run, 'retrieval.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    res, lines = {}, []
    for st in ('development', 'validation'):
        s_all = [r for r in rows if r['set'] == st]
        s_idx = [r for r in s_all if r['indexed']]
        k = sum(r['retrieved'] for r in s_all)
        for lab, base in (('all', s_all), ('indexed', s_idx)):
            p, lo, hi = wilson(k, len(base))
            res[f'{st}_{lab}'] = {'retrieved': k, 'n': len(base), 'share': round(p, 3), 'ci95': [round(lo, 3), round(hi, 3)]}
            lines.append(f'{st:<11} {lab:<8} {k}/{len(base)} = {p:.1%}  (95% CI {lo:.1%}-{hi:.1%})')
    missed = [f"{r['bibkey']} ({r['prisma_box']}){'' if r['indexed'] else ' - not indexed in OpenAlex'}"
              for r in rows if r['set'] == 'validation' and not r['retrieved']]

    log.setdefault('deviations', []).append({
        'date': datetime.datetime.now().isoformat(timespec='seconds'),
        'what': 'steps 3-4 re-executed with run_step3.py',
        'why': 'first run: the register used had no openalex_id values, so no included study could be matched '
               '(all reported as not indexed); terms, threshold and query unchanged (same SHA-256)',
        'first_run_records': log.get('records'), 'first_run_results': log.get('results')})
    log.update(records=hits, results=res, validation_missed=missed,
               run_finished=datetime.datetime.now().isoformat(timespec='seconds'))
    json.dump(log, open(log_path, 'w', encoding='utf-8'), indent=2, default=str)
    summary = '\n'.join([f'records returned by the frozen query: {hits:,}', *lines, 'validation studies not retrieved:',
                         *[f'  {m}' for m in missed]])
    open(os.path.join(args.run, 'summary.txt'), 'w', encoding='utf-8').write(summary + '\n')
    print('4/4 done\n' + summary)


if __name__ == '__main__':
    main()
