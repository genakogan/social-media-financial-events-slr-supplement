# Known-item retrieval check: protocol, version 2 (revision of 20 October 2026; variants B and D)

Version 1 (PROTOCOL.md) was run on 19 October 2026. Its frozen title query returned 528,412 records,
of which OpenAlex tags 427,734 as English and 100,678 as non-English (counts of 20 October 2026), and
about 90% of the records come from thirteen generic words (stock, news, causal, sentiment, opinion, ...).
The eligibility criteria of the review admit English-language publications only, and a query of this
breadth is of little use as a search strategy. Version 2 therefore narrows the version-1 query.

This revision was written after the result of version 1 was known. Both results are reported.
Version 2 only narrows version 1: every record and every included study it returns is also returned by
version 1, so the revision cannot increase the number of included studies retrieved.

## Unchanged from version 1
Population and split (split.csv, seed 20261019), candidate terms (candidates.csv), the OpenAlex title
counts and over-representation ratios of the version-1 run (run_output/term_counts.csv), N, R = 100,
publication dates 2020-2026, exclusion of ineligible document types, title search, one run, reporting
of all 38 and of the indexed validation studies with Wilson 95% confidence intervals.

## Changes
1. Language: filter `language:en` (eligibility criterion "English-language publications"). OpenAlex
   assigns the language automatically; English publications tagged otherwise are lost (known case among
   the included studies: cui2025toward).
2. Specificity cap K: every version-1 term whose OpenAlex title count exceeds K is replaced by the
   candidate phrases that contain it, have a title count <= K and a ratio >= R; if there is none, the
   term is removed. Two variants are pre-specified (chosen by the author on 20 October 2026, before
   either was run):
   * Variant B: K is the smallest value in the grid {5,000; 10,000; 20,000; 50,000; 100,000} for which
     the query still matches at least 90% of the 44 development titles (offline title match, as in
     version 1). On the development titles this gives K = 50,000 (match 90.9%).
   * Variant D: K = 10,000 (development titles matched: 63.6%).
   K = 100,000 would reproduce version 1.
3. Both queries are frozen (SHA-256 in protocol_log_v2.json) before either is run; each is run once,
   and both results are reported together with version 1.

## Addendum (20 October 2026, after variants B and D were run): variant A
Variant A is the version-1 query unchanged, with only the language filter `language:en` added (change 1
above, without change 2). It was requested by the author after the results of B and D were known; it
involves no choice of terms or thresholds. It is run once and reported together with version 1, B and D.

## Addendum 2 (20 October 2026, after variant A was run): variant E
The version-1 query searches titles in all subject areas of OpenAlex, so records from unrelated fields
(e.g. chemistry, medicine) are counted. Variant E is variant A (version-1 query + language:en) with a
subject-field filter. Fields are the OpenAlex fields of each work's primary topic (OpenAlex topic
classification, assigned automatically). Rule, fixed before any field data were retrieved: keep every
field that is the primary-topic field of at least one of the 44 development studies. Only the
development studies are used to choose the fields; the fields of the validation studies are retrieved
after the run, to report the studies not retrieved. Works without a primary topic are excluded by the
filter, as works without a language are excluded by language:en. The records of variant A by field are
reported. Variant E was requested by the author after the result of variant A was known; it is run once
and reported together with version 1 and variants A, B and D.

Implemented by run_v2.py (variants B and D), run_v2A.py (variant A) and run_v2E.py (variant E).
