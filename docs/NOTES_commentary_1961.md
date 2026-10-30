# 1961 commentary edition (completed 2026-10-29)

Source: `TVA_BOK_0044874_தொல்காப்பியம்_1961.pdf`, தொல்காப்பியம் with புலியூர்க்
கேசிகன் தெளிவுரை (1961), Tamil Virtual Academy scan, 437 pages, no text layer.
Pages 11–414 hold the prologue (11–12) and all sutras with commentary.

## Result

- `commentary_1961.csv`: one row per (book sutra, CSV row) pair, keyed by
  `csv_index` (0-based data row of `tholkappiyam.csv`). Columns:
  `edition_no_1961, heading_1961, title_1961, poem_1961, commentary_1961,
  pages_1961, poem_sim, ocr_agreement, warnings`.
- `merge_commentary.py` adds `edition_no_1961, title_1961, poem_1961,
  commentary_1961` to `tholkappiyam.csv`. All 1,603 rows are filled. It is
  safe to rerun.
- `data/work/reports/commentary_1961_review.csv` lists what to check by hand: 581
  sutra-level warnings and 3,502 substantial vision/OCR disagreements.

## Pipeline

```
bash scripts/ocr_1961.sh data/source/TVA_BOK_0044874_தொல்காப்பியம்_1961.pdf data/work/ocr_1961 data/work/tessdata data/work/scan_1961/png 11 414
# vision transcription: data/manual/transcribed_1961/p-NNN.txt, see INSTRUCTIONS.md there
python3 scripts/parse_commentary.py 11 414   # -> data/work/commentary_1961.csv + review report
python3 scripts/merge_commentary.py          # -> data/final/tholkappiyam.csv
```

1. `ocr_1961.sh` renders each page at the scan's native resolution
   (`pdftoppm -r 72`, 2450×3560), cuts it into 3 overlapping strips, and runs
   Tesseract `tam` for a cross-check. The renders (730 MB) are git-ignored scratch.
2. The text was read by Claude vision subagents, 10 pages each, following
   `data/manual/transcribed_1961/INSTRUCTIONS.md`: exact transcription of the 1961
   text, pre-reform ணா/னா/றா ligatures resolved by context, misprints kept and
   marked `⟨sic⟩`, illegible text marked `⟨?⟩`, words split by a page break
   ending in `-`. The transcriptions (1.8 MB) are the source of record. Fix
   errors there and rerun the two scripts.
3. `parse_commentary.py` cuts the marker stream into sutras and handles several
   cases: continuations across pages, poems interleaved with commentary,
   commentaries shared by consecutive sutras, and misprinted numbers corrected
   from their neighbours. It then aligns the book's sutras to the CSV with
   dynamic programming over the poem text, allowing 1:1, two-into-one and
   one-into-two steps.
4. The cross-check diffs each page's vision text with the Tesseract text at
   letter level. One- and two-letter differences are dropped as known
   Tesseract confusions (ந/க/ஈ, ஒ/ஓ, vowels read as Tamil numerals).

## Edition differences found

| 1961 book | CSV rows |
|---|---|
| 537 | 537 + 538 printed as one sutra |
| 598 | 599 + 600 printed as one sutra |
| 786, 787 | 788 split in two |
| 795, 796 | 796 split in two |
| 1157, 1158 | 1157 split in two |
| 1079 | title and number only, no poem printed |
| 1348 | different reading of 1347 ("இறுவாய் ஒப்பினஃ தியைபென மொழிப") |
| — | the book skips the number 1599, and its last sutra is 1604 |

## Quality

- Vision and Tesseract agree on 92.4% of letters overall: about 97% on clean
  pages and much lower on faded ones, where Tesseract is the weaker reader.
  Every disagreement checked by hand in the pilot was a Tesseract error.
- 1,117 `⟨?⟩` marks across 429 sutras. Heavily damaged stretches include
  pp. 125, 137–138, 175, 187, 223–225, 257, 261, 263, 313 and 319, where words
  are missing in the print itself and need another copy of the book.
- 104 `⟨sic⟩` marks for printed misprints. The first batches (pp. 21–240)
  were done before the `⟨sic⟩` rule, and two agents there silently restored a
  few dropped pulli dots. Those pages are less strictly diplomatic.
- Quoted example verses inside commentaries are sometimes one printed line per
  output line and sometimes joined into one paragraph, depending on the batch.
