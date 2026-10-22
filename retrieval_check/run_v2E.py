#!/usr/bin/env python3
"""Known-item retrieval check, protocol version 2, variant E: variant A (version-1 query unchanged +
language:en) with a subject-field filter whose fields are taken from the development studies only
(PROTOCOL_v2.md, addendum 2).

  python3 run_v2E.py --mailto you@example.org [--api-key KEY]

Run it in the folder that contains this file. About 8 OpenAlex requests. Results go to run_output_v2/.

Steps
  1. check the version-1 query against its SHA-256;
  2. read the OpenAlex primary topic of the 44 development studies (validation studies are not read here);
  3. keep every field that is the primary-topic field of at least one development study;
  4. descriptive: records of variant A by field (group_by);
  5. run variant E once: version-1 query + language:en + the kept fields; match the 80 indexed studies;
  6. after the run: read the fields of the validation studies, to report the fields of studies not retrieved.
"""
import argparse, csv, datetime, hashlib, json, os, sys, urllib.error, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify_corpus as vc                           # noqa: E402
from run_validation import DATE, TYPES, wilson       # noqa: E402

LANG = 'language:en'
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
    ap.add_argument('--v1', default=os.path.join(HERE, 'run_output'))
    ap.add_argument('--out', default=os.path.join(HERE, 'run_output_v2'))
    args = ap.parse_args()
    vc.API_KEY = args.api_key
    os.makedirs(args.out, exist_ok=True)

    # 1. frozen version-1 query
    log1 = json.load(open(os.path.join(args.v1, 'protocol_log.json'), encoding='utf-8'))
    qfile = os.path.join(args.v1, 'query_validation.txt')
    if hashlib.sha256(open(qfile, 'rb').read()).hexdigest() != log1['query_sha256']:
        sys.exit('version-1 query differs from the frozen query - stopping')
    query = open(qfile, encoding='utf-8').read().strip()
    flt_a = f'title.search:{urllib.parse.quote(query)},{DATE},{TYPES},{LANG}'

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

    # 4. descriptive: records of variant A by field
    total_a = count(flt_a, args.mailto)
    try:
        g = vc.get_json(f'{vc.OPENALEX}/works?filter={flt_a}&group_by=primary_topic.field.id:include_unknown&per-page=200', args.mailto)
    except urllib.error.HTTPError:
        g = vc.get_json(f'{vc.OPENALEX}/works?filter={flt_a}&group_by=primary_topic.field.id&per-page=200', args.mailto)
    groups = [(vc.short_id(x['key']), x.get('key_display_name') or x['key'], x['count']) if x['key'] and x['key'] != 'unknown'
              else ('none', 'no primary topic', x['count']) for x in g['group_by']]
    with open(os.path.join(args.out, 'records_by_field_v2A.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['field_id', 'field', 'records_variant_A', 'kept_in_variant_E'])
        for fid, name, n in sorted(groups, key=lambda x: -x[2]):
            w.writerow([fid, name, n, 'yes' if fid in kept else 'no'])
    expected = sum(n for fid, _, n in groups if fid in kept)

    # 5. variant E: one run. The field-id form accepted by OpenAlex is checked against the group_by counts.
    flt_e = hits = None
    for form in ('{}', 'fields/{}', 'https://openalex.org/fields/{}'):
        cand = f'{flt_a},primary_topic.field.id:{"|".join(form.format(x) for x in sorted(kept, key=int))}'
        try:
            n = count(cand, args.mailto)
        except urllib.error.HTTPError:
            continue
        if n == expected:
            flt_e, hits = cand, n
            break
    if flt_e is None:
        sys.exit(f'the field filter could not be checked against the group_by counts (expected {expected:,}) - stopping')
    found, idl = set(), list(ids.values())
    for i in range(0, len(idl), 50):
        d = vc.get_json(f'{vc.OPENALEX}/works?filter={flt_e},ids.openalex:{"|".join(idl[i:i + 50])}&per-page=50&select=id', args.mailto)
        found |= {vc.short_id(w['id']) for w in (d or {}).get('results', [])}

    # 6. after the run: fields of the validation studies (for reporting only)
    val_f = fields_of([ids[k] for k, s in split.items() if s['set'] == 'validation' and k in ids], args.mailto)
    allf = {**dev_f, **val_f}

    rows = []
    for k, s in sorted(split.items(), key=lambda x: (x[1]['set'], x[1]['prisma_box'], x[0])):
        oid = ids.get(k, '')
        fno, fname = allf.get(oid, (None, None))
        rows.append({'bibkey': k, 'set': s['set'], 'prisma_box': s['prisma_box'], 'theme': s['theme'], 'openalex_id': oid,
                     'indexed': bool(oid), 'primary_topic_field': fname or ('no primary topic' if oid else ''),
                     'field_kept': bool(fno and fno in kept), 'retrieved': bool(oid and oid in found)})
    with open(os.path.join(args.out, 'retrieval_v2E.csv'), 'w', newline='', encoding='utf-8') as f:
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
    entry = {'variant': 'E', 'description': 'version-1 query unchanged + language:en + primary-topic fields of the development studies',
             'query_sha256': log1['query_sha256'], 'fields_kept': {f: {'name': v[0], 'development_studies': v[1]} for f, v in kept.items()},
             'filters': flt_e.split(',', 1)[1], 'filters_sha256': hashlib.sha256(flt_e.encode('utf-8')).hexdigest(),
             'run': datetime.datetime.now().isoformat(timespec='seconds'), 'records_variant_A': total_a, 'records': hits,
             'results': res, 'validation_missed': missed}
    lp = os.path.join(args.out, 'protocol_log_v2.json')
    log2 = json.load(open(lp, encoding='utf-8')) if os.path.exists(lp) else {'variants': {}}
    log2.setdefault('variants', {})['E'] = entry
    json.dump(log2, open(lp, 'w', encoding='utf-8'), indent=2)

    top = sorted(groups, key=lambda x: -x[2])
    summary = '\n'.join([
        f'records of variant A (English only): {total_a:,}; by field, largest first:',
        *[f"    {'+' if fid in kept else '-'} {name}: {n:,}" for fid, name, n in top],
        '  (+ kept in variant E, - removed)',
        f'variant E (English only + {len(kept)} fields of the development studies): {hits:,} records',
        *lines, '  validation studies not retrieved:', *[f'    {m}' for m in missed]])
    open(os.path.join(args.out, 'summary_v2E.txt'), 'w', encoding='utf-8').write(summary + '\n')
    print(summary)


if __name__ == '__main__':
    main()
