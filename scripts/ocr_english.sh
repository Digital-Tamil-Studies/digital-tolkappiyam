#!/usr/bin/env bash
# Render the scanned "Tolkāppiyam in English" PDF to 300 dpi greyscale PNGs and
# OCR every page twice with Tesseract (Latin script model for the
# transliteration/English text, Tamil model for the sutra lines), writing TSVs
# that parse_english.py reads.
#
# Usage: bash scripts/ocr_english.sh <pdf> <ocr_out_dir> <tessdata_dir> [png_dir] [jobs]
#   pdf          data/source/TVA_BOK_0006660_Tolkappiyam_in_english.pdf
#   ocr_out_dir  where p-NNN.lat.tsv / p-NNN.tam.tsv go (e.g. data/work/ocr)
#   tessdata_dir folder holding Latin.traineddata, tam.traineddata and copies of
#                tesseract's configs/ and tessconfigs/ (needed for the tsv config)
#   png_dir      scratch folder for the page renders (default: <ocr_out_dir>/../png)
#   jobs         parallel workers (default: nproc)
#
# Existing outputs are skipped, so the script can be re-run to fill gaps.
set -euo pipefail

PDF=${1:?pdf}
OUT=${2:?ocr output dir}
TESSDATA=${3:?tessdata dir}
PNG=${4:-$(dirname "$OUT")/png}
JOBS=${5:-$(nproc)}

mkdir -p "$OUT" "$PNG"
PAGES=$(pdfinfo "$PDF" | awk '/^Pages:/ {print $2}')
echo "pages: $PAGES  jobs: $JOBS  png: $PNG  out: $OUT"

export PDF OUT TESSDATA PNG

render_one() {
    local p=$1 tag
    tag=$(printf 'p-%03d' "$p")
    [ -s "$PNG/$tag.png" ] && return 0
    pdftoppm -r 300 -gray -png -f "$p" -l "$p" -singlefile "$PDF" "$PNG/$tag"
}

ocr_one() {
    local p=$1 tag
    tag=$(printf 'p-%03d' "$p")
    if [ ! -s "$OUT/$tag.lat.tsv" ]; then
        TESSDATA_PREFIX="$TESSDATA" OMP_THREAD_LIMIT=1 \
            tesseract "$PNG/$tag.png" "$OUT/$tag.lat" -l Latin --psm 4 tsv >/dev/null 2>&1
    fi
    if [ ! -s "$OUT/$tag.tam.tsv" ]; then
        TESSDATA_PREFIX="$TESSDATA" OMP_THREAD_LIMIT=1 \
            tesseract "$PNG/$tag.png" "$OUT/$tag.tam" -l tam --psm 4 tsv >/dev/null 2>&1
    fi
}

export -f render_one ocr_one

echo "rendering..."
seq 1 "$PAGES" | xargs -P "$JOBS" -I{} bash -c 'render_one {}'
echo "ocr..."
seq 1 "$PAGES" | xargs -P "$JOBS" -I{} bash -c 'ocr_one {}'

echo "done: $(ls "$OUT"/*.lat.tsv | wc -l) lat, $(ls "$OUT"/*.tam.tsv | wc -l) tam"
