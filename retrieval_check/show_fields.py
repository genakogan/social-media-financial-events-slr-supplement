#!/usr/bin/env python3
"""Primary topic of every included study 2021-2026 in OpenAlex: topic, subfield, field, domain.

  python3 show_fields.py --mailto you@example.org [--api-key KEY]

Run it in the folder that contains split.csv and corpus_ids.csv (e.g. variantE_run). 2 OpenAlex requests.
Prints the studies grouped by set (development / validation) and field, and writes fields_check.csv.
If run_output_v2/retrieval_v2E.csv exists, the fields are compared with those recorded in the variant-E run.
"""
import argparse, csv, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify_corpus as vc    # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--mailto', required=True)
    ap.add_argument('--api-key', default=None)
    args = ap.parse_args()
    vc.API_KEY = args.api_key

    split = {r['bibkey']: r for r in csv.DictReader(open(os.path.join(HERE, 'split.csv'), encoding='utf-8'))}
    ids = {r['bibkey']: r['openalex_id'] for r in csv.DictReader(open(os.path.join(HERE, 'corpus_ids.csv'), encoding='utf-8')) if r['openalex_id']}
    idl = list(ids.values())
    works = {}
    for i in range(0, len(idl), 50):
        d = vc.get_json(f'{vc.OPENALEX}/works?filter=ids.openalex:{"|".join(idl[i:i + 50])}'
                        f'&per-page=50&select=id,display_name,primary_topic', args.mailto)
        for w in (d or {}).get('results', []):
            works[vc.short_id(w['id'])] = w

    def name(pt, key):
        return ((pt or {}).get(key) or {}).get('display_name') or ''

    rows = []
    for k, s in split.items():
        w = works.get(ids.get(k, ''), {})
        pt = w.get('primary_topic')
        rows.append({'bibkey': k, 'set': s['set'], 'openalex_id': ids.get(k, ''),
                     'field': name(pt, 'field') or ('no primary topic' if k in ids else 'not indexed'),
                     'subfield': name(pt, 'subfield'), 'topic': (pt or {}).get('display_name') or '',
                     'topic_score': (pt or {}).get('score', ''), 'domain': name(pt, 'domain'),
                     'title': w.get('display_name') or ''})
    with open(os.path.join(HERE, 'fields_check.csv'), 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys())); wr.writeheader(); wr.writerows(rows)

    groups = defaultdict(list)
    for r in rows:
        groups[(r['set'], r['field'])].append(r)
    for st in ('development', 'validation'):
        print(f'\n=== {st} set ===')
        for (s, fld), rs in sorted(groups.items(), key=lambda x: -len(x[1])):
            if s != st:
                continue
            print(f'\n{fld}: {len(rs)}')
            for r in sorted(rs, key=lambda r: r['bibkey']):
                print(f"  {r['bibkey']:<28} topic: {r['topic']}  [subfield: {r['subfield']}]")

    rp = os.path.join(HERE, 'run_output_v2', 'retrieval_v2E.csv')
    if os.path.exists(rp):
        rec = {r['bibkey']: r['primary_topic_field'] for r in csv.DictReader(open(rp, encoding='utf-8'))}
        diff = [(r['bibkey'], rec.get(r['bibkey']), r['field']) for r in rows
                if r['bibkey'] in rec and rec[r['bibkey']] and r['field'] not in ('not indexed',) and rec[r['bibkey']] != r['field']]
        print(f'\ncomparison with the variant-E run: {len(diff)} differences' + ''.join(f'\n  {d}' for d in diff))
    print('\nwritten fields_check.csv')


if __name__ == '__main__':
    main()
