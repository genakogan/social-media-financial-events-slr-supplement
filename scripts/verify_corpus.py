#!/usr/bin/env python3
"""
verify_corpus.py - verification search for the review corpus (OpenAlex + Crossref).

What it does
  1. resolve   Finds every corpus record in OpenAlex (by DOI, otherwise by title)
               and checks its metadata against Crossref (title, year, venue, type).
  2. search    Runs each query from queries.csv in OpenAlex and reports
               - n_hits: how many works the query returns in OpenAlex
               - which corpus records the query retrieves (exact, by OpenAlex ID)
               - recall = corpus records retrieved / corpus records in the date window
  3. Writes a dated search log so every run is documented.

Why OpenAlex for the search and Crossref for metadata
  OpenAlex supports Boolean queries (AND, OR, NOT, "phrases") restricted to title
  and abstract, so a record either matches a query or not. Crossref only ranks
  records by relevance and has no Boolean matching, so it cannot tell whether a
  record is retrieved by a query; it is used to verify bibliographic metadata.

Usage
  pip install openpyxl certifi    (openpyxl reads the .xlsx register; certifi supplies
                                   HTTPS certificates, needed on macOS python.org builds)
  python verify_corpus.py --corpus Supplementary_Table_S1_Corpus_Register.xlsx \
                          --queries queries_v1.csv --mailto you@example.org \
                          --from-date 2021-01-01 --to-date 2026-12-31 --out results

  Options:
    --skip-crossref        do not run the Crossref metadata check
    --export-hits N        also save the first N hits of every query (for screening
                           new candidates); 0 = do not export (default)
    --no-date-filter       run the queries without a publication-date window

  queries CSV columns: block_id, name, query_version, target, field, extra_filter, openalex_query
    target        PRISMA categories the block is meant to retrieve (semicolon-separated,
                  matched against prisma_box / xref_to); gives recall within the section
    field         title  or  title_and_abstract (default)
    extra_filter  optional OpenAlex filter added to the query, e.g. type:article|review

Outputs (folder --out)
  corpus_resolved.csv     corpus record -> OpenAlex ID, match method, metadata check
  coverage.csv            corpus record x query: retrieved yes/no
  search_log.csv          one row per query and run (appended on every run)
  bib_doi_problems.csv    DOIs in the .bib that point to another work or differ from OpenAlex
  missed.csv              corpus records not retrieved by any query in this run
  hits_<block>.csv        (optional) first N hits of each query

The script uses only the Python standard library apart from openpyxl.
"""
import argparse, csv, datetime, difflib, json, os, re, sys, time
import urllib.parse, urllib.request, urllib.error
import http.client

import ssl
try:
    import certifi                      # trusted certificate bundle (fixes macOS python.org builds)
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CTX = ssl.create_default_context()

OPENALEX = 'https://api.openalex.org'
CROSSREF = 'https://api.crossref.org'
SELECT = 'id,doi,display_name,publication_year,type,primary_location'
CORPUS_IDS = set()


# ------------------------------------------------------------------ HTTP
API_KEY = None
PAUSE = 0.35


def get_json(url, mailto, pause=None, tries=8):
    pause = PAUSE if pause is None else pause
    sep = '&' if '?' in url else '?'
    if mailto and 'mailto=' not in url:
        url = f'{url}{sep}mailto={urllib.parse.quote(mailto)}'
    if API_KEY and 'api.openalex.org' in url and 'api_key=' not in url:
        url = f'{url}&api_key={urllib.parse.quote(API_KEY)}'
    req = urllib.request.Request(url, headers={'User-Agent': f'verify_corpus/1.0 (mailto:{mailto})'})
    for k in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60, context=SSL_CTX) as r:
                data = json.loads(r.read().decode('utf-8'))
            time.sleep(pause)
            return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (429, 500, 502, 503) and k < tries - 1:
                wait = e.headers.get('Retry-After') if e.headers else None
                wait = float(wait) if wait and wait.replace('.', '', 1).isdigit() else min(60, 2 ** k * 3)
                print(f'    server busy (HTTP {e.code}); waiting {wait:.0f} s and retrying ...', flush=True)
                time.sleep(wait)
                continue
            if e.code == 429:
                sys.exit('OpenAlex daily limit reached (HTTP 429). Wait and re-run with --resolved '
                         '<out>/corpus_resolved.csv to skip step 1, or add --api-key.')
            raise
        except (urllib.error.URLError, http.client.HTTPException, ConnectionError, TimeoutError,
                json.JSONDecodeError) as e:
            # dropped connections, timeouts, truncated responses: wait and retry
            if k < tries - 1:
                wait = min(60, 2 ** k * 3)
                print(f'    connection problem ({type(e).__name__}); waiting {wait} s and retrying ...', flush=True)
                time.sleep(wait)
                continue
            raise


