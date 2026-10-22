# Dated protocol documents

These are the documents from which `../PROTOCOL.md` was assembled. They are kept unchanged so that the
SHA-256 hashes written before each run can be checked.

| File | Written | Content |
|---|---|---|
| `PROTOCOL_v1.md` | 19 October 2026, before any OpenAlex count | Split, candidate terms, specificity, threshold, date and document-type filters, run and outcome rules. Named `PROTOCOL.md` when its hash was written. |
| `MANIFEST.txt` | 19 October 2026, before the first run | SHA-256 of `PROTOCOL.md` (= `PROTOCOL_v1.md`), the split, the candidate terms and the scripts. |
| `PROTOCOL_v2.md` | 20 October 2026, after the first run | Language filter and the phrase-based variants (rejected); addendum 1 (language filter only); addendum 2 (language and subject-field filters: the final query). |
| `MANIFEST_v2.txt` | 20 October 2026, before each of these runs | SHA-256 of `PROTOCOL_v2.md` at each stage and of `run_v2.py`, `run_v2A.py`, `run_v2E.py`. |
| `PROTOCOL_final_prerun.md` | 20 October 2026, before the final run | `../PROTOCOL.md` as hashed before that run (language filter dropped; final configuration). After the run, Section 9 (results) was added and the wording was revised editorially (`../PROTOCOL.md`, Section 8, last item); no rule, restriction or query was changed. Named `PROTOCOL.md` when its hash was written. |
| `MANIFEST_final.txt` | 20 October 2026, before the final run | SHA-256 of `PROTOCOL.md` (= `PROTOCOL_final_prerun.md`), `run_final.py`, `run_validation.py`, `verify_corpus.py`, the split, the study IDs and the frozen term query. |

Check: `sha256sum PROTOCOL_v1.md PROTOCOL_v2.md PROTOCOL_final_prerun.md ../*.py ../split.csv ../candidates.csv ../corpus_ids.csv` and
compare with the manifests. The files were renamed or moved only; their content is unchanged.
