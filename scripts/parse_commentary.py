#!/usr/bin/env python3
"""Parse the vision transcription of the 1961 Tholkappiyam commentary edition
(TVA_BOK_0044874) into one record per sutra, align each to data/final/tholkappiyam.csv,
and cross-check the text against the Tesseract OCR of the same pages.

Inputs
  data/manual/transcribed_1961/p-NNN.txt   line-marker transcription per page:
      @heading <text>   chapter / section heading
      @title <text>     sutra title
      @poem             poem lines follow
      @num <n>          printed sutra number
      @linenum <n>      line count in the prologue's margin (ignored)
      @commentary       commentary paragraphs follow, one per line
      @cont             text continued from the previous page follows
  data/work/ocr_1961/p-NNN.tam.txt       Tesseract reading of the same page

      @blank            page without book text

Usage: python3 scripts/parse_commentary.py [first_page] [last_page]
Writes data/work/commentary_1961.csv (one row per sutra, keyed by csv_index = 0-based
row of tholkappiyam.csv; merged into it by merge_commentary.py) and
data/work/reports/commentary_1961_review.csv (what to check by hand: unsure readings,
anchoring problems and substantial vision/OCR disagreements).
"""
import csv
import difflib
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TR_DIR = os.path.join(ROOT, 'data', 'manual', 'transcribed_1961')
OCR_DIR = os.path.join(ROOT, 'data', 'work', 'ocr_1961')
CSV_PATH = os.path.join(ROOT, 'data', 'final', 'tholkappiyam.csv')
PROLOGUE_PAGE = 11
LAST_PAGE = 414
OUT_CSV = os.path.join(ROOT, 'data', 'work', 'commentary_1961.csv')
REVIEW_CSV = os.path.join(ROOT, 'data', 'work', 'reports', 'commentary_1961_review.csv')
ANCHOR_WINDOW = 15     # CSV rows searched either side of the printed number

TAMIL_RUN = re.compile(r'[஀-௿]+')


def nfc(s):
    return unicodedata.normalize('NFC', s).replace('‌', '').replace('‍', '')


def skel(s):
    """Tamil letters only: drops spaces, punctuation and sandhi spacing."""
    return ''.join(TAMIL_RUN.findall(nfc(s)))


def words(s):
    """Comparison tokens: Tamil runs and digits, punctuation dropped."""
    return re.findall(r'[஀-௿]+|\d+', nfc(s))


def ratio(a, b):
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


# ---------------------------------------------------------------- transcription
def read_pages(first, last):
    pages = []
    for p in range(first, last + 1):
        path = os.path.join(TR_DIR, f'p-{p:03d}.txt')
        if not os.path.exists(path):
            print(f'warning: {path} missing')
            continue
        with open(path, encoding='utf-8') as f:
            pages.append((p, [nfc(l.rstrip('\n')) for l in f]))
    return pages


def new_sutra(page):
    return {'pages': [page], 'heading': [], 'title': '', 'poem': [], 'num': None,
            'commentary': [], 'unsure': 0}


def segment(pages):
    """Walk the marker stream and cut it into sutra records."""
    sutras = []
    cur = None
    mode = None
    headings = []
    join_next = False    # next text line continues the previous page's paragraph
    tagged = {}          # page -> [(text, sutra index or None)] in reading order

    def add(page, text):
        k = len(sutras) - 1 if sutras else None
        tagged.setdefault(page, []).append((text, k))
        if k is not None and page not in sutras[k]['pages']:
            sutras[k]['pages'].append(page)

    for page, lines in pages:
        for line in lines:
            if not line.strip():
                continue
            m = re.match(r'^@(\w+)\s*(.*)$', line)
            if m:
                tag, arg = m.group(1), m.group(2).strip()
                if tag == 'heading':
                    headings.append(arg)
                    tagged.setdefault(page, []).append((arg, None))
                    mode = None
                elif tag == 'title' or (tag == 'poem' and (cur is None or cur['num'] is not None)):
                    # a title, or a poem with no title after a finished sutra,
                    # opens the next sutra
                    if cur is None or cur['num'] is not None or cur['poem']:
                        cur = new_sutra(page)
                        sutras.append(cur)
                    cur['heading'], headings = headings, []
                    if tag == 'title':
                        cur['title'] = arg
                        add(page, arg)
                        mode = None
                    else:
                        mode = 'poem'
                elif tag == 'poem':
                    mode = 'poem'
                elif tag == 'num':
                    if cur is not None:
                        cur['num'] = int(re.sub(r'\D', '', arg) or 0)
                    mode = None
                elif tag in ('linenum', 'blank'):
                    pass
                elif tag == 'commentary':
                    mode = 'commentary'
                elif tag == 'cont':
                    join_next = True
                    # resume the section the previous page ended in
                    if mode is None:
                        mode = 'commentary' if cur is None or cur['num'] is not None else 'poem'
                else:
                    print(f'warning: page {page}: unknown marker {line!r}')
                continue
            if cur is None:          # text before any sutra on the first page
                cur = new_sutra(page)
                sutras.append(cur)
            add(page, line)
            target = cur['poem'] if mode == 'poem' else cur['commentary'] if mode == 'commentary' else None
            if join_next and target:
                # continued from the previous page: same paragraph / line
                prev = target[-1]
                target[-1] = prev[:-1] + line.strip() if prev.endswith('-') else prev + ' ' + line.strip()
                join_next = False
            elif target is not None:
                target.append(line.strip())
                join_next = False
            else:
                print(f'warning: page {page}: text outside a section: {line[:40]!r}')
            cur['unsure'] += line.count('⟨?⟩')
    return sutras, tagged


