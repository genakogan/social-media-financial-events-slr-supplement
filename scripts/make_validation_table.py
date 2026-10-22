#!/usr/bin/env python3
"""LaTeX table of the retrospective known-item retrieval check (tab:retrievability_check), following the
protocol (PROTOCOL.md): result of the final run (run_output_final/results_final.json); the term query
and threshold are read from run_output/.

Usage: python3 make_validation_table.py [run_output_folder] [results_final.json] [results_v2.json]
Output: validation_table.tex"""
import csv, json, os, re, sys
from collections import defaultdict

RUN = sys.argv[1] if len(sys.argv) > 1 else 'run_output'
BASE = os.path.dirname(os.path.abspath(RUN))
FP = sys.argv[2] if len(sys.argv) > 2 else os.path.join(BASE, 'run_output_final', 'results_final.json')
V2P = sys.argv[3] if len(sys.argv) > 3 else os.path.join(BASE, 'run_output_v2', 'results_v2.json')
log = json.load(open(f'{RUN}/protocol_log.json', encoding='utf-8'))
ret = list(csv.DictReader(open(f'{RUN}/retrieval.csv', encoding='utf-8')))
E = json.load(open(FP, encoding='utf-8'))
A = json.load(open(V2P, encoding='utf-8'))['variants']['A']
lost = {r['bibkey'] for r in ret if r['set'] == 'validation' and r['retrieved'] == 'True'} - (
    {r['bibkey'] for r in ret if r['set'] == 'validation'} - set(E['validation_missed']) - set(E['validation_not_indexed']))

THEMES = [('Social media analysis', 'Social media analysis'), ('Financial market events', 'Financial market events'),
          ('Cross-Domain Events and Causality', 'Cross-domain events and causality')]
first, final = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
for r in ret:
    if r['set'] != 'validation':
        continue
    hit = r['retrieved'] == 'True'
    for c, h in ((first, hit), (final, hit and r['bibkey'] not in lost)):
        c[r['theme']][0] += h
        c[r['theme']][1] += 1

res = log['results']
v1v, v1i, v1d = res['validation_all'], res['validation_indexed'], res['development_all']
ev, ei, ed = E['validation_all'], E['validation_indexed'], E['development']
assert sum(final[t][0] for t, _ in THEMES) == ev['retrieved'] == 29
assert sum(first[t][0] for t, _ in THEMES) == v1v['retrieved'] == 29


def pc(x):
    return f"{100 * x:.1f}\\%"


def ci(d):
    return f"{d['retrieved']}/{d['n']} ({pc(d['share'])}; 95\\% CI {pc(d['ci95'][0])}--{pc(d['ci95'][1])})"


query = re.sub(r'"([^"]+)"', r"``\1''", log['query'])
missed = E['validation_missed']
notidx = E['validation_not_indexed']
fields = '; '.join(v[0] for v in E['fields_kept'].values())

rows = '\n'.join(f"{label} & {final[t][0]}/{final[t][1]} \\\\" for t, label in THEMES)
cut = E['records_term_query'] - E['records']

tex = rf"""\begin{{table}}[!htbp]
\centering
\caption{{\textcolor{{blue}}{{Retrospective known-item retrieval check in OpenAlex (20 October 2026): included studies published 2021--2026 retrieved by a title query derived from the development set by fixed rules and restricted to the OpenAlex subject fields of the development set. The check measures retrieval of known included studies; it does not reproduce the original search or estimate its sensitivity.}}}}
\label{{tab:retrievability_check}}
\scriptsize
\begin{{tabular}}{{p{{5.0cm}} p{{7.6cm}}}}
\hline
\textbf{{Validation set, by theme}} & \textbf{{Studies retrieved}} \\
\hline
{rows}
\hline
\textbf{{Validation set, all}} & \textbf{{{ci(ev)}}} \\
Validation set, indexed in OpenAlex & {ci(ei)} \\
Development set & {ed['retrieved']}/{ed['n']} ({pc(ed['share'])}) \\
Records returned & {E['records']:,} ({E['records_term_query']:,} without the subject-field restriction on the same day; $-${100 * cut / E['records_term_query']:.1f}\%) \\
\hline
\multicolumn{{2}}{{p{{13.0cm}}}}{{\textit{{Title query ({log['n_terms']} terms):}} {query}}} \\
\multicolumn{{2}}{{p{{13.0cm}}}}{{\textit{{Restrictions:}} publication dates 2020--2026; ineligible document types excluded; OpenAlex fields {fields}; no language restriction.}} \\
\hline
\end{{tabular}}

\vspace{{4pt}}
\begin{{minipage}}{{13.4cm}}
\scriptsize
\textit{{Note.}} The included studies published 2021--2026 were split at random within each category of the flow diagram into a development set (44) and a validation set (38). Candidate terms were the words and two-word phrases occurring in at least two development titles and the keywords of Table~\ref{{tab:search_concepts}}; terms enriched in the development titles relative to OpenAlex were kept, with the threshold chosen on the development set (R = {log['R']}); offline matching of the development titles was used only for this choice, and all retrieval figures are from the OpenAlex searches. Publication dates start in 2020 because OpenAlex dates some works by their first online version. The subject fields are those of the primary topics of the development studies; the restriction was chosen after the fields of the validation studies had been inspected and is therefore not independently validated. It did not remove any of the known included studies retrieved by the original pre-specified query, which retrieved the same validation studies. A language filter was tested and dropped because it lost two validation studies to which OpenAlex assigns no language (\citealp{{{','.join(A['missed_beyond_v1'])}}}); the language criterion is applied at screening. Validation studies indexed in OpenAlex but not retrieved: \citealp{{{','.join(missed)}}}; not indexed in OpenAlex: \citealp{{{','.join(notidx)}}}. Protocol, terms, counts, per-study results and earlier configurations are reported in Supplementary Table~S1.
\end{{minipage}}
\end{{table}}
"""
open('validation_table.tex', 'w', encoding='utf-8').write(tex)
print('written validation_table.tex; final', dict(final), 'first', dict(first))
