#!/usr/bin/env python3
"""Known-item retrieval check, protocol version 2 (PROTOCOL_v2.md): narrows the version-1 query.
Two pre-specified variants are built and frozen before either is run, then both are run once and reported:
  B  - cap K chosen by the 90%-of-development-titles rule (grid 5,000-100,000)
  D  - cap K = 10,000

  python3 run_v2.py --register ../Supplementary_Table_S1_Corpus_Register.xlsx --mailto you@example.org [--api-key KEY]

Uses the version-1 outputs in run_output/ (term_counts.csv, protocol_log.json); needs split.csv,
corpus_ids.csv, derive_terms.py, run_validation.py and verify_corpus.py in this folder.
Steps: build both version-2 queries offline, freeze them, run each once with language:en, report.
About 6 OpenAlex requests. Output folder: run_output_v2/
"""
import argparse, csv, datetime, hashlib, json, os, sys, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify_corpus as vc                                        # noqa: E402
import derive_terms as dt                                         # noqa: E402
from run_validation import DATE, TYPES, wilson, load_register, q_term  # noqa: E402

GRID_K = [5000, 10000, 20000, 50000, 100000]
DEV_TARGET = 0.90
LANG = 'language:en'


def build_v2(v1_terms, all_terms, R, dev_titles):
    def terms_for(K):  # noqa: E306
        kept = {}
        for t in v1_terms:
            if t['count'] <= K:
                kept[t['key']] = t
                continue
            for p in all_terms:          # replacement: candidate phrases containing the term
                if (p['kind'] == 'phrase' and p['key'] != t['key'] and f" {t['key']} " in f" {p['key']} "
                        and p['count'] <= K and p['ratio'] >= R):
                    kept[p['key']] = p
        words = {k for k, v in kept.items() if v['kind'] == 'word'}
        return [v for k, v in sorted(kept.items()) if v['kind'] == 'word' or not (set(k.split()) & words)]

    trace = []
    for K in GRID_K:
        ts = terms_for(K)
        cov = sum(any(dt.contains(title, t['key']) for t in ts) for title in dev_titles) / len(dev_titles)
        trace.append({'K': K, 'n_terms': len(ts), 'dev_match_offline': round(cov, 3)})
    K_B = min([t['K'] for t in trace if t['dev_match_offline'] >= DEV_TARGET] or [max(GRID_K)])
    return {'B': (K_B, sorted(terms_for(K_B), key=lambda t: t['term'])),
            'D': (10000, sorted(terms_for(10000), key=lambda t: t['term']))}, trace


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--register', required=True)
    ap.add_argument('--mailto', required=True)
    ap.add_argument('--api-key', default=None)
    ap.add_argument('--v1', default=os.path.join(HERE, 'run_output'))
    ap.add_argument('--out', default=os.path.join(HERE, 'run_output_v2'))
    args = ap.parse_args()
    vc.API_KEY = args.api_key
    os.makedirs(args.out, exist_ok=True)

    log1 = json.load(open(os.path.join(args.v1, 'protocol_log.json'), encoding='utf-8'))
    tc = list(csv.DictReader(open(os.path.join(args.v1, 'term_counts.csv'), encoding='utf-8')))
    for t in tc:
        t['count'], t['ratio'] = int(t['oa_count']), float(t['ratio'])
    v1_terms = [t for t in tc if t['in_query'] == 'True']
    assert ' OR '.join(q_term(t['term']) for t in sorted(v1_terms, key=lambda t: t['term'])) == log1['query']

    split = {r['bibkey']: r for r in csv.DictReader(open(os.path.join(HERE, 'split.csv'), encoding='utf-8'))}
    reg = load_register(args.register)
    dev_titles = [reg[k]['title'] for k, s in split.items() if s['set'] == 'development']
    variants, trace = build_v2(v1_terms, tc, log1['R'], dev_titles)
    ids = {r['bibkey']: r['openalex_id'] for r in csv.DictReader(open(os.path.join(HERE, 'corpus_ids.csv'), encoding='utf-8')) if r['openalex_id']}
    assert len(ids) == 80
    log = {'protocol': 'PROTOCOL_v2.md', 'based_on': 'version 1', 'run_started': datetime.datetime.now().isoformat(timespec='seconds'),
           'R': log1['R'], 'K_grid': GRID_K, 'cap_trace': trace, 'filters': f'{DATE},{TYPES},{LANG}', 'variants': {}}
    # 1. freeze both queries before running either
    for name, (K, terms) in variants.items():
        query = ' OR '.join(q_term(t['term']) for t in terms)
        qpath = os.path.join(args.out, f'query_v2{name}.txt')
        open(qpath, 'w', encoding='utf-8').write(query + '\n')
        log['variants'][name] = {'K': K, 'n_terms': len(terms), 'query': query,
                                 'query_sha256': hashlib.sha256(open(qpath, 'rb').read()).hexdigest()}
    log['frozen_at'] = datetime.datetime.now().isoformat(timespec='seconds')
    json.dump(log, open(os.path.join(args.out, 'protocol_log_v2.json'), 'w', encoding='utf-8'), indent=2)
    for name, v in log['variants'].items():
        print(f"variant {name}: K = {v['K']}, {v['n_terms']} terms, frozen (sha256 {v['query_sha256'][:12]}...)", flush=True)
    # 2. run each once
    summary = []
    for name, v in log['variants'].items():
        flt = f"title.search:{urllib.parse.quote(v['query'])},{DATE},{TYPES},{LANG}"
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
        with open(os.path.join(args.out, f'retrieval_v2{name}.csv'), 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
        res, lines = {}, []
        for st in ('development', 'validation'):
            a_ = [r for r in rows if r['set'] == st]
            k = sum(r['retrieved'] for r in a_)
            for lab, base in (('all', a_), ('indexed', [r for r in a_ if r['indexed']])):
                p, lo, hi = wilson(k, len(base))
                res[f'{st}_{lab}'] = {'retrieved': k, 'n': len(base), 'share': round(p, 3), 'ci95': [round(lo, 3), round(hi, 3)]}
                lines.append(f'  {st:<11} {lab:<8} {k}/{len(base)} = {p:.1%}  (95% CI {lo:.1%}-{hi:.1%})')
        missed = [f"{r['bibkey']} ({r['prisma_box']}){'' if r['indexed'] else ' - not indexed in OpenAlex'}"
                  for r in rows if r['set'] == 'validation' and not r['retrieved']]
        v.update(records=hits, results=res, validation_missed=missed)
        summary += [f"variant {name} (K = {v['K']}, {v['n_terms']} terms, English only): {hits:,} records", *lines,
                    '  validation studies not retrieved:', *[f'    {m}' for m in missed], '']
    log['run_finished'] = datetime.datetime.now().isoformat(timespec='seconds')
    json.dump(log, open(os.path.join(args.out, 'protocol_log_v2.json'), 'w', encoding='utf-8'), indent=2)
    open(os.path.join(args.out, 'summary_v2.txt'), 'w', encoding='utf-8').write('\n'.join(summary))
    print('\n'.join(summary))


if __name__ == '__main__':
    main()
