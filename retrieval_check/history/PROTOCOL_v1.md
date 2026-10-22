# Validated verification search: protocol

Fixed on 19 October 2026, before any term was derived and before any count was retrieved.
Approach: objectively derived search strategy with a development and a validation set
(Hausner E, Waffenschmidt S, Kaiser T, Simon M. Routine development of objectively derived
search strategies. Systematic Reviews 2012;1:19. doi:10.1186/2046-4053-1-19).

## 1. Population and split  (split_corpus.py)
* Included studies published 2021-2026 (register column in_search_window = yes): 82.
* Strata: flow-diagram category (prisma_box). Within each stratum: bibkeys sorted, shuffled with one
  random.Random(20261019) (strata in sorted order); first ceil(n/2) -> development, rest -> validation.
* Result: 44 development, 38 validation.

## 2. Candidate terms  (derive_terms.py; reads development titles only)
* Titles from the register (surveybib_corrected.bib). Lower case; tokens = runs of letters/digits;
  a fixed stop-word list (in the script); digits-only tokens ignored.
* Plural variants are counted together (trailing -s / -ies removed for counting only; the query uses
  the form most frequent in the development titles).
* Candidates:
  (a) single words and two-word phrases (adjacent, no stop word) that occur in the titles of at least
      two development studies;
  (b) every keyword and quoted phrase of Table 2 (columns "Keywords and Synonyms" and
      "Representative Boolean Search String") that occurs in the title of at least one development study.

## 3. Specificity  (run_validation.py, steps 1-2)
* For every candidate: number of OpenAlex works whose title matches it, publication dates 2020-01-01 to
  2026-12-31, ineligible document types excluded (dissertation, dataset, paratext, editorial, letter,
  erratum, peer-review, retraction). N = number of works with the same filters and no title condition.
* Over-representation ratio r = (development titles containing the term / 44) / (OpenAlex count / N).
* Threshold R: the largest value in the grid {10, 20, 50, 100, 200, 500, 1000} for which the query
  (all candidates with r >= R) still matches at least 90% of the 44 development titles (offline title
  match). If no grid value reaches 90%, the smallest value (10) is used.
* A two-word phrase is dropped from the query when one of its words is itself a retained single word
  (the single word already covers it).

## 4. Query  (run_validation.py, step 2)
* One title query: all retained terms combined with OR; same date window and type exclusion as in 3;
  no language filter.
* The query file is frozen (SHA-256 recorded in protocol_log.json) before it is run.

## 5. Run and outcome  (run_validation.py, steps 3-4)
* The frozen query is run once in OpenAlex.
* Primary outcome: share of validation studies retrieved, with Wilson 95% confidence interval,
  reported over all 38 and over those indexed in OpenAlex.
* Secondary: share of development studies retrieved; number of records; list of validation studies
  not retrieved.
* No change to terms, threshold or query after the run. Whatever the result, it is reported.

## 6. Use of this protocol
* Sections 1-5 are implemented one-to-one by split_corpus.py, derive_terms.py and run_validation.py;
  MANIFEST.txt records the SHA-256 of every file before the run.
* Any deviation from this protocol (for example a technical fix needed to complete the run) is
  reported with the results, together with its reason.
* The protocol, the scripts, the frozen query and the outputs of the run are published with
  Supplementary Table S1, so that the result can be reproduced and checked against the protocol.
