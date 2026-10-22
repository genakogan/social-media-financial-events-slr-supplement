# Supplementary material: Connecting Social Media Analysis and Financial Market Events — A Systematic Survey

Supplementary data and code for the systematic review *Connecting Social Media Analysis and Financial
Market Events: A Systematic Survey* (manuscript submitted to *Array*).

The repository supports the subsection **Reproducibility of the Review** of the manuscript. It contains
the study-level register of the 126 included works (Supplementary Table S1), the corrected bibliographic
database, the metadata check against OpenAlex and Crossref, and a retrospective known-item retrieval check
in OpenAlex with its protocol, scripts, run outputs and audit trail.

## Quick verification (offline, about one minute)

Requirements: Python 3.9 or later.

```bash
pip install -r requirements.txt
python3 verify_repository.py
```

`verify_repository.py` needs no network access and changes no file. It checks that

1. every SHA-256 hash written before a run (`retrieval_check/history/MANIFEST*.txt`) matches the file;
2. `split_corpus.py` reproduces the development/validation split exactly from Supplementary Table S1;
3. `fix_bib.py` reproduces the corrected bibliography and its change log exactly from the original `.bib`;
4. `make_validation_table.py` reproduces the LaTeX table of the retrieval check exactly from the run outputs;
5. the Wilson 95% confidence intervals and the record counts are arithmetically correct;
6. Supplementary Table S1 has 126 studies, reproduces every count of the PRISMA flow diagram, and its
   validation set and per-study results agree with `split.csv` and the run outputs;
7. the result stated in `PROTOCOL.md` (Section 9) and in the run summaries agrees with the run outputs;
8. the per-study files of the final run in `run_output_final/` agree with the summary.

The last line of the output is `ALL CHECKS PASSED` or `SOME CHECKS FAILED`.

## What the material shows, and what it does not

* **Corpus.** The register lists all 126 included works with their PRISMA category, manuscript sections,
  and, for 84 studies, their methodological class (C1–C6, F1–F5; definitions and assignment procedure on
  sheet `class_definitions`). Spreadsheet formulas recompute every category count of the PRISMA flow
  diagram (59 / 40 / 27; each study counted once; eight overlaps) and the publication-type composition.
* **Metadata.** Bibliographic records were checked against OpenAlex and DOIs against Crossref; 17
  corrections (10 DOIs) and one new entry are listed in `bibliography/bib_corrections_log.csv`.
* **Search and screening.** The original search and screening are documented at the aggregate level in the
  manuscript (Section 2.2, Table 2, PRISMA diagram). Individual deduplication and exclusion decisions are
  not part of this repository.
* **Known-item retrieval check.** One protocol (`retrieval_check/PROTOCOL.md`). A title query of 27 terms,
  derived by fixed rules from a random half of the included studies published 2021–2026 (development set)
  and restricted to the OpenAlex subject fields of the development studies, retrieved 29 of the 38 studies
  of the other half (validation set) in OpenAlex and returned 311,556 records (20 October 2026). The
  subject-field restriction was chosen after the fields of the validation studies had been inspected, so
  it is not independently validated; it removed 41.1% of the records (528,902 without it on the same day)
  but none of the included studies retrieved by the original query.
* **What the check does not show.** It measures known-item retrieval within the included corpus. Because
  both samples come from that corpus, it cannot establish the completeness, representativeness or
  sensitivity of the original search, and it does not show that the records removed by the field
  restriction contain no other relevant studies.

### Result of the retrieval check (final run, 20 October 2026)

| Outcome | Value |
|---|---|
| Records returned | 311,556 (528,902 without the subject-field restriction on the same day; −41.1%) |
| Validation set, all 38 studies | 29/38 = 76.3% (Wilson 95% CI 60.8–87.0%) |
| Validation set, 36 studies indexed in OpenAlex | 29/36 = 80.6% (95% CI 65.0–90.2%) |
| Development set | 42/44 = 95.5% |
| Validation studies indexed but not retrieved (7) | hrckova2025autonomation, liu2024exploring, smith2024unraveling, su2025emotionally, yang2025price, bradley2024place, roy2024unveiling |
| Validation studies not indexed in OpenAlex (2) | cayuela2025influence, kumarsocial |

Restrictions: title search; publication dates 2020–2026; ineligible document types excluded; OpenAlex
fields Social Sciences; Economics, Econometrics and Finance; Computer Science; Physics and Astronomy;
Decision Sciences; no language restriction (the English-language criterion is applied at screening).

## Contents

