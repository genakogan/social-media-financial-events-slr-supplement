# Known-item retrieval check: protocol

Retrospective check of whether the included studies of the review can be retrieved in OpenAlex by a
title query that is derived by fixed rules from part of the included studies and tested on the others
(objective approach of Hausner E, Waffenschmidt S, Kaiser T, Simon M. Routine development of
objectively derived search strategies. Systematic Reviews 2012;1:19. doi:10.1186/2046-4053-1-19).

This experiment measures known-item retrieval within the previously selected corpus. Because both the
development and validation samples originate from that corpus, the results are conditional on the
original study-selection process and cannot establish the completeness, representativeness, or
sensitivity of the original systematic search. The check does not reproduce the original search of
the review (Section 2.2, Table 2 and the PRISMA diagram of the manuscript). Section 8 records when each
rule was fixed.

## 1. Population and split  (split_corpus.py)
* Included studies published 2021-2026 (register column in_search_window = yes): 82.
* Strata: flow-diagram category (prisma_box). Within each stratum: bibkeys sorted, shuffled with one
  random.Random(20261019) (strata in sorted order); first ceil(n/2) -> development set, rest ->
  validation set.
* Result: 44 development studies, 38 validation studies. The development studies are used to build
  the query; the validation studies are used to test it.

## 2. Retrieval restrictions  (applied in OpenAlex)
The date and document-type restrictions follow the eligibility criteria of the review. The
subject-field restriction is not an eligibility criterion: it is an additional restriction of the
search strategy, used to reduce the number of records. It was specified after earlier runs
(Section 8).
* Publication date 2020-01-01 to 2026-12-31. The window starts one year before the studies checked
  because OpenAlex dates some works by their first online or preprint version (e.g. arnold2022attention,
  published in 2022, is dated 2020).
* Document types excluded: dissertation, dataset, paratext, editorial, letter, erratum, peer-review,
  retraction. All other types are kept, so that journal articles, conference papers, books, book
  chapters and preprints, which the review admits, are not excluded.
* No language restriction. The review admits English-language publications only, but OpenAlex assigns
  the language automatically and leaves some works without a language; a language filter excludes them.
  Two included studies (cui2025toward, goldsmith2025causal) have no language assigned and would be
  lost (Section 8). The language criterion is applied when the records are screened, not in the query.
* Subject fields: the OpenAlex field of each work's primary topic must be the primary-topic field of
  at least one development study. The fields are taken from the development
  studies only. Works without a primary topic are excluded by this restriction.

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

## 4. Term enrichment and threshold selection  (run_validation.py)
* For each candidate term, its frequency in the OpenAlex title index was determined under the
  publication-date and document-type restrictions of Section 2. N = number of works under the same
  restrictions and no title condition.
* Over-representation ratio r = (development titles containing the term / 44) / (OpenAlex count / N).
  The ratio measures enrichment of the term in the development set relative to its prevalence in
  OpenAlex. It is used for query construction and does not constitute an estimate of search precision
  or specificity.
* Threshold R: the largest value in the grid {10, 20, 50, 100, 200, 500, 1000} for which the query
  (all candidates with r >= R) still matches at least 90% of the 44 development titles (offline title
  match). If no grid value reaches 90%, the smallest value (10) is used. Offline matching of the
  development titles is used only for this choice; all retrieval outcomes come from OpenAlex searches.
* A two-word phrase is dropped from the query when one of its words is itself a retained single word.

## 5. Query  (run_validation.py builds and freezes the term query; run_final.py adds the restrictions and runs it)
* Term query: one title query (title.search), all retained terms combined with OR; frozen with its
  SHA-256 before it was first run.
* Restrictions: the date, document-type and subject-field restrictions of Section 2; no language
  restriction. run_final.py checks the SHA-256 of the term query and records the full filter string
  with its SHA-256.
* A SHA-256 documents the exact configuration that was run and that it was not changed afterwards; it
  does not by itself show that the configuration was chosen independently of the validation results
  (see Section 8).

## 6. Run and outcomes
* The query is run once in OpenAlex.
* Primary outcome: share of validation studies retrieved, with Wilson 95% confidence interval,
  reported over all 38 and over those indexed in OpenAlex.
* Secondary: share of development studies retrieved; number of records; validation studies indexed in
  OpenAlex but not retrieved, and validation studies not indexed in OpenAlex; records by OpenAlex
  field; records not tagged as English (descriptive).
