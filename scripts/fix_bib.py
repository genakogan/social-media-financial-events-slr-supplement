#!/usr/bin/env python3
"""Apply verified corrections to surveybib.bib -> surveybib_corrected.bib and write a change log.

Every edit is applied inside the named entry only and must match exactly once,
otherwise the script stops. Sources of each correction are recorded in the log.
"""
import csv, re, sys

SRC, DST, LOG = 'surveybib.bib', 'surveybib_corrected.bib', 'bib_corrections_log.csv'
OA = 'OpenAlex/Crossref check, verify_corpus.py run 2026-10-19'

# (key, field, old_substring, new_substring, reason, source)
EDITS = [
    ('chang2022systematic', 'doi', '10.1016/j.procs.2022.09.374', '10.1016/j.procs.2022.09.373',
     'DOI resolved to another article (A reverse personnel assignment method ...)', OA),
    ('zhou2020two', 'doi', '10.1016/j.ins.2020.01.016', '10.1016/j.ins.2020.01.052',
     'DOI resolved to another article (Recognizing novel patterns via adversarial learning ...)', OA),
    ('mridha2021comprehensive', 'doi', '10.1109/ACCESS.2021.3128879', '10.1109/ACCESS.2021.3129329',
     'DOI resolved to another article (Incremental Attribute Reduction ...)', OA),
    ('anderson2003micro', 'doi', '10.1257/000282803321455214', '10.1257/000282803321455151',
     'DOI resolved to another article (Gravity with Gravitas ...)', OA),
    ('kogan2023social', 'doi', '10.1093/rof/rfad010', '10.1093/rof/rfac058',
     'DOI resolved to another article (Income, Liquidity, and the Consumption Response ...)', OA),
    ('ienca2023artificial', 'doi', '10.1007/s11245-021-09797-0', '10.1007/s11245-023-09940-3',
     'DOI not registered in Crossref; DOI of the matching OpenAlex record', OA),
    ('butts2023mathematical', 'doi', '10.1038/s41598-023-45671-z', '10.1038/s41598-023-45710-2',
     'DOI not registered in Crossref; DOI of the matching OpenAlex record', OA),
    ('smith2024unraveling', 'doi', '10.1007/s12144-023-04628-2', '10.1007/s12144-023-05350-1',
     'DOI not registered in Crossref; DOI of the matching OpenAlex record', OA),
    ('budak2024misunderstanding', 'doi', '10.1038/s41586-024-07328-2', '10.1038/s41586-024-07417-w',
     'DOI not registered in Crossref; DOI of the matching OpenAlex record', OA),
    ('sadeghi2025causal', 'doi', '10.1007/s41060-024-00679-}', '10.1007/s41060-024-00679-7}',
     'DOI truncated (last character missing)', OA),
    ('wang2022causal', 'doi', '  year={2022},\n', '  year={2022},\n  doi={10.1016/j.econlet.2022.110598},\n',
     'DOI missing', 'Full text of the article (Economics Letters 216, 110598)'),
    ('campbell1997econometrics', 'doi', '  isbn      = {9780691043012},\n  doi={10.1017/S1365100598009092}',
     '  isbn      = {9780691043012}',
     'DOI belongs to a 1998 item in Macroeconomic Dynamics about the book, not to the book; ISBN kept', OA),
    ('ghazouani2025virtual', 'year/volume', '  pages={100375},\n  year={2025},',
     '  volume={7},\n  pages={100375},\n  year={2026},',
     'Published in volume 7 (2026); online 2025', 'Full text of the article (Blockchain: Research and Applications 7 (2026) 100375)'),
    ('kim2025news', 'title/author',
     '  title={How social-network attention and sentiment of investors affect commodity futures market returns: New evidence from {China}},',
     '  title={News vs. Social Media: Sentiment Impact on Stock Performance of Big {Tech} Companies},\n'
     '  author={Kim-Hahm, Hyunsun and Abou-Zaid, Ahmed S. and Mohd, Abidalrahman},',
     'Title was copied from liu2023social and authors were missing',
     'DOI record 10.3390/jrfm18120660 (OpenAlex, Crossref, ResearchGate)'),
    ('page2021prisma', 'author', 'Shamseer, Larissa andCharacteristicTetzlaff, Jennifer M',
     'Shamseer, Larissa and Tetzlaff, Jennifer M',
     'Corrupted author field (merged names)', 'Manual correction'),
    ('hegselmann2002opinion', 'journal', 'Journal of Artifical Societies and Social Simulation (JASSS) vol',
     'Journal of Artificial Societies and Social Simulation',
     'Typo in journal name', 'Manual correction'),
    ('stapic2012performing', 'url', '{ttps://', '{https://', 'Malformed URL', 'Manual correction'),
]

text = open(SRC, encoding='utf-8').read()


def entry_span(key):
    m = re.search(r'@\w+\s*\{\s*' + re.escape(key) + r'\s*,', text)
    if not m:
        sys.exit(f'entry not found: {key}')
    depth, i = 0, text.index('{', m.start())
    while True:
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return m.start(), i + 1
        i += 1


log = []
for key, field, old, new, reason, source in EDITS:
    a, b = entry_span(key)
    entry = text[a:b]
    if entry.count(old) != 1:
        sys.exit(f'{key}: expected exactly one match for {old!r}, found {entry.count(old)}')
    text = text[:a] + entry.replace(old, new) + text[b:]
    log.append({'bibkey': key, 'field': field, 'old': old.strip(), 'new': new.strip(), 'reason': reason, 'source': source})

# new entries cited in the revision (appended; logged as "new entry")
ADDITIONS = [
    ('hausner2012routine', """@article{hausner2012routine,
  title={Routine development of objectively derived search strategies},
  author={Hausner, Elke and Waffenschmidt, Siw and Kaiser, Thomas and Simon, Michael},
  journal={Systematic Reviews},
  volume={1},
  number={1},
  pages={19},
  year={2012},
  doi={10.1186/2046-4053-1-19}
}
""", 'Method reference for the validated verification search (subsection Reproducibility of the Review)',
     'Systematic Reviews 1:19 (2012); record checked on the University of Southampton repository (eprints.soton.ac.uk/301322)'),
]
for key, entry, reason, source in ADDITIONS:
    if re.search(r'@\w+\s*\{\s*' + re.escape(key) + r'\s*,', text):
        sys.exit(f'entry already present: {key}')
    text = text.rstrip('\n') + '\n\n' + entry
    log.append({'bibkey': key, 'field': 'new entry', 'old': '', 'new': entry.strip(), 'reason': reason, 'source': source})

open(DST, 'w', encoding='utf-8').write(text)
with open(LOG, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(log[0].keys()))
    w.writeheader(); w.writerows(log)
print(f'{len(log)} changes (corrections and new entries) written to {DST}; log in {LOG}')
