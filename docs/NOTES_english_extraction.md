# English edition extraction (completed 2026-10-29)

Goal: add title, English transliteration and English translation per sutra from
`TVA_BOK_0006660_Tolkappiyam_in_english.pdf` (Dr V. Murugan, *Tolkāppiyam in
English*, Institute of Asian Studies, 2001; 713-page scanned image PDF, no text
layer) to `tholkappiyam.csv`.

## Status

Done. `tholkappiyam.csv` has four added columns: `english_edition_no`, `title`,
`transliteration`, `translation`. All 1,603 sutras (prologue + 1,602) were
located in the OCR; 1,602 by a confident match of the transliteration, one
(1255) by a partial match. `data/work/reports/english_ocr.csv` is the review report
(one row per sutra: pages, similarity scores, printed number, warnings).

Remaining warnings (47), all reviewed:

- 38 `number read as …`: the printed sutra number was mis-OCR'd (a dropped
  leading digit or a stray glyph); the computed edition number is right.
- 1217: the book prints no translation (checked the page image).
- 103 and 1577 are printed as one sutra with the preceding one (edition
  numbers 102 and 1577 respectively); both CSV rows carry the shared
  translation.
- 441 and 1255 are printed as two sutras each (edition numbers `440-441` and
  `1255-1256`); the transliterations and translations are joined.
- 109: the book omits the opening line அவற்றுள்; the generated transliteration
  of that line is prepended.
- 65, 67, 1255: Tamil OCR similarity below 0.6 (only a cross-check; the Tamil
  text comes from the CSV, not from the OCR).
- 1057: the book breaks the sutra into 5 lines where the CSV has 6.

## Edition numbering

The book numbers sutras 1..1602 continuously (the prologue is unnumbered), but
its numbering differs from the CSV's by the merges and splits above:

| CSV rows      | book numbers        |
|---------------|---------------------|
| 1–102         | same                |
| 103           | 102 (with 102)      |
| 104–440       | CSV − 1             |
| 441           | 440–441 (two sutras)|
| 442–1254      | same                |
| 1255          | 1255–1256 (two)     |
| 1256–1576     | CSV + 1             |
| 1577          | 1577 (with 1576)    |
| 1578–1602     | same                |

`english_edition_no` records the book's number so cross-references in the
translations such as `[686]` (which use the book's numbering) can be followed.

## Pipeline

```
bash scripts/ocr_english.sh data/source/TVA_BOK_0006660_Tolkappiyam_in_english.pdf data/work/ocr data/work/tessdata [png_dir] [jobs]
python3 scripts/parse_english.py data/work/ocr   # rewrites data/final/tholkappiyam.csv, writes data/work/reports/english_ocr.csv
```

- `ocr_english.sh` renders every page at 300 dpi (pdftoppm, greyscale) and runs
  Tesseract twice per page, with the `Latin` script model (transliteration and
  English) and the `tam` model (to recognise the Tamil lines), `--psm 4`, TSV
  output. About 10 minutes on 22 cores. Outputs `p-NNN.lat.tsv` / `p-NNN.tam.tsv`
  (17 MB for the book) are kept in `data/work/ocr/`; the PNG renders (about 300 MB)
  are scratch. Existing outputs are skipped, so the script can be re-run.
- `data/work/tessdata/` holds `Latin.traineddata` and `tam.traineddata` from
  tessdata_best plus copies of Tesseract's `configs/` and `tessconfigs/`
  (needed, or the `tsv` config is not found when `TESSDATA_PREFIX` points
  there). The two models (107 MB) are git-ignored; fetch them from
  https://github.com/tesseract-ocr/tessdata_best (`script/Latin.traineddata`,
  `tam.traineddata`).
- `parse_tholkappiyam.py` regenerates `tholkappiyam.csv` from the Project
  Madurai HTML *without* the English columns; re-run `parse_english.py`
  afterwards.

## How parse_english.py works

1. Words from both TSVs are regrouped into lines by y-centre; junk lines
   (punctuation only, single letters), running headers (up to two lines above
   y = 1100 with a digit) and signature numbers at the foot are dropped. A line
   is Tamil when the Tamil model reads it with higher confidence than the Latin
   model (and ≥ 60, or the Latin reading is mostly upper-case garbage).
   `gap_before` marks paragraph breaks (> 1.45 × line pitch); `indent` is the
   offset from the page's text margin, estimated separately for the upper and
   lower half of the page so skewed scans do not shift it (≥ 35 px = example /
   footnote line, > 250 px = centred chapter title).
2. Every CSV sutra is transliterated with the Tamil Lexicon scheme the book uses
   (`transliterate()`), and that text is located in the OCR line stream by
   diacritic-insensitive similarity (`strip_marks()`, difflib with
   `autojunk=False`, which matters for sutras longer than 200 characters).
   Pass 1 walks the book once accepting matches ≥ 0.85; pass 2 searches between
   anchored neighbours with a 0.55 threshold; a layout-based fallback handles
   anything left. Variants tried: the sutra as printed, without a short opening
   line such as அவற்றுள், and a leading part only (for sutras the book splits).
3. The transliteration block is the anchor line plus the following lines (count
   chosen among the CSV line count, the paragraph, the first capital-initial
   line, and a penalised prefix). The Tamil block is the paragraph before the
   anchor (back to the gap or the numbered line; a stray non-Tamil line directly
   under Tamil lines belongs to it). Title = up to three Title-Case lines
   immediately before the Tamil block. Translation = lines after the
   transliteration up to the next sutra's title, minus Tamil, centred, indented
   and `e.g.` lines (everything from an `e.g.` line to the end of the segment is
   dropped). Transliteration lines that match the generated line ≥ 0.8 are
   replaced by the generated one (restores lost dot-below diacritics).
4. A sutra whose transliteration directly follows the previous one's with no
   Tamil between is "merged" (shares the previous edition number and
   translation); a sutra whose remaining transliteration lines appear later
   after their own Tamil block is "split" (edition `N-N+1`). The printed numbers
   are read only to cross-check the computed edition number.

Not extracted (by decision): the `e.g.` example blocks (mixed Tamil/Latin OCR
is poor). Bracketed cross-references like `[686]` keep the book's numbering.

Layout facts (300 dpi): text margin x ≈ 580–890 depending on the page; sutra
numbers ≈ 60–110 px left of it; chapter title pages centred (x > 1000);
first sutra on pdf page 27 (body page 3), last on pdf page 681 (body page 657);
prologue on pdf pages 23–24; glossary follows.