* No change to terms, threshold, restrictions or query after the run.

## 7. Reporting
* The protocol, the scripts, the frozen query, the restrictions and all outputs are published with
  Supplementary Table S1. Deviations are reported with their reasons (Section 8).

## 8. Record of how this protocol was fixed
* 19 October 2026, before any term was derived or any count retrieved: Sections 1, 3, 4, the date and
  document-type restrictions, and the run and outcome rules (history/PROTOCOL_v1.md; hashes in
  history/MANIFEST.txt). The term query was frozen (27 terms, R = 100; SHA-256
  51377ba9737a1b12a8a0b8878bb0c5a27f32e47ad78dd6255a59cf54fb06a7f6) and run with the date and
  document-type restrictions only: 528,412 records; validation 29/38. This is the original
  pre-specified configuration, evaluated before any validation result was known.
  Technical deviation: the first execution used a register file without OpenAlex identifiers, so no
  study could be matched; the matching step was re-executed with the same frozen query (run_step3.py).
* 20 October 2026, after that result: a language filter (English only) and the subject-field
  restriction of Section 2 were added (history/PROTOCOL_v2.md, addenda 1 and 2; hashes in
  history/MANIFEST_v2.txt). The field rule was written before any field data were retrieved. English
  only: 427,734 records, validation 27/38; English only and fields: 247,876 records, validation 27/38.
  The two validation studies lost (cui2025toward, goldsmith2025causal) have no language assigned in
  OpenAlex; their fields are kept. The fields of all 82 studies were then read (show_fields.py): all 36
  indexed validation studies have their primary topic in one of the fields kept.
* 20 October 2026: two variants that also replaced generic terms by phrases (every term with more than
  K = 50,000 or K = 10,000 OpenAlex title matches replaced by its candidate phrases) were run once each
  and not adopted, because they lost validation studies: 297,641 records, validation 24/38; 49,580
  records, validation 12/38.
* 20 October 2026: the language filter was dropped, because it removes works without an assigned
  language, including two included studies. The final configuration (Sections 2 and 5) was hashed
  before it was run (history/MANIFEST_final.txt), but after the fields of the validation studies were
  known. The field restriction was thus not specified before the first run. The final configuration
  is used for the reported filtered retrieval result, while the original pre-specified configuration
  and all intermediate runs are retained as part of the methodological audit trail.
* 20 October 2026, after the final run: editorial revision of this document (statement on known-item
  retrieval; Section 2 renamed "Retrieval restrictions"; Section 4 renamed "Term enrichment and
  threshold selection"; Sections 5, 6 and 9 clarified). No rule, restriction, query or result was
  changed. The version hashed before the final run is history/PROTOCOL_final_prerun.md.

## 9. Result  (run_final.py, 20 October 2026; run_output_final/)
The term query, the threshold and the date and document-type restrictions were fixed before any
validation result. The subject-field restriction was specified after the validation results of an
earlier configuration and the primary-topic fields of the validation studies had been inspected; the
result below is therefore not an independent validation of that restriction.

* Fields kept: Social Sciences (23 development studies); Economics, Econometrics and Finance (15);
  Computer Science (3); Physics and Astronomy (2); Decision Sciences (1).
* Records: 311,556. Without the subject-field restriction the query returned 528,902 records on the
  same day, so the restriction removed 217,346 records (41.1%). Records not tagged as English by
  OpenAlex (another language or none): 63,578 (20.4%); the language criterion is applied to them at
  screening.
* Validation set: 29/38 = 76.3% (95% CI 60.8-87.0%); indexed in OpenAlex: 29/36 = 80.6%
  (95% CI 65.0-90.2%). Development set: 42/44 = 95.5%.
* Validation studies indexed in OpenAlex but not retrieved (7): hrckova2025autonomation,
  liu2024exploring, smith2024unraveling, su2025emotionally, yang2025price, bradley2024place,
  roy2024unveiling.
* Validation studies not indexed in OpenAlex (2): cayuela2025influence, kumarsocial.

Interpretation
* The subject-field restriction did not remove any of the known included studies retrieved by the
  original query: the original pre-specified configuration retrieved the same validation studies
  (Section 8). The check does not show that the 217,346 records removed by the
  restriction contain no other relevant studies, and it cannot be used as evidence of the absence of
  selection bias.
