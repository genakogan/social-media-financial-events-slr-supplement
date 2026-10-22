# Known-item retrieval check: protocol

Retrospective check of whether the included studies of the review can be retrieved in OpenAlex by a
title query that is derived by fixed rules from part of the included studies and tested on the others
(objective approach of Hausner E, Waffenschmidt S, Kaiser T, Simon M. Routine development of
objectively derived search strategies. Systematic Reviews 2012;1:19. doi:10.1186/2046-4053-1-19).

The check does not reproduce the original search of the review (Section 2.2, Table 2 and the PRISMA
diagram of the manuscript) and does not estimate its sensitivity. Section 8 records when each rule
was fixed.

## 1. Population and split  (split_corpus.py)
* Included studies published 2021-2026 (register column in_search_window = yes): 82.
* Strata: flow-diagram category (prisma_box). Within each stratum: bibkeys sorted, shuffled with one
  random.Random(20261019) (strata in sorted order); first ceil(n/2) -> development set, rest ->
  validation set.
* Result: 44 development studies, 38 validation studies. The development studies are used to build
  the query; the validation studies are used only to test it.

## 2. Eligibility filters  (applied in OpenAlex)
The filters correspond to the eligibility criteria of the review.
* Publication date 2020-01-01 to 2026-12-31. The window starts one year before the studies checked
  because OpenAlex dates some works by their first online or preprint version (e.g. arnold2022attention,
  published in 2022, is dated 2020).
* Document types excluded: dissertation, dataset, paratext, editorial, letter, erratum, peer-review,
  retraction. All other types are kept, so that journal articles, conference papers, books, book
  chapters and preprints, which the review admits, are not excluded.
* No language filter. The review admits English-language publications only, but OpenAlex assigns the
  language automatically and leaves some works without a language; a language filter excludes them.
  Two included studies (cui2025toward, goldsmith2025causal) have no language assigned and would be
  lost (Section 8). The language criterion is applied when the records are screened, not in the query.
* Subject fields: the OpenAlex field of each work's primary topic must be the primary-topic field of at
  least one development study. The fields are taken from the development studies only. Works without
  a primary topic are excluded by this filter.

## 3. Candidate terms  (derive_terms.py; reads development titles only)
* Titles from the register (surveybib_corrected.bib). Lower case; tokens = runs of letters/digits;
  a fixed stop-word list (in the script); digits-only tokens ignored.
* Plural variants are counted together (trailing -s / -ies removed for counting only; the query uses
  the form most frequent in the development titles).
* Candidates:
  (a) single words and two-word phrases (adjacent, no stop word) that occur in the titles of at least
      two development studies;
  (b) every keyword and quoted phrase of Table 2 (columns "Keywords and Synonyms" and
      "Representative Boolean Search String") that occurs in the title of at least one development study.

## 4. Specificity and threshold  (run_validation.py)
* For every candidate: number of OpenAlex works whose title matches it, with the date and
  document-type filters of Section 2. N = number of works with the same filters and no title
  condition. (Specificity measures how common a term is in the literature; the field filter restricts
  the final query, Section 5.)
* Over-representation ratio r = (development titles containing the term / 44) / (OpenAlex count / N).
* Threshold R: the largest value in the grid {10, 20, 50, 100, 200, 500, 1000} for which the query
  (all candidates with r >= R) still matches at least 90% of the 44 development titles (offline title
  match). If no grid value reaches 90%, the smallest value (10) is used. Offline matching of the
  development titles is used only for this choice; all retrieval outcomes come from OpenAlex searches.
* A two-word phrase is dropped from the query when one of its words is itself a retained single word.

## 5. Query  (run_validation.py builds and freezes the terms; run_final.py adds the filters and runs it)
* One title query (title.search): all retained terms combined with OR.
* Filters: the date, document-type and subject-field filters of Section 2.
* The term query is frozen (SHA-256 recorded) before it is run; run_final.py checks the SHA-256 before
  running and records the full filter string with its SHA-256.

## 6. Run and outcome
* The query is run once in OpenAlex.
* Primary outcome: share of validation studies retrieved, with Wilson 95% confidence interval,
  reported over all 38 and over those indexed in OpenAlex.
* Secondary: share of development studies retrieved; number of records; list of validation studies
  not retrieved; records by OpenAlex field; records not tagged as English (descriptive).
* No change to terms, threshold, filters or query after the run.

## 7. Reporting
* The protocol, the scripts, the frozen query, the filters and all outputs are published with
  Supplementary Table S1. Deviations are reported with their reasons (Section 8).

## 8. Record of how this protocol was fixed
* 19 October 2026, before any term was derived or any count retrieved: Sections 1, 3, 4, the date and
  document-type filters, and the run and outcome rules (history/PROTOCOL_v1.md; hashes in
  history/MANIFEST.txt). The term query was frozen (27 terms, R = 100; SHA-256 51377ba9...a7f6) and run
  without language and field filters: 528,412 records; validation 29/38 (76.3%; 95% CI 60.8-87.0%);
  development 42/44.
  Technical deviation: the first execution used a register file without OpenAlex identifiers, so no
  study could be matched; the matching step was re-executed with the same frozen query (run_step3.py).
* 20 October 2026, after that result: a language filter (English only) and the subject-field filter of
  Section 2 were added (history/PROTOCOL_v2.md, addenda 1 and 2; hashes in history/MANIFEST_v2.txt).
  The field rule was written before any field data were retrieved. English only: 427,734 records,
  validation 27/38; English only and fields: 247,876 records, validation 27/38. The two validation
  studies lost (cui2025toward, goldsmith2025causal) have no language assigned in OpenAlex; their fields
  are kept. The fields of all 82 studies were then read (show_fields.py): all 36 indexed validation
  studies have their primary topic in one of the fields kept.
* 20 October 2026: two variants that also replaced generic terms by phrases (every term with more than
  K = 50,000 or K = 10,000 OpenAlex title matches replaced by its candidate phrases) were run once each
  and not adopted, because they lost validation studies: 297,641 records, validation 24/38; 49,580
  records, validation 12/38.
* 20 October 2026: the language filter was dropped, because it removes works without an assigned
  language, including two included studies. The final query (Sections 2 and 5: term query with date,
  document-type and subject-field filters) was defined before it was run (hashes in MANIFEST_final.txt),
  but after the fields of the validation studies were known. The field filter was thus not specified
  before the first run.

## 9. Result
Completed after the run of run_final.py (run_output_final/).