| Path | Content |
|---|---|
| `README.md` | This file. |
| `LICENSE` | Apache License 2.0. |
| `verify_repository.py` | Offline verification of the repository (see above). |
| `requirements.txt` | Python packages: `openpyxl` (reads the register), `certifi` (HTTPS certificates). |
| `Supplementary_Table_S1_Corpus_Register.xlsx` | Supplementary Table S1. Sheet `README` explains all sheets; `codebook` defines every column; `decisions_log` records every decision. Retrieval check: sheets `search_protocol`, `validation_result`, `validation_terms`, `protocol_history`, `openalex_fields`. |
| `bibliography/surveybib.bib` | Bibliographic database as submitted, before corrections. |
| `bibliography/surveybib_corrected.bib` | Corrected bibliographic database used by the revised manuscript. |
| `bibliography/bib_corrections_log.csv` | Every change: field, old value, new value, reason, source. |
| `metadata_check/corpus_resolved.csv` | Metadata check of 19 October 2026 (before corrections): OpenAlex record and title match, Crossref status for each study. |
| `metadata_check/bib_doi_problems.csv` | DOIs that resolved to a different work, with the DOI of the matching record. |
| `metadata_check/no_queries.csv` | Empty query list, so that `verify_corpus.py` runs the metadata check only. |
| `retrieval_check/PROTOCOL.md` | **The protocol** of the known-item retrieval check: split, retrieval restrictions, candidate terms, term enrichment and threshold selection, query, run and outcomes, reporting, the record of when each rule was fixed (Section 8) and the result (Section 9). |
| `retrieval_check/split.csv` | Development (44) / validation (38) split; seed 20261019, stratified by PRISMA category. |
| `retrieval_check/candidates.csv` | Candidate terms derived from the development titles and Table 2. |
| `retrieval_check/corpus_ids.csv` | OpenAlex IDs of the 82 studies published 2021–2026 (80 indexed). |
| `retrieval_check/run_output/` | Term counts and enrichment ratios (`term_counts.csv`), the frozen term query (`query_validation.txt`, SHA-256 in `protocol_log.json`), and the original pre-specified run without the subject-field restriction (19 October 2026: `retrieval.csv`, `summary.txt`). |
| `retrieval_check/run_output_final/` | **The reported run** (20 October 2026): files written by `run_final.py` (`summary_final.txt`, `retrieval_final.csv`, `records_by_field.csv`, `protocol_log_final.json`) and `results_final.json` (the numbers of the summary in machine-readable form). Additional descriptive count, not part of the protocol: `summary_types.txt`, `studies_types.csv`, `types_summary.json` (records and included studies by OpenAlex source type and work type). |
| `retrieval_check/run_output_v2/` | Intermediate, dropped and rejected runs, retained as part of the methodological audit trail (PROTOCOL.md, Section 8): `summary_v2A.txt`, `summary_v2E.txt`, `results_v2.json`. |
| `retrieval_check/validation_table.tex` | LaTeX table of the retrieval check as used in the manuscript (reproduced by `verify_repository.py`). |
| `retrieval_check/history/` | The dated protocol documents and the SHA-256 manifests written before each run; `history/README.md` explains them. |
| `retrieval_check/*.py` | `split_corpus.py` (protocol Section 1), `derive_terms.py` (Section 3), `run_validation.py` (Sections 4–5: counts, threshold, frozen term query; original run), `run_final.py` (Sections 5–6: restrictions and final run), `show_fields.py` (OpenAlex field, subfield and primary topic of the 82 studies), `count_by_source_type.py` (descriptive: records by source type and work type; nothing filtered), `verify_corpus.py` (HTTP helper). Scripts of the other runs in the audit trail: `run_step3.py` (re-execution of the matching step), `run_v2A.py`, `run_v2E.py`, `run_v2.py`. |
| `scripts/` | `fix_bib.py` (applies the bibliographic corrections), `make_validation_table.py` (LaTeX table), `check_corrected_dois.py` (checks every changed DOI in Crossref), `verify_corpus.py` (metadata check), `extract_citations.py` and `build_corpus.py` (citation inventory and register; these two read the manuscript source, which is not included). |

## Reproducing the OpenAlex and Crossref queries (online)

