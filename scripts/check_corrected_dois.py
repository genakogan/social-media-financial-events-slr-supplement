#!/usr/bin/env python3
"""Check every DOI that was changed or added in surveybib_corrected.bib against Crossref.

For each row of bib_corrections_log.csv that sets a DOI (field 'doi' or 'new entry'), the script
looks the new DOI up in Crossref and compares the Crossref title with the title in
surveybib_corrected.bib. arXiv DOIs (10.48550/...) are registered with DataCite and are skipped.

  python3 check_corrected_dois.py --mailto you@example.org
Output: doi_check.csv and a summary on screen. About 11 Crossref requests.
"""
import argparse, csv, re, sys, os, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_corpus as vc                     # HTTP helper with retries; similarity()


def bib_title(text, key):
    m = re.search(r'@\w+\s*\{\s*' + re.escape(key) + r'\s*,(.*?)\n\}', text, re.S)
    t = re.search(r'\btitle\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}', m.group(1)) if m else None
    return re.sub(r'[{}]', '', t.group(1)) if t else ''


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--mailto', required=True)
    ap.add_argument('--bib', default='surveybib_corrected.bib')
    ap.add_argument('--log', default='bib_corrections_log.csv')
    args = ap.parse_args()
    bibtext = open(args.bib, encoding='utf-8').read()
    out = []
    for r in csv.DictReader(open(args.log, encoding='utf-8')):
        if r['field'] not in ('doi', 'new entry'):
            continue
        m = re.search(r'doi\s*=\s*\{([^}]+)\}', r['new'])
        doi = (m.group(1) if m else r['new']).strip().rstrip('}').lower()
        if not doi.startswith('10.'):
            continue
        title = bib_title(bibtext, r['bibkey'])
        d = vc.get_json(f'{vc.CROSSREF}/works/{urllib.parse.quote(doi, safe="/")}', args.mailto, pause=0.2)
        if not d:
            out.append({'bibkey': r['bibkey'], 'doi': doi, 'crossref': 'not found', 'crossref_title': '', 'similarity': '', 'verdict': 'CHECK'})
            continue
        ct = (d['message'].get('title') or [''])[0]
        s = vc.similarity(title, ct)
        out.append({'bibkey': r['bibkey'], 'doi': doi, 'crossref': 'found', 'crossref_title': ct, 'similarity': s,
                    'verdict': 'ok' if s >= 0.8 or vc.title_prefix(title, ct) else 'CHECK'})
    with open('doi_check.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)
    for o in out:
        print(f"{o['verdict']:<6} {o['bibkey']:<28} {o['doi']:<40} {o['similarity']}")
    print(f"\n{sum(o['verdict'] == 'ok' for o in out)} of {len(out)} DOIs confirmed in Crossref -> doi_check.csv")


if __name__ == '__main__':
    main()