# ------------------------------------------------------------------ helpers
def norm_doi(d):
    d = (d or '').strip().lower()
    d = re.sub(r'^(https?://)?(dx\.)?doi\.org/', '', d)
    d = re.sub(r'^doi:\s*', '', d)
    return d or None


def norm_title(t):
    return re.sub(r'[^a-z0-9 ]', '', (t or '').lower()).strip()


def similarity(a, b):
    return round(difflib.SequenceMatcher(None, norm_title(a), norm_title(b)).ratio(), 3)


def title_prefix(a, b):
    a, b = norm_title(a), norm_title(b)
    return bool(a and b) and (a.startswith(b) or b.startswith(a))


def short_id(oa_id):
    return (oa_id or '').rsplit('/', 1)[-1]


def read_corpus(path):
    rows = []
    if path.lower().endswith('.xlsx'):
        from openpyxl import load_workbook
        ws = load_workbook(path, read_only=True, data_only=True)['Data']
        it = ws.iter_rows(values_only=True)
        hdr = [str(h) for h in next(it)]
        for r in it:
            if r and r[hdr.index('bibkey')]:
                rows.append(dict(zip(hdr, r)))
    else:
        with open(path, encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        y = r.get('year')
        out.append({'bibkey': str(r['bibkey']), 'doi': norm_doi(r.get('doi')), 'title': str(r.get('title') or ''),
                    'year': int(y) if str(y).isdigit() else None,
                    'boxes': ' | '.join(str(x) for x in (r.get('prisma_box'), r.get('xref_to')) if x)})
    return out


def read_queries(path):
    with open(path, encoding='utf-8') as f:
        return [q for q in csv.DictReader(f) if q.get('block_id', '').strip()]


def date_filter(args):
    if args.no_date_filter:
        return ''
    parts = []
    if args.from_date:
        y = int(args.from_date[:4]) - args.date_slack
        parts.append(f'from_publication_date:{y}{args.from_date[4:]}')
    if args.to_date:
        parts.append(f'to_publication_date:{args.to_date}')
    return ','.join(parts)


def in_window(year, args):
    if args.no_date_filter or year is None:
        return True
    lo = int(args.from_date[:4]) if args.from_date else -1
    hi = int(args.to_date[:4]) if args.to_date else 9999
    return lo <= year <= hi


# ------------------------------------------------------------------ step 1: resolve corpus
def apply_manual_ids(corpus, path, args):
    """CSV with columns bibkey, openalex_id: records the author identified by hand in OpenAlex."""
    with open(path, encoding='utf-8') as f:
        manual = {r['bibkey'].strip(): r['openalex_id'].strip() for r in csv.DictReader(f) if r.get('openalex_id', '').strip()}
    for c in corpus:
        wid = manual.get(c['bibkey'])
        if not wid:
            continue
        wid = short_id(wid)
        w = get_json(f'{OPENALEX}/works/{wid}?select={SELECT}', args.mailto)
        if not w:
            print(f'  manual id {wid} for {c["bibkey"]} not found in OpenAlex')
            continue
        c.update(oa_id=short_id(w['id']), oa_title=w.get('display_name'), oa_year=w.get('publication_year'),
                 match='manual OpenAlex ID', title_sim=similarity(c['title'], w.get('display_name')),
                 oa_doi=norm_doi(w.get('doi')))
        warn = '' if float(c['title_sim']) >= 0.80 else '  WARNING: title differs from the register, check the ID'
        print(f'  manual id: {c["bibkey"]} -> {c["oa_id"]} ({c["oa_title"]}){warn}')


def resolve(corpus, args, skip_doi=False):
    by_doi = {} if skip_doi else {c['doi']: c for c in corpus if c['doi']}
    dois = list(by_doi)
    for i in range(0, len(dois), 50):
        batch = dois[i:i + 50]
        flt = 'doi:' + '|'.join(urllib.parse.quote(d, safe='/.') for d in batch)
        data = get_json(f'{OPENALEX}/works?filter={flt}&per-page=50&select={SELECT}', args.mailto)
        for w in (data or {}).get('results', []):
            c = by_doi.get(norm_doi(w.get('doi')))
            if c:
                c.update(oa_id=short_id(w['id']), oa_title=w.get('display_name'), oa_year=w.get('publication_year'),
                         match='doi', title_sim=similarity(c['title'], w.get('display_name')))
    for c in corpus:
        if c.get('oa_id') and float(c.get('title_sim') or 0) < 0.80 and not title_prefix(c['title'], c.get('oa_title')):
            c['doi_problem'] = f"DOI {c['doi']} resolves to a different work: {c.get('oa_title')}"
            c['oa_id'] = None
        if c.get('oa_id'):
            continue
        best, score = None, 0
        phrase = re.sub(r'[^A-Za-z0-9 ]+', ' ', c['title'])[:250]
        phrase = re.sub(r'\s+', ' ', phrase).strip()
        urls = [f'{OPENALEX}/works?filter=title.search:{urllib.parse.quote(chr(34) + phrase + chr(34))}&per-page=25&select={SELECT}',
                f'{OPENALEX}/works?search={urllib.parse.quote(c["title"][:250])}&per-page=25&select={SELECT}']
        for url in urls:
            data = get_json(url, args.mailto)
            for w in (data or {}).get('results', []):
                s = similarity(c['title'], w.get('display_name'))
                if s > score:
                    best, score = w, s
            if score >= 0.90:
                break
        if best and score >= 0.90:
            oa_doi = norm_doi(best.get('doi'))
            if c.get('doi_problem'):
                how = 'title (bib DOI belongs to another work)'
            elif not c['doi']:
                how = 'title'
            else:
                how = 'title (bib DOI not in OpenAlex)'
            c.update(oa_id=short_id(best['id']), oa_title=best.get('display_name'), oa_year=best.get('publication_year'),
                     match=how, title_sim=score, oa_doi=oa_doi)
            if c['doi'] and oa_doi and oa_doi != c['doi'] and not c.get('doi_problem'):
                c['doi_problem'] = f'bib DOI {c["doi"]} differs from OpenAlex DOI {oa_doi}'
        else:
            c.update(oa_id=None, match='not found', title_sim=score or None)

    if not args.skip_crossref:
        for c in corpus:
            if not c['doi']:
                c['cr_status'] = 'no DOI'
                continue
            data = get_json(f'{CROSSREF}/works/{urllib.parse.quote(c["doi"], safe="/")}', args.mailto, pause=0.2)
            if not data:
                c['cr_status'] = 'DOI not found in Crossref'
                continue
            m = data['message']
            ct = (m.get('title') or [''])[0]
            yr = None
            for key in ('published-print', 'published-online', 'issued'):
                dp = (m.get(key) or {}).get('date-parts')
                if dp and dp[0] and dp[0][0]:
                    yr = dp[0][0]
                    break
            c.update(cr_status='ok', cr_title=ct, cr_title_sim=similarity(c['title'], ct), cr_year=yr,
                     cr_venue=(m.get('container-title') or [''])[0], cr_type=m.get('type'))
    return corpus


# ------------------------------------------------------------------ step 2: run queries
def run_query(q, corpus, args):
    qtext = q['openalex_query'].strip()
    field = (q.get('field') or 'title_and_abstract').strip()
    base = f'{field}.search:{urllib.parse.quote(qtext)}'
    if (q.get('extra_filter') or '').strip():
        base += ',' + q['extra_filter'].strip()
    dflt = date_filter(args)
    flt = base + (',' + dflt if dflt else '')
    meta = get_json(f'{OPENALEX}/works?filter={flt}&per-page=1&select=id', args.mailto)
    n_hits = (meta or {}).get('meta', {}).get('count')

    ids = [c['oa_id'] for c in corpus if c.get('oa_id')]
    found = set()
    for i in range(0, len(ids), 50):
        batch = '|'.join(ids[i:i + 50])
        data = get_json(f'{OPENALEX}/works?filter={flt},ids.openalex:{batch}&per-page=50&select=id', args.mailto)
        found |= {short_id(w['id']) for w in (data or {}).get('results', [])}

    hits = []
    if args.export_hits > 0:
        cursor, fetched = '*', 0
        while cursor and fetched < args.export_hits:
            per = min(200, args.export_hits - fetched)
            data = get_json(f'{OPENALEX}/works?filter={flt}&per-page={per}&cursor={cursor}&select={SELECT}', args.mailto)
            res = (data or {}).get('results', [])
            for w in res:
                loc = (w.get('primary_location') or {}).get('source') or {}
                hits.append({'openalex_id': short_id(w['id']), 'in_corpus': 'yes' if short_id(w['id']) in CORPUS_IDS else '',
                             'doi': norm_doi(w.get('doi')), 'year': w.get('publication_year'),
                             'title': w.get('display_name'), 'venue': loc.get('display_name'), 'type': w.get('type')})
            fetched += len(res)
            cursor = (data or {}).get('meta', {}).get('next_cursor') if res else None
    all_ids = set()
    if args.union_hits and n_hits:
        cursor = '*'
        while cursor:
            data = get_json(f'{OPENALEX}/works?filter={flt}&per-page=200&cursor={cursor}&select=id', args.mailto)
            res = (data or {}).get('results', [])
            all_ids |= {short_id(w['id']) for w in res}
            cursor = (data or {}).get('meta', {}).get('next_cursor') if res else None
    return n_hits, found, hits, all_ids


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--corpus', required=True)
    ap.add_argument('--queries', required=True)
    ap.add_argument('--mailto', required=True, help='e-mail for the OpenAlex/Crossref polite pool')
    ap.add_argument('--from-date', default='2021-01-01')
    ap.add_argument('--to-date', default='2026-12-31')
    ap.add_argument('--no-date-filter', action='store_true')
    ap.add_argument('--date-slack', type=int, default=1,
                    help='years subtracted from --from-date in the API filter, because OpenAlex often dates '
                         'a paper by its online-first year (default 1); recall is still computed on --from-date')
    ap.add_argument('--skip-crossref', action='store_true')
    ap.add_argument('--export-hits', type=int, default=0)
    ap.add_argument('--out', default='results')
    ap.add_argument('--api-key', default=None, help='OpenAlex API key (optional; raises rate limits)')
    ap.add_argument('--resolved', default=None, help='corpus_resolved.csv from an earlier run: skips step 1')
    ap.add_argument('--pause', type=float, default=0.35, help='seconds between requests')
    ap.add_argument('--manual-ids', default=None, help='CSV (bibkey, openalex_id) for records identified by hand')
    ap.add_argument('--union-hits', action='store_true',
                    help='download the IDs of all hits to count unique records across queries (deduplicated total)')
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    run_date = datetime.date.today().isoformat()

    corpus = read_corpus(args.corpus)
    queries = read_queries(args.queries)
    print(f'corpus: {len(corpus)} records; queries: {len(queries)}; run date {run_date}')

    global API_KEY, PAUSE
    API_KEY, PAUSE = args.api_key, args.pause
    if args.resolved:
        print(f'step 1: re-using resolved records from {args.resolved}')
        with open(args.resolved, encoding='utf-8') as f:
            prev = {r['bibkey']: r for r in csv.DictReader(f)}
        for c in corpus:
            p = prev.get(c['bibkey'], {})
            for k, v in p.items():
                if k not in ('bibkey', 'year', 'doi', 'title') and v:
                    c[k] = v
            c['oa_id'] = p.get('oa_id') or None
        recheck = [c for c in corpus if c.get('oa_id') and float(c.get('title_sim') or 0) < 0.80
                   and not title_prefix(c['title'], c.get('oa_title'))]
        if recheck:
            print(f'  re-checking {len(recheck)} records whose DOI points to another work')
            resolve(recheck, args, skip_doi=True)
        missing = [c for c in corpus if not c.get('oa_id')]
        if missing:
            print(f'  retrying {len(missing)} records not found before: {", ".join(c["bibkey"] for c in missing)}')
            resolve(missing, args, skip_doi=True)
    else:
        print('step 1: resolving corpus records in OpenAlex' + ('' if args.skip_crossref else ' and Crossref'))
        resolve(corpus, args)
    if args.manual_ids:
        apply_manual_ids(corpus, args.manual_ids, args)
    n_res = sum(1 for c in corpus if c.get('oa_id'))
    print(f'  found in OpenAlex: {n_res}/{len(corpus)}')
    cols = ['bibkey', 'year', 'doi', 'title', 'oa_id', 'match', 'oa_title', 'oa_year', 'title_sim', 'oa_doi', 'doi_problem',
            'cr_status', 'cr_title', 'cr_title_sim', 'cr_year', 'cr_venue', 'cr_type']
    with open(os.path.join(args.out, 'corpus_resolved.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
        w.writeheader(); w.writerows(corpus)

    CORPUS_IDS.update(c['oa_id'] for c in corpus if c.get('oa_id'))
    with open(os.path.join(args.out, 'bib_doi_problems.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['bibkey', 'problem', 'suggested_doi'])
        for c in corpus:
            if c.get('doi_problem'):
                w.writerow([c['bibkey'], c['doi_problem'], c.get('oa_doi') or ''])
    window = [c for c in corpus if in_window(c['year'], args)]
    window_ids = {c['oa_id'] for c in window if c.get('oa_id')}
    print(f'step 2: running queries (corpus records in date window: {len(window)}, resolvable: {len(window_ids)})')
    coverage = {c['bibkey']: {} for c in corpus}
    log_rows, union, union_hits = [], set(), set()
    for q in queries:
        n_hits, found, hits, ids_q = run_query(q, corpus, args)
        union |= found
        union_hits |= ids_q
        for c in corpus:
            coverage[c['bibkey']][q['block_id']] = 'yes' if c.get('oa_id') in found else ''
        n_found_window = len(found & window_ids)
        recall = round(n_found_window / len(window), 3) if window else None
        targets = [t.strip().lower() for t in (q.get('target') or '').split(';') if t.strip()]
        tgt = [c for c in window if targets and any(t in c.get('boxes', '').lower() for t in targets)]
        tgt_found = [c for c in tgt if c.get('oa_id') in found]
        tgt_missed = [c['bibkey'] for c in tgt if c.get('oa_id') not in found]
        log_rows.append({'run_date': run_date, 'database': 'OpenAlex', 'block_id': q['block_id'], 'name': q.get('name', ''),
                         'query_version': q.get('query_version', ''), 'field': (q.get('field') or 'title_and_abstract'),
                         'extra_filter': q.get('extra_filter', ''),
                         'date_window': 'none' if args.no_date_filter else f'{args.from_date}..{args.to_date}',
                         'api_date_filter': date_filter(args) or 'none',
                         'query': q['openalex_query'], 'n_hits': n_hits, 'n_corpus_in_window': len(window),
                         'n_corpus_found': n_found_window, 'recall': recall,
                         'n_target': len(tgt), 'n_target_found': len(tgt_found),
                         'target_recall': round(len(tgt_found) / len(tgt), 3) if tgt else '',
                         'target_missed': '; '.join(tgt_missed)})
        tmsg = f", own section {len(tgt_found)}/{len(tgt)}" if tgt else ''
        print(f"  {q['block_id']}: hits {n_hits}, corpus found {n_found_window}/{len(window)}{tmsg}"
              + (f"  missed: {', '.join(tgt_missed)}" if tgt_missed else ''), flush=True)
        if hits:
            with open(os.path.join(args.out, f"hits_{q['block_id']}.csv"), 'w', newline='', encoding='utf-8') as f:
                w = csv.DictWriter(f, fieldnames=list(hits[0].keys()))
                w.writeheader(); w.writerows(hits)

    n_union = len(union & window_ids)
    log_rows.append({'run_date': run_date, 'database': 'OpenAlex', 'block_id': 'ALL', 'name': 'union of all queries',
                     'query_version': '', 'field': '', 'extra_filter': '',
                     'date_window': 'none' if args.no_date_filter else f'{args.from_date}..{args.to_date}',
                         'api_date_filter': date_filter(args) or 'none',
                     'query': '', 'n_hits': len(union_hits) if args.union_hits else '',
                     'n_corpus_in_window': len(window), 'n_corpus_found': n_union,
                     'recall': round(n_union / len(window), 3) if window else None,
                     'n_target': '', 'n_target_found': '', 'target_recall': '', 'target_missed': ''})
    print(f'  union of all queries: {n_union}/{len(window)}'
          + (f'; unique records across all queries: {len(union_hits)}' if args.union_hits else ''))

    log_path = os.path.join(args.out, 'search_log.csv')
    new = not os.path.exists(log_path)
    with open(log_path, 'a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(log_rows[0].keys()))
        if new:
            w.writeheader()
        w.writerows(log_rows)

    blocks = [q['block_id'] for q in queries]
    with open(os.path.join(args.out, 'coverage.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['bibkey', 'year', 'in_date_window', 'openalex_id'] + blocks + ['found_any'])
        for c in corpus:
            cov = coverage[c['bibkey']]
            w.writerow([c['bibkey'], c['year'], 'yes' if in_window(c['year'], args) else 'no', c.get('oa_id') or '']
                       + [cov.get(b, '') for b in blocks] + ['yes' if any(cov.values()) else ''])
    with open(os.path.join(args.out, 'missed.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['bibkey', 'year', 'title', 'reason'])
        for c in window:
            if not c.get('oa_id'):
                w.writerow([c['bibkey'], c['year'], c['title'], 'not found in OpenAlex'])
            elif c['oa_id'] not in union:
                w.writerow([c['bibkey'], c['year'], c['title'], 'not retrieved by any query'])
    print(f'done; results in {args.out}/')


if __name__ == '__main__':
    main()
