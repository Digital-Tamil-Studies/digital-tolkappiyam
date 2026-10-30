#!/usr/bin/env bash
# Render the scanned 1961 Tholkappiyam commentary edition and OCR it with the
# Tesseract Tamil model.  Also cuts each page into horizontal strips for
# vision transcription (dense commentary stays legible when a strip is read
# instead of a whole downscaled page).
#
# Usage: bash scripts/ocr_1961.sh <pdf> <ocr_out_dir> <tessdata_dir> <png_dir> [first] [last] [jobs]
#   pdf          data/source/TVA_BOK_0044874_தொல்காப்பியம்_1961.pdf
#   ocr_out_dir  p-NNN.tam.tsv / p-NNN.tam.txt go here (e.g. data/work/ocr_1961)
#   tessdata_dir folder with tam.traineddata + configs/ (e.g. data/work/tessdata)
#   png_dir      page renders p-NNN.png and strips p-NNN-s1..s3.png (e.g. data/work/scan_1961/png)
#   first last   page range (default: whole book)
#   jobs         parallel workers (default: nproc)
#
# Pages are rendered at 72 dpi, which is the scan's native resolution
# (about 2450 x 3560 px); higher dpi only upscales.  Existing outputs are skipped.
set -euo pipefail

PDF=${1:?pdf}
OUT=${2:?ocr output dir}
TESSDATA=${3:?tessdata dir}
PNG=${4:?png dir}
PAGES=$(pdfinfo "$PDF" | awk '/^Pages:/ {print $2}')
FIRST=${5:-1}
LAST=${6:-$PAGES}
JOBS=${7:-$(nproc)}
STRIPS=3
OVERLAP=80

mkdir -p "$OUT" "$PNG"
echo "pages $FIRST..$LAST  jobs: $JOBS  png: $PNG  out: $OUT"
export PDF OUT TESSDATA PNG STRIPS OVERLAP

one_page() {
    local p=$1 tag h w step i y0 y1
    tag=$(printf 'p-%03d' "$p")
    [ -s "$PNG/$tag.png" ] || pdftoppm -r 72 -gray -png -f "$p" -l "$p" -singlefile "$PDF" "$PNG/$tag"
    if [ ! -s "$PNG/$tag-s$STRIPS.png" ]; then
        read -r w h < <(identify -format '%w %h' "$PNG/$tag.png")
        step=$(( h / STRIPS ))
        for i in $(seq 1 "$STRIPS"); do
            y0=$(( (i - 1) * step - OVERLAP )); [ "$y0" -lt 0 ] && y0=0
            y1=$(( i * step + OVERLAP )); [ "$y1" -gt "$h" ] && y1=$h
            convert "$PNG/$tag.png" -crop "${w}x$(( y1 - y0 ))+0+${y0}" +repage "$PNG/$tag-s$i.png"
        done
    fi
    if [ ! -s "$OUT/$tag.tam.tsv" ]; then
        TESSDATA_PREFIX="$TESSDATA" OMP_THREAD_LIMIT=1 \
            tesseract "$PNG/$tag.png" "$OUT/$tag.tam" -l tam --psm 4 tsv txt >/dev/null 2>&1
    fi
}
export -f one_page

seq "$FIRST" "$LAST" | xargs -P "$JOBS" -I{} bash -c 'one_page {}'
echo "done: $(ls "$OUT"/*.tam.tsv | wc -l) pages OCR'd"
