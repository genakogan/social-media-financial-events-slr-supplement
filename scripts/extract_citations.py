#!/usr/bin/env python3
"""
extract_citations.py -- reconstruct the citation inventory of a LaTeX manuscript.

Reads a .tex file and a .bib file and writes three CSV files:
  citation_occurrences.csv  one row per (citation command, key) occurrence
  citation_keys.csv         one row per unique cited key, with all locations
  bib_entries.csv           one row per BibTeX entry, with cited / uncited flag

Rules
  * Line comments (unescaped %) and \\begin{comment}...\\end{comment} blocks are ignored.
  * Everything after \\end{document} is ignored.
  * Recognised commands: \\cite, \\citep, \\citet, \\citealp, \\citealt, \\citeauthor,
    \\citeyear, \\citeyearpar, \\Citep, \\Citet, \\nocite and starred variants, with up
    to two optional [..] arguments. Several comma-separated keys per command are split.
  * Keys are preserved exactly (case-sensitive).
  * Section numbers are computed from \\section / \\subsection / \\subsubsection in
    order of appearance; after \\appendix sections are lettered (A, B, ...).
  * Class context (C1-C6, F1-F5) is taken from paragraph headings of the form
    \\textbf{C1 - ...} / \\textbf{F1 - ...} and resets at every new (sub)section.
  * Table context is the \\label of the enclosing table / table* environment.

Usage:  python3 extract_citations.py manuscript.tex surveybib.bib [outdir]
"""
import csv, os, re, sys
from collections import OrderedDict

CITE_RE = re.compile(
    r'\\(cite|citep|citet|citealp|citealt|citeauthor|citeyear|citeyearpar|Citep|Citet|nocite)\*?'
    r'\s*(?:\[[^\]]*\]\s*){0,2}\{([^}]*)\}')
SEC_RE = re.compile(r'\\(section|subsection|subsubsection)\*?\s*\{')
CLASS_RE = re.compile(r'\\textbf\{\s*([CF][1-6])\s*-')
BEGIN_TAB = re.compile(r'\\begin\{(table\*?)\}')
END_TAB = re.compile(r'\\end\{(table\*?)\}')
LABEL_RE = re.compile(r'\\label\{([^}]*)\}')


def strip_comments(lines):
    """Return list of (lineno, active_text) with comments removed."""
    out, in_env = [], False
    for n, line in enumerate(lines, 1):
        s = line
        m = re.search(r'(?<!\\)%', s)
        if m:
            s = s[:m.start()]
        if in_env:
            if '\\end{comment}' in s:
                s = s.split('\\end{comment}', 1)[1]
                in_env = False
            else:
                s = ''
        if '\\begin{comment}' in s:
            before, after = s.split('\\begin{comment}', 1)
            if '\\end{comment}' in after:
                s = before + after.split('\\end{comment}', 1)[1]
            else:
                s, in_env = before, True
        out.append((n, s))
        if '\\end{document}' in s:
            break
    return out


def braced(text, start):
    """text[start] is just after an opening brace; return content up to matching brace."""
    depth, i = 1, start
    while i < len(text) and depth:
        if text[i] == '{' and text[i - 1] != '\\':
            depth += 1
        elif text[i] == '}' and text[i - 1] != '\\':
            depth -= 1
        i += 1
    return text[start:i - 1]


def extract(tex_path):
    lines = open(tex_path, encoding='utf-8').read().split('\n')
    active = strip_comments(lines)

    # pass 1: table spans with labels
    tables, cur = [], None
    for n, s in active:
        if BEGIN_TAB.search(s):
            cur = {'start': n, 'label': ''}
        if cur is not None:
            m = LABEL_RE.search(s)
            if m and not cur['label']:
                cur['label'] = m.group(1)
        if END_TAB.search(s) and cur is not None:
            cur['end'] = n
            tables.append(cur)
            cur = None

    def table_at(n):
        for t in tables:
            if t['start'] <= n <= t['end']:
                return t['label']
        return ''

    # pass 2: walk events in order
    sec = sub = subsub = 0
    appendix = False
    sec_title = sub_title = subsub_title = ''
    cls = ''
    occ = []
    for n, s in active:
        if re.search(r'\\appendix\b', s):
            appendix, sec = True, 0
        events = []
        for m in SEC_RE.finditer(s):
            events.append((m.start(), 'sec', m.group(1), braced(s, m.end())))
        for m in CLASS_RE.finditer(s):
            events.append((m.start(), 'cls', m.group(1), ''))
        for m in CITE_RE.finditer(s):
            events.append((m.start(), 'cite', m.group(1), m.group(2)))
        for pos, kind, a, b in sorted(events):
            if kind == 'sec':
                title = re.sub(r'\s+', ' ', b).strip()
                if a == 'section':
                    sec += 1; sub = subsub = 0
                    sec_title, sub_title, subsub_title = title, '', ''
                elif a == 'subsection':
                    sub += 1; subsub = 0
                    sub_title, subsub_title = title, ''
                else:
                    subsub += 1
                    subsub_title = title
                cls = ''
            elif kind == 'cls':
                cls = a
            else:
                keys = [k.strip() for k in b.split(',') if k.strip()]
                s_lab = chr(64 + sec) if appendix else str(sec)
                num = s_lab + (f'.{sub}' if sub else '') + (f'.{subsub}' if subsub else '')
                title = subsub_title or sub_title or sec_title
                for k in keys:
                    occ.append(OrderedDict(
                        line=n, command='\\' + a, key=k,
                        section_number=num, section_title=title,
                        top_section=f'{s_lab} {sec_title}',
                        class_context=cls, table_label=table_at(n),
                        co_cited='; '.join(x for x in keys if x != k)))
    return occ, tables


