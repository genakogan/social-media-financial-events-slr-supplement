#!/usr/bin/env python3
"""Known-item retrieval check - final query (PROTOCOL.md): the frozen term query with the date,
document-type and subject-field filters; no language filter.

  python3 run_final.py --mailto you@example.org [--api-key KEY]

Run it in the folder that contains this file. About 9 OpenAlex requests. Results go to run_output_final/.

Steps
  1. check the frozen term query (run_output/query_validation.txt) against its SHA-256;
  2. read the OpenAlex primary topic of the 44 development studies (validation studies are not read here);
  3. keep every field that is the primary-topic field of at least one development study;
  4. records of the term query (date and type filters) by field (group_by), and their total;
  5. run the final query once: term query + date + type + field filters; match the 80 indexed studies;
  6. after the run: fields of the validation studies (reporting only); records of the final query not
     tagged as English (descriptive only).
"""
import argparse, csv, datetime, hashlib, json, os, sys, urllib.error, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify_corpus as vc                           # noqa: E402
from run_validation import DATE, TYPES, wilson       # noqa: E402

MIN_DEV = 1          # a field is kept if it is the primary-topic field of >= MIN_DEV development studies


def fields_of(ids, mailto):
    """OpenAlex primary-topic field of each work: {short_id: (field_no, field_name)}; (None, None) if no topic."""
    out = {}
    for i in range(0, len(ids), 50):
        d = vc.get_json(f'{vc.OPENALEX}/works?filter=ids.openalex:{"|".join(ids[i:i + 50])}'
                        f'&per-page=50&select=id,primary_topic', mailto)
        for w in (d or {}).get('results', []):
            f = (w.get('primary_topic') or {}).get('field') or {}
            out[vc.short_id(w['id'])] = (vc.short_id(f.get('id')) or None, f.get('display_name'))
    return out


