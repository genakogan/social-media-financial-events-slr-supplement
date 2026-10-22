#!/usr/bin/env python3
"""Descriptive only: how the records of the final query are distributed over OpenAlex source types
(journal, conference, repository, ...) and work types (article, preprint, book-chapter, ...), and the
source and work type of the 82 included studies 2021-2026. Nothing is filtered; the result of the
check is not changed.

  python3 count_by_source_type.py --mailto you@example.org [--api-key KEY]

Run it in the final_run folder (it reads run_output/ and run_output_final/protocol_log_final.json).
About 5 OpenAlex requests. Writes run_output_final/records_by_source_type.csv,
records_by_work_type.csv, studies_types.csv and summary_types.txt.
"""
import argparse, csv, datetime, hashlib, json, os, sys, urllib.error, urllib.parse
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify_corpus as vc    # noqa: E402


def group(flt, key, mailto):
    for k in (f'{key}:include_unknown', key):
        try:
            g = vc.get_json(f'{vc.OPENALEX}/works?filter={flt}&group_by={k}&per-page=200', mailto)
            return [(x.get('key_display_name') or x.get('key') or 'unknown', x['count']) for x in g['group_by']]
        except urllib.error.HTTPError:
            continue
    sys.exit(f'group_by {key} not accepted by OpenAlex - stopping')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--mailto', required=True)
    ap.add_argument('--api-key', default=None)
    ap.add_argument('--final', default=os.path.join(HERE, 'run_output_final'))
    ap.add_argument('--v1', default=os.path.join(HERE, 'run_output'))
    args = ap.parse_args()
    vc.API_KEY = args.api_key

    # the exact filter of the final run, checked against its SHA-256
    logf = json.load(open(os.path.join(args.final, 'protocol_log_final.json'), encoding='utf-8'))
    log1 = json.load(open(os.path.join(args.v1, 'protocol_log.json'), encoding='utf-8'))
    qfile = os.path.join(args.v1, 'query_validation.txt')
    if hashlib.sha256(open(qfile, 'rb').read()).hexdigest() != log1['query_sha256']:
        sys.exit('term query differs from the frozen query - stopping')
    query = open(qfile, encoding='utf-8').read().strip()
    flt = f'title.search:{urllib.parse.quote(query)},{logf["filters"]}'
    if hashlib.sha256(flt.encode('utf-8')).hexdigest() != logf['filters_sha256']:
        sys.exit('filter string differs from the final run - stopping')

    total = vc.get_json(f'{vc.OPENALEX}/works?filter={flt}&per-page=1&select=id', args.mailto)['meta']['count']
    src = sorted(group(flt, 'primary_location.source.type', args.mailto), key=lambda x: -x[1])
    wtp = sorted(group(flt, 'type', args.mailto), key=lambda x: -x[1])
    for name, rows in (('records_by_source_type.csv', src), ('records_by_work_type.csv', wtp)):
        with open(os.path.join(args.final, name), 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f); w.writerow(['type', 'records', 'share'])
            for k, n in rows:
                w.writerow([k, n, f'{n / total:.4f}'])

    # source and work type of the 82 included studies 2021-2026
    split = {r['bibkey']: r for r in csv.DictReader(open(os.path.join(HERE, 'split.csv'), encoding='utf-8'))}
    ids = {r['bibkey']: r['openalex_id'] for r in csv.DictReader(open(os.path.join(HERE, 'corpus_ids.csv'), encoding='utf-8')) if r['openalex_id']}
    rp = os.path.join(args.final, 'retrieval_final.csv')
    retrieved = {r['bibkey']: r['retrieved'] == 'True' for r in csv.DictReader(open(rp, encoding='utf-8'))} if os.path.exists(rp) else {}
    info, idl = {}, list(ids.values())
    for i in range(0, len(idl), 50):
        d = vc.get_json(f'{vc.OPENALEX}/works?filter=ids.openalex:{"|".join(idl[i:i + 50])}'
                        f'&per-page=50&select=id,type,primary_location', args.mailto)
        for w in (d or {}).get('results', []):
            s = ((w.get('primary_location') or {}).get('source') or {})
            info[vc.short_id(w['id'])] = (s.get('type') or 'no source', s.get('display_name') or '', w.get('type') or '')
    rows = []
    for k, s in sorted(split.items(), key=lambda x: (x[1]['set'], x[0])):
        oid = ids.get(k, '')
        st, sname, wt = info.get(oid, ('not indexed', '', '')) if oid else ('not indexed', '', '')
        rows.append({'bibkey': k, 'set': s['set'], 'openalex_id': oid, 'source_type': st, 'source': sname, 'work_type': wt,
                     'retrieved_final': '' if k not in retrieved else ('yes' if retrieved[k] else 'no')})
    with open(os.path.join(args.final, 'studies_types.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    cross = defaultdict(Counter)
    for r in rows:
        cross[r['set']][r['source_type']] += 1
    lines = [f'final query, {datetime.date.today().isoformat()}: {total:,} records (descriptive breakdown; nothing filtered)',
             '  by OpenAlex source type (primary location):',
             *[f'    {k}: {n:,} ({n / total:.1%})' for k, n in src],
             '  by OpenAlex work type:',
             *[f'    {k}: {n:,} ({n / total:.1%})' for k, n in wtp],
             'included studies 2021-2026 by OpenAlex source type:',
             *[f'  {s}: ' + ', '.join(f'{k} {n}' for k, n in cross[s].most_common()) for s in ('development', 'validation')]]
    if retrieved:
        vr = Counter(r['source_type'] for r in rows if r['set'] == 'validation' and r['retrieved_final'] == 'yes')
        lines.append('  validation studies retrieved by the final query: ' + ', '.join(f'{k} {n}' for k, n in vr.most_common()))
    lines.append('  validation studies not in a journal source: ' +
                 ', '.join(f"{r['bibkey']} ({r['source_type']})" for r in rows if r['set'] == 'validation' and r['source_type'] != 'journal'))
    summary = '\n'.join(lines)
    open(os.path.join(args.final, 'summary_types.txt'), 'w', encoding='utf-8').write(summary + '\n')
    print(summary)


if __name__ == '__main__':
    main()