OpenAlex and Crossref are queried through their public APIs. `--mailto` is your e-mail address (the
polite pool of both services); an OpenAlex API key is optional (`--api-key`, free at
https://openalex.org/settings/api) and raises the daily limit. No key is stored in this repository.
Use a new output folder (`rerun`) so that the stored outputs are not overwritten.

```bash
cd retrieval_check

# Protocol Section 1: split of the included studies (reproduces split.csv exactly; offline)
python3 split_corpus.py ../Supplementary_Table_S1_Corpus_Register.xlsx

# Sections 3-5: term counts, enrichment ratios, threshold, frozen term query, original run
# (about 95 OpenAlex requests; writes rerun/term_counts.csv, query_validation.txt, protocol_log.json,
#  retrieval.csv, summary.txt)
python3 run_validation.py --register ../Supplementary_Table_S1_Corpus_Register.xlsx --mailto you@example.org --out rerun

# Sections 5-6: date, document-type and subject-field restrictions; final run (about 9 requests;
# writes rerun/summary_final.txt, retrieval_final.csv, records_by_field.csv, protocol_log_final.json)
python3 run_final.py --v1 rerun --mailto you@example.org --out rerun

# OpenAlex field, subfield and primary topic of the 82 studies (2 requests; writes fields_check.csv)
python3 show_fields.py --mailto you@example.org

# descriptive: records of the final query by source type and work type (about 5 requests)
python3 count_by_source_type.py --mailto you@example.org --final rerun --v1 rerun

# LaTeX table from the stored outputs (offline)
python3 ../scripts/make_validation_table.py run_output

# Crossref check of every changed DOI (about 12 requests; writes doi_check.csv)
cd ../bibliography
python3 ../scripts/check_corrected_dois.py --mailto you@example.org

# metadata check of all 126 studies in OpenAlex and Crossref (about 250 requests;
# writes rerun_metadata/corpus_resolved.csv and bib_doi_problems.csv)
cd ..
python3 scripts/verify_corpus.py --corpus Supplementary_Table_S1_Corpus_Register.xlsx \
    --queries metadata_check/no_queries.csv --mailto you@example.org --out rerun_metadata
```

Notes:

* OpenAlex is updated continuously, so a new run can give slightly different counts, ratios and records
  than the runs of 19–20 October 2026 stored here (without the subject-field restriction the query
  returned 528,412 records on 19 October and 528,902 on 20 October 2026; the reduction by the restriction
  is computed between the two counts of 20 October). The stored outputs are the reference for the
  reported numbers.
* A new metadata check uses the register with the corrected DOIs, so it reports fewer DOI problems than
  `metadata_check/` (made before the corrections).
* `derive_terms.py` reads the development titles from the register and the Table 2 keywords from the
  manuscript source. Its output, `candidates.csv`, is included and its hash is recorded in
  `history/MANIFEST.txt`; the Table 2 strings are also on sheet `search_concepts_table2` of
  Supplementary Table S1.
* Confidence intervals are Wilson score intervals (`wilson()` in `run_validation.py`).
* Offline matching of the development titles was used exclusively for threshold selection; all
  retrieval outcomes were determined from the actual OpenAlex search results.

## How the protocol was fixed (audit trail)

`PROTOCOL.md`, Section 8, records the order of events; Supplementary Table S1, sheet `protocol_history`,
gives the numbers. A SHA-256 documents the exact configuration that was run; it does not by itself show
that the configuration was chosen independently of the validation results.

* 19 October 2026: split, candidate terms, term enrichment, threshold, date and document-type
  restrictions were fixed before any OpenAlex count. The term query was frozen and run without the
  subject-field restriction (original pre-specified configuration): 528,412 records; validation 29/38.
  In the first execution the register file used had no OpenAlex identifiers, so the matching step was
  re-executed with the same frozen query (`run_step3.py`; recorded in `run_output/protocol_log.json`,
  `deviations`).
* 20 October 2026, after that result: a language filter (English only; 427,734 records; validation 27/38)
  and the subject-field restriction (fields of the development studies; with the language filter 247,876
  records; validation 27/38) were tested. The field rule was written before any field data were retrieved.
  The two validation studies lost, `cui2025toward` (W4415736465) and `goldsmith2025causal` (W7106255595),
  have no language assigned in OpenAlex. Every indexed validation study has its primary topic in one of
  the five fields kept (Social Sciences 21, Economics 9, Computer Science 4, Physics and Astronomy 1,
  Decision Sciences 1; sheet `openalex_fields`).
* 20 October 2026: two variants that replaced generic terms by phrases were run once each and rejected,
  because they lost validation studies (297,641 records, validation 24/38; 49,580 records, validation
  12/38).
* 20 October 2026: the language filter was dropped, because it removes works without an assigned language,
  including two included studies. The final configuration was hashed before its run
  (`history/MANIFEST_final.txt`), but after the fields of the validation studies were known, so the
  subject-field restriction is not independently validated. Final run: 311,556 records; validation 29/38,
  the same studies as the original configuration; development 42/44. The final configuration is used for
  the reported filtered retrieval result, while the original pre-specified configuration and all
  intermediate runs are retained as part of the methodological audit trail.
* 20 October 2026, after that run: `PROTOCOL.md` was revised editorially (Section 8, last item); no rule,
  restriction, query or result was changed. The version hashed before the run is
  `history/PROTOCOL_final_prerun.md`.
* Additional descriptive count (not part of the protocol): of the 311,556 records, 175,350 (56.3%) have a
  journal as source. A journal-only restriction was considered and not applied: it would lose four
  retrieved validation studies (validation 25/38) and exclude conference papers and preprints, which the
  review admits.

## Repository and license

Repository: https://github.com/genakogan/finance-sentiment-analysis

Licensed under the Apache License, Version 2.0 (see `LICENSE`).

## Method reference

Hausner E, Waffenschmidt S, Kaiser T, Simon M. Routine development of objectively derived search
strategies. *Systematic Reviews* 2012;1:19. https://doi.org/10.1186/2046-4053-1-19