def count(flt, mailto):
    return vc.get_json(f'{vc.OPENALEX}/works?filter={flt}&per-page=1&select=id', mailto)['meta']['count']


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--mailto', required=True)
    ap.add_argument('--api-key', default=None)
    ap.add_argument('--v1', default=os.path.join(HERE, 'run_output'), help='folder with the frozen term query')
    ap.add_argument('--out', default=os.path.join(HERE, 'run_output_final'))
    args = ap.parse_args()
    vc.API_KEY = args.api_key
    os.makedirs(args.out, exist_ok=True)

    # 1. frozen term query
    log1 = json.load(open(os.path.join(args.v1, 'protocol_log.json'), encoding='utf-8'))
    qfile = os.path.join(args.v1, 'query_validation.txt')
    if hashlib.sha256(open(qfile, 'rb').read()).hexdigest() != log1['query_sha256']:
        sys.exit('term query differs from the frozen query - stopping')
    query = open(qfile, encoding='utf-8').read().strip()
    flt_q = f'title.search:{urllib.parse.quote(query)},{DATE},{TYPES}'

    split = {r['bibkey']: r for r in csv.DictReader(open(os.path.join(HERE, 'split.csv'), encoding='utf-8'))}
    ids = {r['bibkey']: r['openalex_id'] for r in csv.DictReader(open(os.path.join(HERE, 'corpus_ids.csv'), encoding='utf-8')) if r['openalex_id']}
    assert len(ids) == 80 and len(split) == 82

    # 2-3. fields of the development studies only
    dev_keys = [k for k, s in split.items() if s['set'] == 'development']
    assert len(dev_keys) == 44
    dev_f = fields_of([ids[k] for k in dev_keys if k in ids], args.mailto)
    kept = {}
    for k in dev_keys:
        fno, fname = dev_f.get(ids.get(k, ''), (None, None))
        if fno:
            kept.setdefault(fno, [fname, 0])[1] += 1
    kept = {f: v for f, v in kept.items() if v[1] >= MIN_DEV}
    if not kept:
        sys.exit('no primary-topic fields found for the development studies - stopping')
    print('fields kept (primary-topic field of >= 1 development study):')
    for f, (name, n) in sorted(kept.items(), key=lambda x: -x[1][1]):
        print(f'  {f:>3}  {name}  ({n} development studies)')

    # 4. records of the term query by field
    total_q = count(flt_q, args.mailto)
    try:
        g = vc.get_json(f'{vc.OPENALEX}/works?filter={flt_q}&group_by=primary_topic.field.id:include_unknown&per-page=200', args.mailto)
    except urllib.error.HTTPError:
        g = vc.get_json(f'{vc.OPENALEX}/works?filter={flt_q}&group_by=primary_topic.field.id&per-page=200', args.mailto)
    groups = []
    for x in g['group_by']:
        fid = vc.short_id(x['key']) if x['key'] else 'unknown'
        if fid == 'unknown':
            groups.append(('none', 'no primary topic', x['count']))
        else:
            groups.append((fid, x.get('key_display_name') or fid, x['count']))
    with open(os.path.join(args.out, 'records_by_field.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['field_id', 'field', 'records_term_query', 'kept_in_final_query'])
        for fid, name, n in sorted(groups, key=lambda x: -x[2]):
            w.writerow([fid, name, n, 'yes' if fid in kept else 'no'])
    expected = sum(n for fid, _, n in groups if fid in kept)

    # 5. final query: one run. The field-id form accepted by OpenAlex is checked against the group_by counts.
    flt = hits = None
    for form in ('{}', 'fields/{}', 'https://openalex.org/fields/{}'):
        cand = f'{flt_q},primary_topic.field.id:{"|".join(form.format(x) for x in sorted(kept, key=int))}'
        try:
            n = count(cand, args.mailto)
        except urllib.error.HTTPError:
            continue
        if n == expected:
            flt, hits = cand, n
            break
    if flt is None:
        sys.exit(f'the field filter could not be checked against the group_by counts (expected {expected:,}) - stopping')
    frozen_at = datetime.datetime.now().isoformat(timespec='seconds')
    found, idl = set(), list(ids.values())
    for i in range(0, len(idl), 50):
        d = vc.get_json(f'{vc.OPENALEX}/works?filter={flt},ids.openalex:{"|".join(idl[i:i + 50])}&per-page=50&select=id', args.mailto)
        found |= {vc.short_id(w['id']) for w in (d or {}).get('results', [])}

    # 6. after the run: fields of the validation studies; records not tagged as English (descriptive)
    val_f = fields_of([ids[k] for k, s in split.items() if s['set'] == 'validation' and k in ids], args.mailto)
    allf = {**dev_f, **val_f}
    not_en = count(f'{flt},language:!en', args.mailto)

    rows = []
    for k, s in sorted(split.items(), key=lambda x: (x[1]['set'], x[1]['prisma_box'], x[0])):
        oid = ids.get(k, '')
        fno, fname = allf.get(oid, (None, None))
        rows.append({'bibkey': k, 'set': s['set'], 'prisma_box': s['prisma_box'], 'theme': s['theme'], 'openalex_id': oid,
                     'indexed': bool(oid), 'primary_topic_field': fname or ('no primary topic' if oid else ''),
                     'field_kept': bool(fno and fno in kept), 'retrieved': bool(oid and oid in found)})
    with open(os.path.join(args.out, 'retrieval_final.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    res, lines = {}, []
    for st in ('development', 'validation'):
        a = [r for r in rows if r['set'] == st]
        k = sum(r['retrieved'] for r in a)
        for lab, base in (('all', a), ('indexed', [r for r in a if r['indexed']])):
            p, lo, hi = wilson(k, len(base))
            res[f'{st}_{lab}'] = {'retrieved': k, 'n': len(base), 'share': round(p, 3), 'ci95': [round(lo, 3), round(hi, 3)]}
            lines.append(f'  {st:<11} {lab:<8} {k}/{len(base)} = {p:.1%}  (95% CI {lo:.1%}-{hi:.1%})')
    missed = [f"{r['bibkey']} ({r['prisma_box']}; field: {r['primary_topic_field'] or '-'})"
              f"{'' if r['indexed'] else ' - not indexed in OpenAlex'}"
              for r in rows if r['set'] == 'validation' and not r['retrieved']]
    log = {'protocol': 'PROTOCOL.md', 'query': query, 'query_sha256': log1['query_sha256'],
           'fields_kept': {f: {'name': v[0], 'development_studies': v[1]} for f, v in kept.items()},
           'filters': flt.split(',', 1)[1], 'filters_sha256': hashlib.sha256(flt.encode('utf-8')).hexdigest(),
           'run': frozen_at, 'records_term_query': total_q, 'records': hits, 'records_not_tagged_english': not_en,
           'results': res, 'validation_missed': missed}
    json.dump(log, open(os.path.join(args.out, 'protocol_log_final.json'), 'w', encoding='utf-8'), indent=2)

    summary = '\n'.join([
        f'records of the term query (dates 2020-2026, ineligible types excluded): {total_q:,}; by field, largest first:',
        *[f"    {'+' if fid in kept else '-'} {name}: {n:,}" for fid, name, n in sorted(groups, key=lambda x: -x[2])],
        '  (+ kept in the final query, - removed)',
        f'final query (term query + {len(kept)} fields of the development studies, no language filter): {hits:,} records',
        f'  of which not tagged as English by OpenAlex (other language or none): {not_en:,}',
        *lines, '  validation studies not retrieved:', *[f'    {m}' for m in missed]])
    open(os.path.join(args.out, 'summary_final.txt'), 'w', encoding='utf-8').write(summary + '\n')
    print(summary)


if __name__ == '__main__':
    main()