# ---------------------------------------------------------------- BibTeX
ENTRY_RE = re.compile(r'@(\w+)\s*\{')


def parse_fields(body):
    fields, i, L = OrderedDict(), 0, len(body)
    while i < L:
        m = re.compile(r'\s*,?\s*([A-Za-z_\-]+)\s*=\s*').match(body, i)
        if not m:
            break
        name, i = m.group(1).lower(), m.end()
        if i < L and body[i] == '{':
            depth, j = 1, i + 1
            while j < L and depth:
                if body[j] == '{':
                    depth += 1
                elif body[j] == '}':
                    depth -= 1
                j += 1
            val, i = body[i + 1:j - 1], j
        elif i < L and body[i] == '"':
            j = body.index('"', i + 1)
            val, i = body[i + 1:j], j + 1
        else:
            m2 = re.compile(r'[^,]*').match(body, i)
            val, i = m2.group(0).strip(), m2.end()
        fields[name] = re.sub(r'\s+', ' ', val).strip()
    return fields


def parse_bib(path):
    text = open(path, encoding='utf-8').read()
    entries, pos = [], 0
    while True:
        m = ENTRY_RE.search(text, pos)
        if not m:
            break
        typ = m.group(1).lower()
        ls = text.rfind('\n', 0, m.start()) + 1
        prefix = text[ls:m.start()]
        depth, j = 1, m.end()
        while j < len(text) and depth:
            if text[j] == '{':
                depth += 1
            elif text[j] == '}':
                depth -= 1
            j += 1
        body = text[m.end():j - 1]
        if typ in ('comment', 'string', 'preamble'):
            pos = j
            continue
        key, _, rest = body.partition(',')
        entries.append(OrderedDict(
            key=key.strip(), type=typ, line=text.count('\n', 0, m.start()) + 1,
            percent_prefixed='%' in prefix, fields=parse_fields(rest)))
        pos = j
    return entries


def main():
    tex, bib = sys.argv[1], sys.argv[2]
    outdir = sys.argv[3] if len(sys.argv) > 3 else '.'
    os.makedirs(outdir, exist_ok=True)
    occ, tables = extract(tex)
    entries = parse_bib(bib)
    bibkeys = {e['key'] for e in entries}

    with open(os.path.join(outdir, 'citation_occurrences.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(occ[0].keys()))
        w.writeheader(); w.writerows(occ)

    keys = OrderedDict()
    for o in occ:
        d = keys.setdefault(o['key'], {'n': 0, 'sections': [], 'tables': [], 'classes': [], 'first_line': o['line']})
        d['n'] += 1
        sec = f"{o['section_number']} {o['section_title']}"
        if sec not in d['sections']:
            d['sections'].append(sec)
        if o['table_label'] and o['table_label'] not in d['tables']:
            d['tables'].append(o['table_label'])
        if o['class_context'] and o['class_context'] not in d['classes']:
            d['classes'].append(o['class_context'])
    with open(os.path.join(outdir, 'citation_keys.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['key', 'occurrences', 'first_line', 'in_bib', 'sections', 'tables', 'class_context_in_text'])
        for k, d in keys.items():
            w.writerow([k, d['n'], d['first_line'], k in bibkeys, ' | '.join(d['sections']),
                        ' | '.join(d['tables']), ' | '.join(d['classes'])])
    with open(os.path.join(outdir, 'bib_entries.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['key', 'type', 'line', 'percent_prefixed', 'cited', 'author', 'title', 'year',
                    'journal_or_booktitle', 'doi', 'url'])
        for e in entries:
            fl = e['fields']
            w.writerow([e['key'], e['type'], e['line'], e['percent_prefixed'], e['key'] in keys,
                        fl.get('author', ''), fl.get('title', ''), fl.get('year', ''),
                        fl.get('journal', fl.get('booktitle', fl.get('institution', ''))),
                        fl.get('doi', ''), fl.get('url', fl.get('howpublished', ''))])
    missing = [k for k in keys if k not in bibkeys]
    print(f'citation occurrences: {len(occ)}')
    print(f'unique cited keys:    {len(keys)}')
    print(f'bib entries parsed:   {len(entries)} '
          f'(%-prefixed: {sum(e["percent_prefixed"] for e in entries)})')
    print(f'cited keys missing from bib: {missing}')
    print(f'tables found: {len(tables)}')


if __name__ == '__main__':
    main()