# ---------------------------------------------------------------- alignment
def load_csv():
    with open(CSV_PATH, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def anchor(sutra, rows, prologue, prev_idx):
    """Best matching CSV row (0-based index) near the row after the previous
    sutra's, and near the printed number (either may be off)."""
    target = skel(' '.join(sutra['poem']))
    if prologue:
        cands = [0]
    else:
        cands = set()
        for c in (prev_idx + 1, sutra['num'] or 0):
            cands.update(range(max(1, c - ANCHOR_WINDOW), min(len(rows), c + ANCHOR_WINDOW + 1)))
        # prefer the expected next row on ties
        cands = sorted(cands, key=lambda i: abs(i - prev_idx - 1))
    best = (None, 0.0)
    for i in cands:
        s = ratio(target, skel(rows[i]['பாடல்']))
        if s > best[1]:
            best = (i, s)
    return best


def align(sutras, rows, band=40):
    """Monotonic alignment of the book's sutras with the CSV rows.

    The 1961 edition divides the text differently in places: it prints two
    CSV sutras as one, or one CSV sutra as two.  Dynamic programming over
    the poem skeletons allows 1:1, 1:2 (book merges) and 2:1 (book splits)
    steps plus skips, and maximises the summed gain 2*similarity - 1.
    Returns {sutra index: (csv indices, similarity, kind)}."""
    B = [k for k, s in enumerate(sutras) if s['poem'] and not s.get('prologue')]
    bs = [skel(' '.join(sutras[k]['poem'])) for k in B]
    cs = [skel(r['பாடல்']) for r in rows]
    nb, nc = len(B), len(rows)
    cache = {}

    def sim(a, b):
        key = (a, b)
        if key not in cache:
            cache[key] = ratio(a, b)
        return cache[key]

    NEG = float('-inf')
    # dp[i][j]: best score aligning book items < i with csv rows < j (row 0 = prologue)
    dp = {(0, 1): (0.0, None)}
    for i in range(0, nb + 1):
        for j in range(max(1, i - band), min(nc, i + band) + 1):
            if (i, j) == (0, 1):
                continue
            best = (NEG, None)
            cands = []
            if i >= 1 and j >= 2:
                cands.append(((i - 1, j - 1), 'match', 2 * sim(bs[i - 1], cs[j - 1]) - 1))
            if i >= 1 and j >= 3:
                cands.append(((i - 1, j - 2), 'merge', 2 * sim(bs[i - 1], cs[j - 2] + cs[j - 1]) - 1))
            if i >= 2 and j >= 2:
                cands.append(((i - 2, j - 1), 'split', 2 * sim(bs[i - 2] + bs[i - 1], cs[j - 1]) - 1))
            if i >= 1:
                cands.append(((i - 1, j), 'skipb', -0.3))
            if j >= 2:
                cands.append(((i, j - 1), 'skipc', -0.3))
            for prev, kind, gain in cands:
                if prev in dp and dp[prev][0] + gain > best[0]:
                    best = (dp[prev][0] + gain, (prev, kind, gain))
            if best[1] is not None:
                dp[(i, j)] = best
    # trace back
    out = {}
    cur = (nb, nc)
    while cur in dp and dp[cur][1] is not None:
        prev, kind, gain = dp[cur][1]
        i, j = cur
        sim_ = (gain + 1) / 2
        if kind == 'match':
            out[B[i - 1]] = ([j - 1], sim_, kind)
        elif kind == 'merge':
            out[B[i - 1]] = ([j - 2, j - 1], sim_, kind)
        elif kind == 'split':
            out[B[i - 2]] = ([j - 1], sim_, kind)
            out[B[i - 1]] = ([j - 1], sim_, kind)
        cur = prev
    return out


# ---------------------------------------------------------------- OCR cross-check
def page_ocr_text(page):
    path = os.path.join(OCR_DIR, f'p-{page:03d}.tam.txt')
    if not os.path.exists(path):
        return ''
    with open(path, encoding='utf-8') as f:
        return nfc(f.read())


def cross_check(tagged, nsutras):
    """Compare each page's vision text with its OCR text.

    Agreement is measured on Tamil letters only (spacing and punctuation
    ignored, so OCR word splits do not count), per sutra.  Disagreements are
    reported as word spans of the vision text whose letters the OCR does not
    share, with the OCR letters at that place."""
    stats = {k: [0, 0] for k in range(nsutras)}      # matched letters, total letters
    diffs = []
    for page in sorted(tagged):
        chars, owner, wid = [], [], []                  # vision letters, sutra, word number
        vwords = []
        for text, k in tagged[page]:
            for w in words(text):
                for c in skel(w):
                    chars.append(c)
                    owner.append(k)
                    wid.append(len(vwords))
                vwords.append(w)
        ocr = skel(page_ocr_text(page))
        sm = difflib.SequenceMatcher(None, ''.join(chars), ocr, autojunk=False)
        ok = [False] * len(chars)
        for i, j, n in sm.get_matching_blocks():
            for x in range(i, i + n):
                ok[x] = True
        for x, k in enumerate(owner):
            if k is not None:
                stats[k][1] += 1
                stats[k][0] += ok[x]
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == 'equal' or i1 == i2 and j2 - j1 <= 2:
                continue     # pure OCR insertions of a stray letter or two are noise
            w1 = wid[i1] if i1 < len(wid) else len(vwords) - 1
            w2 = wid[i2 - 1] if i2 > i1 else w1
            k = owner[i1] if i1 < len(owner) else None
            diffs.append({'page': page, 'sutra_index': '' if k is None else k, 'op': op,
                          'vision_words': ' '.join(vwords[w1:w2 + 1]),
                          'vision_letters': ''.join(chars[i1:i2]),
                          'ocr_letters': ocr[j1:j2]})
    return stats, diffs


# ---------------------------------------------------------------- main
def main():
    first = int(sys.argv[1]) if len(sys.argv) > 1 else PROLOGUE_PAGE
    last = int(sys.argv[2]) if len(sys.argv) > 2 else LAST_PAGE
    pages = read_pages(first, last)
    sutras, tagged = segment(pages)
    # the book sometimes prints consecutive sutras one after another with a
    # single commentary for the group: give each of them that commentary
    for k in range(len(sutras) - 2, -1, -1):
        s, nxt = sutras[k], sutras[k + 1]
        if not s['commentary'] and s['num'] is not None and nxt['commentary'] \
                and s['pages'][-1] in nxt['pages']:
            s['commentary'] = list(nxt['commentary'])
            s['shared'] = nxt['num']
            if not nxt['title']:
                nxt['title'] = s['title']
    # misprinted sutra numbers: when the neighbours agree on the sequence,
    # the number in between is taken from it (the printed one is kept in
    # the warnings)
    for k in range(1, len(sutras)):
        s, prev = sutras[k], sutras[k - 1]
        nxt = sutras[k + 1] if k + 1 < len(sutras) else None
        if prev['num'] is None or s['num'] == prev['num'] + 1:
            continue
        if nxt is None or nxt['num'] == prev['num'] + 2:
            s['printed'] = s['num']
            s['num'] = prev['num'] + 1
    rows = load_csv()
    stats, diffs = cross_check(tagged, len(sutras))
    for s in sutras:
        s['prologue'] = s['pages'][0] == PROLOGUE_PAGE and s['num'] is None
    aligned = align(sutras, rows)
    out, review = [], []
    expected, prev_idx = 1, 0
    for k, s in enumerate(sutras):
        prologue = s['prologue']
        warn = []
        if prologue:
            idxs, sim = [0], ratio(skel(' '.join(s['poem'])), skel(rows[0]['பாடல்']))
        elif k in aligned:
            idxs, sim, kind = aligned[k]
            if kind == 'merge':
                warn.append(f'book prints csv rows {idxs[0]} and {idxs[1]} as one sutra')
            elif kind == 'split':
                warn.append(f'book prints csv row {idxs[0]} as two sutras')
        elif not s['poem']:
            idxs, sim = [prev_idx + 1], 0.0      # nothing to match: place by sequence
            warn.append('no poem printed; placed by sequence')
        else:
            idxs, sim = [], 0.0
            warn.append('not aligned to any csv row')
        if not prologue:
            if s['num'] is None:
                warn.append('no number')
            elif s['num'] != expected:
                warn.append(f'number {s["num"]}, expected {expected}')
            if s['num'] is not None:
                expected = s['num'] + 1
            if idxs and idxs[0] > prev_idx + 1:
                warn.append(f'csv rows {prev_idx + 1}..{idxs[0] - 1} not in the book')
        if idxs:
            prev_idx = idxs[-1]
        if sim < 0.85 and s['poem']:
            warn.append(f'poem match {sim:.2f}')
        if 'printed' in s:
            warn.append(f'printed number {s["printed"]} corrected to {s["num"]}')
        if s.get('shared'):
            warn.append(f'commentary printed jointly with {s["shared"]}')
        if not s['commentary']:
            warn.append('no commentary')
        if s['unsure']:
            warn.append(f'{s["unsure"]} unsure readings')
        matched, total = stats[k]
        agree = matched / total if total else 0.0
        if agree < 0.9 and total:
            warn.append(f'ocr agreement {agree:.2f}')
        for idx in (idxs or [None]):
          out.append({
            'csv_index': '' if idx is None else idx,
            'edition_no_1961': '' if s['num'] is None else s['num'],
            'heading_1961': ' | '.join(s['heading']),
            'title_1961': s['title'],
            'poem_1961': '\n'.join(s['poem']),
            'commentary_1961': '\n'.join(s['commentary']),
            'pages_1961': ','.join(map(str, s['pages'])),
            'poem_sim': f'{sim:.2f}',
            'ocr_agreement': f'{agree:.2f}',
            'warnings': '; '.join(warn),
        })
        if warn:
            review.append({'kind': 'sutra', 'page': s['pages'][0], 'edition_no_1961': s['num'] or '',
                           'csv_index': ';'.join(map(str, idxs)), 'detail': '; '.join(warn),
                           'vision': '', 'ocr': ''})
    first_row = {}
    for k, s in enumerate(sutras):
        a_ = aligned.get(k)
        if a_:
            first_row[k] = a_[0][0]
    # substantial disagreements only: one- or two-letter swaps are almost
    # always Tesseract confusions (ந/க/ஈ, ஒ/ஓ, Tamil numerals)
    for d in diffs:
        if max(len(d['vision_letters']), len(d['ocr_letters'])) <= 2:
            continue
        k = d['sutra_index']
        review.append({'kind': 'ocr-diff', 'page': d['page'],
                       'edition_no_1961': sutras[k]['num'] if k != '' and sutras[k]['num'] else '',
                       'csv_index': first_row.get(k, '') if k != '' else '',
                       'detail': d['op'], 'vision': d['vision_words'], 'ocr': d['ocr_letters']})
    with open(OUT_CSV, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    os.makedirs(os.path.dirname(REVIEW_CSV), exist_ok=True)
    with open(REVIEW_CSV, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['kind', 'page', 'edition_no_1961', 'csv_index', 'detail', 'vision', 'ocr'])
        w.writeheader()
        w.writerows(review)
    idxs = [r['csv_index'] for r in out if r['csv_index'] != '']
    dup = sorted({i for i in idxs if idxs.count(i) > 1})
    missing = sorted(set(range(len(rows))) - set(idxs))
    tot_m = sum(m for m, t in stats.values())
    tot_t = sum(t for m, t in stats.values())
    print(f'pages {first}..{last}: {len(pages)} transcribed; sutras: {len(out)}; '
          f'csv rows covered: {len(set(idxs))}/{len(rows)}; missing: {len(missing)} {missing[:20]}; '
          f'shared rows: {dup[:20]}')
    print(f'sutras with warnings: {sum(1 for r in out if r["warnings"])}; '
          f'vision/OCR letter agreement: {tot_m / max(1, tot_t):.1%}; '
          f'review items: {len(review)}')
    print(f'wrote {OUT_CSV} and {REVIEW_CSV}')


if __name__ == '__main__':
    main()
