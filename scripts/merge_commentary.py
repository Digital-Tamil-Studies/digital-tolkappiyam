#!/usr/bin/env python3
"""Append the 1961 commentary edition's columns to tholkappiyam.csv.

    python3 scripts/merge_commentary.py [commentary_1961.csv] [tholkappiyam.csv]

Defaults: data/work/commentary_1961.csv and data/final/tholkappiyam.csv.

Reads commentary_1961.csv (written by parse_commentary.py, one row per sutra
of the 1961 book, keyed by csv_index = 0-based data row of tholkappiyam.csv)
and adds or replaces these columns in tholkappiyam.csv:

    edition_no_1961  title_1961  poem_1961  commentary_1961

Rows of the main CSV with no 1961 entry get empty cells.  If the 1961 book
prints one CSV sutra as two numbered sutras, both map to the same row and are
joined (numbers as "N-M", texts separated by a blank line).  Running it again
is safe: existing 1961 columns are replaced, not duplicated.
"""
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLS = ['edition_no_1961', 'title_1961', 'poem_1961', 'commentary_1961']


def main(argv):
    src = argv[0] if argv else os.path.join(ROOT, 'data', 'work', 'commentary_1961.csv')
    dst = argv[1] if len(argv) > 1 else os.path.join(ROOT, 'data', 'final', 'tholkappiyam.csv')
    merged = {}
    with open(src, encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f):
            if r['csv_index'] == '':
                continue
            i = int(r['csv_index'])
            if i in merged:
                m = merged[i]
                m['edition_no_1961'] = f"{m['edition_no_1961']}-{r['edition_no_1961']}"
                for c in ('title_1961', 'poem_1961', 'commentary_1961'):
                    m[c] = '\n\n'.join(x for x in (m[c], r[c]) if x)
            else:
                merged[i] = {c: r[c] for c in COLS}
    with open(dst, encoding='utf-8-sig', newline='') as f:
        rd = csv.DictReader(f)
        rows = list(rd)
        fields = [c for c in rd.fieldnames if c not in COLS] + COLS
    for i, row in enumerate(rows):
        row.update(merged.get(i, {c: '' for c in COLS}))
    with open(dst, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    filled = sum(1 for i in range(len(rows)) if i in merged)
    print(f'{dst}: {filled}/{len(rows)} rows have 1961 commentary columns')


if __name__ == '__main__':
    main(sys.argv[1:])
