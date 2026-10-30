#!/usr/bin/env python3
"""Extract title / transliteration / English translation per sutra from the OCR
of "Tolkāppiyam in English" (Dr V. Murugan, Institute of Asian Studies, 2001;
Tamil Virtual Academy scan TVA_BOK_0006660) and add them to tholkappiyam.csv.

Input: a directory of Tesseract TSV files produced by ocr_english.sh:
    p-NNN.lat.tsv   Latin-script model (transliteration + English text)
    p-NNN.tam.tsv   Tamil model (used to recognise the Tamil lines)

Each sutra in the book is laid out as: [bold title]  number + Tamil text,
transliteration, English translation, optional "e.g." examples.  The book
numbers sutras 1..1602 continuously (payiram is unnumbered); our CSV global
id g == book number + 1.

Method: the Tamil text of every CSV sutra is transliterated with the same
Tamil Lexicon scheme the book uses, and that transliteration is located in
the OCR line stream (anchor).  The Tamil block is the paragraph before the
anchor, the title the bold Title-Case line(s) before that, and the
translation the lines after the transliteration up to the next sutra.  The
printed sutra numbers are only used to cross-check.

Usage: python3 scripts/parse_english.py <ocr_dir> [tholkappiyam.csv] [english_ocr.csv]
  ocr_dir is data/work/ocr; the defaults are data/final/tholkappiyam.csv and
  data/work/reports/english_ocr.csv.
Writes the CSV back with four added columns and a review report.
"""
import csv
import difflib
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIRST_PAGE = 27        # pdf page of body page 3 (first sutra)
LAST_PAGE = 681        # pdf page of body page 657 (last sutra)
PROLOGUE_PAGES = (23, 24)
HEADER_Y = 1100        # lines above this y (300 dpi) are running headers
NUM_COL_X = 600        # sutra numbers sit left of this x
CENTRED = 250          # indent (px past the page's text margin) of centred chapter titles
BOTTOM_Y = 3000        # standalone numbers below this are signature marks
INDENT = 35            # extra indent (px) that marks example/note lines

ANCHOR_STRONG = 0.85   # pass 1: full-text similarity for a confident anchor
ANCHOR_WEAK = 0.55     # pass 2: between two confident anchors
FIRST_LINE_MIN = 0.5   # prefilter on the first transliteration line
WINDOW = 400           # lines searched ahead of the cursor in pass 1

TAMIL = re.compile(r'[஀-௿]')
NUM_RE = re.compile(r'^(\d{1,4})[.,:;]?$')
NUMISH_RE = re.compile(r'^[\dlIoOS|]{1,4}[a-zA-Z]?[.,:;]?$')
EG_RE = re.compile(r'^(e\.?g|c\.?g|6\.?8|e\.?8|c\.?8|c\.?p|c\.?s|eg|cg)[.,:]?$', re.I)
STOP = {'a', 'an', 'and', 'as', 'at', 'by', 'for', 'in', 'of', 'on', 'or',
        'the', 'to', 'vs', 'vis-a-vis', 'with', 'its', 'their', 'into',
        'from', 'but', 'not', 'is', 'are', 'be', 'that', 'which', 'when'}

NEW_COLS = ['english_edition_no', 'title', 'transliteration', 'translation']

# ---------------------------------------------------------------- transliteration
VOWELS = {'அ': 'a', 'ஆ': 'ā', 'இ': 'i', 'ஈ': 'ī', 'உ': 'u', 'ஊ': 'ū',
          'எ': 'e', 'ஏ': 'ē', 'ஐ': 'ai', 'ஒ': 'o', 'ஓ': 'ō', 'ஔ': 'au', 'ஃ': 'ḵ'}
CONS = {'க': 'k', 'ங': 'ṅ', 'ச': 'c', 'ஞ': 'ñ', 'ட': 'ṭ', 'ண': 'ṇ', 'த': 't',
        'ந': 'n', 'ப': 'p', 'ம': 'm', 'ய': 'y', 'ர': 'r', 'ல': 'l', 'வ': 'v',
        'ழ': 'ḻ', 'ள': 'ḷ', 'ற': 'ṟ', 'ன': 'ṉ', 'ஜ': 'j', 'ஷ': 'ṣ', 'ஸ': 's',
        'ஹ': 'h'}
SIGNS = {'ா': 'ā', 'ி': 'i', 'ீ': 'ī', 'ு': 'u', 'ூ': 'ū', 'ெ': 'e', 'ே': 'ē',
         'ை': 'ai', 'ொ': 'o', 'ோ': 'ō', 'ௌ': 'au'}


def transliterate(text):
    """Tamil script -> Tamil Lexicon romanisation (as used in the book)."""
    out = []
    i = 0
    text = unicodedata.normalize('NFC', text)
    while i < len(text):
        c = text[i]
        if c in CONS:
            out.append(CONS[c])
            nxt = text[i + 1] if i + 1 < len(text) else ''
            if nxt == '்':
                i += 2
                continue
            if nxt in SIGNS:
                out.append(SIGNS[nxt])
                i += 2
                continue
            out.append('a')
        elif c in VOWELS:
            out.append(VOWELS[c])
        elif c == '‌':
            pass
        else:
            out.append(c)
        i += 1
    return ''.join(out)


def strip_marks(s):
    """Lower-case ASCII skeleton for diacritic-insensitive comparison."""
    s = unicodedata.normalize('NFD', s.lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.translate(str.maketrans({'ı': 'i', 'ł': 'l', 'ß': 'ss'}))
    return re.sub(r'[^a-z]', '', s)


def ratio(a, b):
    if not a or not b:
        return 0.0
    # autojunk must be off: with it, every common letter of a 200+ character
    # string is treated as junk and long sutras score near zero
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def fix_ocr_latin(s):
    return s.replace('ı', 'i').replace('ſ', 's')


def ws(s):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', s)).strip()


# ---------------------------------------------------------------- OCR lines
def read_words(path):
    words = []
    if not os.path.exists(path):
        return words
    with open(path, encoding='utf-8') as f:
        rd = csv.reader(f, delimiter='\t', quoting=csv.QUOTE_NONE)
        next(rd, None)
        for row in rd:
            if len(row) < 12 or row[0] != '5' or not row[11].strip():
                continue
            left, top, width, height = map(int, row[6:10])
            words.append({'x': left, 'y': top, 'w': width, 'h': height,
                          'cy': top + height / 2, 'conf': float(row[10]),
                          'text': row[11]})
    return words


def group_lines(words):
    """Cluster words into lines by vertical centre regardless of OCR blocks."""
    words = sorted(words, key=lambda w: w['cy'])
    lines = []
    for w in words:
        tol = max(10, 0.55 * w['h'])
        best = None
        for ln in lines[-6:]:
            if abs(ln['cy'] - w['cy']) <= tol:
                best = ln
                break
        if best is None:
            lines.append({'cy': w['cy'], 'words': [w]})
        else:
            best['words'].append(w)
            n = len(best['words'])
            best['cy'] = (best['cy'] * (n - 1) + w['cy']) / n
    out = []
    for ln in lines:
        wsd = sorted(ln['words'], key=lambda w: w['x'])
        out.append({
            'cy': ln['cy'], 'x': wsd[0]['x'],
            'top': min(w['y'] for w in wsd),
            'bottom': max(w['y'] + w['h'] for w in wsd),
            'text': ws(' '.join(w['text'] for w in wsd)),
            'words': wsd,
        })
    out.sort(key=lambda l: l['cy'])
    return out


def mean_conf(line):
    cs = [w['conf'] for w in line['words']]
    return sum(cs) / len(cs) if cs else 0.0


def tamil_share(text):
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if TAMIL.match(c)) / len(letters)


def upper_share(text):
    letters = [c for c in text if c.isascii() and c.isalpha()]
    if not letters:
        return 1.0
    return sum(1 for c in letters if c.isupper()) / len(letters)


def number_token(line):
    """Sutra number at the start of the line: (value or None, numish flag).

    value < 0 marks a doubtful reading (letters standing in for digits)."""
    w = line['words'][0]
    if w['x'] >= NUM_COL_X:
        return None, False
    m = NUM_RE.match(w['text'])
    if m:
        return int(m.group(1)), True
    if NUMISH_RE.match(w['text']) and len(line['words']) > 1:
        fixed = re.sub(r'[a-zA-Z.,:;]+$', '', w['text']).translate(str.maketrans('lIoOS|', '110051'))
        if fixed.isdigit():
            return -int(fixed), True
        return None, True
    return None, False


def mode_bucket(values):
    buckets = {}
    for v in values:
        b = v // 10
        buckets[b] = buckets.get(b, 0) + 1
    return min(buckets, key=lambda b: (-buckets[b], b)) * 10 if buckets else None


def page_lines(ocr_dir, page):
    """Cleaned, classified lines of one page.

    A line is Tamil when the Tamil model reads it better than the Latin model
    (each model produces low-confidence garbage on the other script)."""
    lat = group_lines(read_words(os.path.join(ocr_dir, f'p-{page:03d}.lat.tsv')))
    tam = group_lines(read_words(os.path.join(ocr_dir, f'p-{page:03d}.tam.tsv')))
    tam_rows = [(l['top'], l['bottom'], l['text'], mean_conf(l)) for l in tam]
    lines = []
    for l in lat:
        if not l['text'] or not re.search(r'[^\W_]', l['text']) or re.fullmatch(r'[^\W\d_][.,]?', l['text']):
            continue  # empty, punctuation-only or single-letter junk such as a stray '.' or 'l'
        tam_text, tam_conf = None, -1.0
        for top, bottom, text, conf in tam_rows:
            if top - 8 <= l['cy'] <= bottom + 8 and conf > tam_conf:
                tam_text, tam_conf = text, conf
        lat_conf = mean_conf(l)
        l['lat_conf'] = lat_conf
        l['tam_raw'] = tam_text or ''
        l['tamil'] = bool(tam_text) and tamil_share(tam_text) >= 0.5 and tam_conf > lat_conf \
            and (tam_conf >= 60 or upper_share(l['text']) >= 0.5)
        l['tam_text'] = tam_text if l['tamil'] else None
        l['page'] = page
        l['num'], l['numish'] = number_token(l)
        # text x: skip the number column
        l['tx'] = l['words'][1]['x'] if l['numish'] and len(l['words']) > 1 else l['x']
        l['eg'] = bool(EG_RE.match(l['words'][0]['text'])) or \
            (len(l['words']) > 1 and EG_RE.match((l['words'][0]['text'] + l['words'][1]['text'])) is not None
             and len(l['words'][0]['text']) <= 2)
        l['skel'] = strip_marks(l['text'])
        lines.append(l)
    # running header: up to two lines near the top (chapter name and page
    # number, sometimes read as separate lines), one of them carrying a digit
    head = [l for l in lines[:2] if l['cy'] < HEADER_Y]
    if head and any(re.search(r'\d', l['text']) and (len(l['text'].split()) <= 8 or 'ENGLISH' in l['text'].upper())
                    for l in head):
        lines = lines[len(head):]
    # signature marks / stray numbers at the bottom
    while lines and lines[-1]['cy'] > BOTTOM_Y and re.fullmatch(r'[\d.,]+', lines[-1]['text']):
        lines.pop()
    # paragraph gaps
    pitches = [b['cy'] - a['cy'] for a, b in zip(lines, lines[1:]) if 0 < b['cy'] - a['cy'] < 120]
    pitch = sorted(pitches)[len(pitches) // 2] if pitches else 55
    for a, b in zip(lines, lines[1:]):
        b['gap_before'] = (b['cy'] - a['cy']) > 1.45 * pitch
    if lines:
        lines[0]['gap_before'] = True
        lines[0]['page_top'] = True
    # base indent of body text: the modal x in the upper and lower half of the
    # page, interpolated, so a skewed scan does not shift the indents
    body = list(lines)
    base_all = mode_bucket([l['tx'] for l in body])
    if base_all is None:
        base_all = 650
    if len(body) >= 8:
        mid = sorted(l['cy'] for l in body)[len(body) // 2]
        top = [l for l in body if l['cy'] <= mid]
        bot = [l for l in body if l['cy'] > mid]
        bt, bb = mode_bucket([l['tx'] for l in top]), mode_bucket([l['tx'] for l in bot])
        yt = sum(l['cy'] for l in top) / len(top)
        yb = sum(l['cy'] for l in bot) / len(bot)
        if abs(bt - bb) > 60 or yb - yt < 200:   # not a skew: fall back to the mode
            bt = bb = base_all
    else:
        bt = bb = base_all
        yt, yb = 0, 1
    for l in lines:
        base = bt + (bb - bt) * (l['cy'] - yt) / (yb - yt) if yb != yt else bt
        l['indent'] = l['tx'] - base
        l['centred'] = l['indent'] > CENTRED
    return lines


def clean_title(t):
    t = re.sub(r"(?<=[a-z])[!\]](?=[a-z/ ]|$)", 'l', t)   # Consonanta! -> Consonantal
    t = re.sub(r"^[\-\s`'|]+|[\s`'|\-]+$", '', t)
    return ws(t)


def heading_like(line):
    t = line['text']
    if line['tamil'] or line['centred'] or line['eg'] or line['indent'] >= INDENT:
        return False
    if re.search(r'[.;:,]$', t) or len(t.split()) > 12 or re.search(r'\d', t):
        return False
    words = re.findall(r"[A-Za-z][A-Za-z'\-]*", t)
    if not words or tamil_share(t) > 0:
        return False
    content = [w for w in words if w.lower() not in STOP]
    if not content or not words[0][0].isupper():
        return False
    return all(w[0].isupper() for w in content)


# ---------------------------------------------------------------- alignment
def collect_lines(ocr_dir, first, last):
    out = []
    for page in range(first, last + 1):
        out.extend(page_lines(ocr_dir, page))
    return out


def candidate_line(l):
    """A line that could be the start of a transliteration block.  Lines the
    classifier took for Tamil are allowed: a genuine Tamil line read by the
    Latin model is garbage and never matches a transliteration."""
    return not l['centred'] and not l['eg'] and l['skel']


def variants(gen):
    """(offset, first-line skeleton, full skeleton, line count) to try for a
    sutra: as printed, and without a short opening line such as avaṟṟuḷ,
    which the book sometimes leaves out."""
    out = [(0, strip_marks(gen[0]), strip_marks(''.join(gen)), len(gen), gen)]
    if len(gen) > 1 and len(strip_marks(gen[0])) <= 12:
        out.append((1, strip_marks(gen[1]), strip_marks(''.join(gen[1:])), len(gen) - 1, gen[1:]))
    return out


def block_score(lines, i, gen_skel, n, gen_lines=None):
    """Best similarity of gen_skel with the n-1, n or n+1 lines from i.

    With gen_lines given, a leading part of the sutra is also tried: the
    book sometimes prints one CSV sutra as two numbered sutras, so only its
    first lines follow the anchor (slightly penalised, needs a paragraph gap
    after the part and at least 20 % of the text)."""
    best = 0.0
    for k in (n, n - 1, n + 1):
        if k < 1 or i + k > len(lines):
            continue
        skel = ''.join(l['skel'] for l in lines[i:i + k])
        if abs(len(skel) - len(gen_skel)) > 0.5 * max(len(skel), len(gen_skel)):
            continue
        best = max(best, ratio(skel, gen_skel))
    if gen_lines and n > 1:
        for k in range(1, n - 1 if n > 2 else n):
            if i + k >= len(lines) or not lines[i + k].get('gap_before'):
                continue
            part = strip_marks(''.join(gen_lines[:k]))
            if len(part) < 15 or len(part) < 0.2 * len(gen_skel):
                continue
            skel = ''.join(l['skel'] for l in lines[i:i + k])
            best = max(best, 0.98 * ratio(skel, part))
    return best


def find_anchors(lines, gens):
    """Map book number -> index of the first transliteration line.

    gens: book number -> list of generated transliteration lines.  Pass 1
    walks the text once with a cursor accepting confident matches; pass 2
    looks for the rest between their already anchored neighbours."""
    anchors, scores, offs = {}, {}, {}
    numbers = sorted(gens)
    cursor, fails = 0, 0

    def best_at(i, vars_, first_min):
        best = (0.0, 0)
        for off, first, full, n, gl in vars_:
            if ratio(lines[i]['skel'], first) < first_min:
                continue
            s = block_score(lines, i, full, n, gl)
            if s > best[0]:
                best = (s, off)
        return best

    for no in numbers:
        vars_ = variants(gens[no])
        hi = min(len(lines), cursor + WINDOW + 100 * fails)
        hit = None
        for i in range(cursor, hi):
            if not candidate_line(lines[i]):
                continue
            s, off = best_at(i, vars_, FIRST_LINE_MIN)
            if s >= ANCHOR_STRONG:
                hit = (i, s, off)
                break
        if hit:
            anchors[no], scores[no], offs[no] = hit
            cursor, fails = hit[0] + 1, 0
        else:
            fails += 1
    # pass 2: fill gaps between anchored neighbours
    for no in numbers:
        if no in anchors:
            continue
        prev = max((a for a in anchors if a < no), default=None)
        nxt = min((a for a in anchors if a > no), default=None)
        lo = anchors[prev] + 1 if prev is not None else 0
        hi = anchors[nxt] if nxt is not None else len(lines)
        vars_ = variants(gens[no])
        best = (None, ANCHOR_WEAK, 0)
        for i in range(lo, hi):
            if not candidate_line(lines[i]):
                continue
            s, off = best_at(i, vars_, 0.4)
            if s > best[1]:
                best = (i, s, off)
        if best[0] is not None:
            anchors[no], scores[no], offs[no] = best
    return anchors, scores, offs


# ---------------------------------------------------------------- segmentation
def translit_end(lines, i, gen, limit):
    """Index after the transliteration block starting at i."""
    n = len(gen)
    gen_skel = strip_marks(''.join(gen))
    cands = {n}
    a = i + 1
    while a < limit and not lines[a]['gap_before'] and not lines[a]['tamil']:
        a += 1
    cands.add(a - i)
    b = i
    while b < limit and not lines[b]['tamil'] and \
            not next((c for c in lines[b]['text'] if c.isalpha()), 'a').isupper():
        b += 1
    if b > i:
        cands.add(b - i)
    best, best_score = n, -1.0
    for k in sorted(cands):
        if k < 1 or i + k > limit:
            continue
        skel = ''.join(l['skel'] for l in lines[i:i + k])
        s = ratio(skel, gen_skel)
        if s > best_score:
            best, best_score = k, s
    # a leading part only (the book printed the rest as a separate sutra):
    # accepted, with a penalty, when a paragraph gap or an English line
    # with a capital initial follows and the part matches the gen prefix
    for k in range(1, n):
        if i + k >= limit:
            break
        nxt = lines[i + k]
        if not (nxt.get('gap_before') or nxt['text'][:1].isupper()):
            continue
        skel = ''.join(l['skel'] for l in lines[i:i + k])
        s = 0.9 * ratio(skel, strip_marks(''.join(gen[:k])))
        if s > best_score:
            best, best_score = k, s
    return i + best, best_score


def tamil_start(lines, anchor, floor):
    """Index of the first Tamil line of the sutra whose transliteration starts
    at anchor: walk back to the paragraph gap or the numbered line."""
    j = anchor - 1
    if j < floor:
        return anchor
    while True:
        l = lines[j]
        if l['numish']:
            break
        if l.get('gap_before'):
            # a page break is not a paragraph gap when Tamil continues above
            if l.get('page_top') and j - 1 >= floor and (lines[j - 1]['tamil'] or lines[j - 1]['numish']):
                j -= 1
                continue
            # a stray non-Tamil line (an opening avaṟṟuḷ the CSV lacks, a word
            # the OCR split off) directly below a Tamil line belongs to the block
            if not l['tamil'] and j - 1 >= floor and (lines[j - 1]['tamil'] or lines[j - 1]['numish']):
                j -= 1
                continue
            break
        if j - 1 < floor:
            break
        j -= 1
    return j


def title_start(lines, tstart, floor):
    j = tstart
    while j - 1 >= floor and tstart - j < 3 and heading_like(lines[j - 1]):
        j -= 1
    return j


def body_lines(lines, a, b):
    """Translation lines in [a, b): drop Tamil, centred, example and note lines."""
    out, example = [], False
    for l in lines[a:b]:
        if l['eg']:
            example = True
        if example:
            continue
        if l['tamil'] or l['centred']:
            continue
        if l['text'].startswith('*') or re.fullmatch(r'[*\s.]+', l['text']):
            continue
        if l['indent'] >= INDENT and out:
            continue
        out.append(l)
    return out


def repair_translit(lines, i, end, gen):
    translit = []
    for k, l in enumerate(lines[i:end]):
        ocr = fix_ocr_latin(l['text'])
        if k < len(gen) and ratio(strip_marks(ocr), strip_marks(gen[k])) >= 0.8:
            translit.append(gen[k])
        else:
            translit.append(ocr)
    return translit


def fallback_anchor(lines, lo, hi, gen):
    """For a sutra with no transliteration match: look for a Tamil block start
    in [lo, hi) and treat the paragraph after it as the transliteration."""
    for i in range(lo + 1, hi):
        l = lines[i]
        if l.get('gap_before') and (l['tamil'] or l['numish']) and not l['centred'] \
                and not l['eg'] and l['indent'] < INDENT:
            j = i + 1
            while j < hi and (lines[j]['tamil'] or not lines[j].get('gap_before')):
                j += 1
            if j < hi and candidate_line(lines[j]):
                return j
    return None


def segment(lines, anchors, gens, offs):
    """Per anchored sutra: transliteration range, Tamil block and title start."""
    order = sorted(anchors)
    segs = []
    for k, no in enumerate(order):
        anchor = anchors[no]
        gen = gens[no][offs.get(no, 0):]
        nxt = order[k + 1] if k + 1 < len(order) else None
        limit = anchors[nxt] if nxt is not None else len(lines)
        t_end, t_score = translit_end(lines, anchor, gen, limit)
        floor = segs[-1]['t_end'] if segs else 0
        ts = tamil_start(lines, anchor, floor)
        segs.append({'no': no, 'anchor': anchor, 't_end': t_end, 't_score': t_score,
                     'ts': ts, 'tt': title_start(lines, ts, floor), 'gen': gen,
                     'omitted': gens[no][:offs.get(no, 0)]})
    for k, s in enumerate(segs):
        s['body_end'] = segs[k + 1]['tt'] if k + 1 < len(segs) else len(lines)
        # the book runs this sutra together with the previous one: its
        # transliteration follows the previous one's with no Tamil in between
        s['merged'] = k > 0 and s['ts'] == s['anchor'] and segs[k - 1]['t_end'] == s['anchor']
    return segs


def find_split(lines, seg):
    """The book sometimes prints one CSV sutra as two numbered sutras.  Then
    the transliteration of the remaining lines turns up later in the segment,
    after its own Tamil block; return (tamil start, start, end) or None."""
    gen = seg['gen']
    used = seg['t_end'] - seg['anchor']
    if used >= len(gen):
        return None
    remaining = [strip_marks(g) for g in gen[used:]]
    for p in range(seg['t_end'] + 1, seg['body_end']):
        l = lines[p]
        if not candidate_line(l) or l['indent'] >= INDENT:
            continue
        if any(ratio(l['skel'], r) >= 0.8 for r in remaining):
            ts2 = tamil_start(lines, p, seg['t_end'])
            if ts2 == p or not any(lines[j]['tamil'] or lines[j]['numish'] for j in range(ts2, p)):
                return None  # no Tamil block of its own: not a second sutra
            t_end2, _ = translit_end(lines, p, gen[used:], seg['body_end'])
            return ts2, p, t_end2
    return None


def parse_sutras(ocr_dir, csv_lines):
    lines = collect_lines(ocr_dir, FIRST_PAGE, LAST_PAGE)
    for i, l in enumerate(lines):
        l['idx'] = i
    gens = {no: [transliterate(t) for t in csv_lines[no]] for no in csv_lines if no >= 1}
    anchors, scores, offs = find_anchors(lines, gens)
    # fallbacks for the unanchored, in order
    for no in sorted(gens):
        if no in anchors:
            continue
        prev = max((a for a in anchors if a < no), default=None)
        nxt = min((a for a in anchors if a > no), default=None)
        lo = translit_end(lines, anchors[prev], gens[prev][offs.get(prev, 0):], len(lines))[0] \
            if prev is not None else 0
        hi = tamil_start(lines, anchors[nxt], lo) if nxt is not None else len(lines)
        hit = fallback_anchor(lines, lo, hi, gens[no])
        if hit is not None:
            anchors[no], scores[no] = hit, 0.0
    segs = segment(lines, anchors, gens, offs)
    rows = []
    offset = 0          # book number - CSV number, changes at merges and splits
    prev_edition = None
    for k, s in enumerate(segs):
        no, gen = s['no'], s['gen']
        anchor, t_end, ts, tt = s['anchor'], s['t_end'], s['ts'], s['tt']
        warn = []
        translit = list(s['omitted']) + repair_translit(lines, anchor, t_end, gen)
        split = find_split(lines, s)
        if split:
            ts2, p, t_end2 = split
            translit += repair_translit(lines, p, t_end2, gen[t_end - anchor:])
            body = body_lines(lines, t_end, ts2) + body_lines(lines, t_end2, s['body_end'])
            t_lines = t_end - anchor + t_end2 - p
            s['t_score'] = ratio(''.join(l['skel'] for l in lines[anchor:t_end] + lines[p:t_end2]),
                                 strip_marks(''.join(gen)))
        else:
            body = body_lines(lines, t_end, s['body_end'])
            t_lines = t_end - anchor
        if s['merged']:
            edition = prev_edition
            offset -= 1
            warn.append('printed as one sutra with the previous one (shared translation)')
        else:
            edition = no + offset
        edition_no = f'{edition}-{edition + 1}' if split else str(edition)
        if split:
            offset += 1
            warn.append('printed as two sutras in the book')
        prev_edition = edition + 1 if split else edition
        if s['omitted']:
            warn.append(f'book omits opening line {" / ".join(s["omitted"])}')
        if scores[no] == 0.0:
            warn.append('anchored by layout only')
        elif scores[no] < ANCHOR_STRONG:
            warn.append(f'weak anchor {scores[no]:.2f}')
        if t_lines != len(gen):
            warn.append(f'translit lines {t_lines} != tamil lines {len(gen)}')
        if s['t_score'] < 0.75:
            warn.append(f'translit match {s["t_score"]:.2f}')
        num = lines[ts]['num']
        if num is not None and abs(num) != edition and not str(edition).endswith(str(abs(num))):
            warn.append(f'number read as {num}, expected {edition}')
        if s['merged']:
            sim = None
        else:
            tam = re.sub(r'[^஀-௿]', '', ''.join(l['tam_raw'] for l in lines[ts:anchor]))
            ref = re.sub(r'[^஀-௿]', '', ''.join(csv_lines[no]))
            sim = ratio(tam, ref) if ref else 0
            if ts == anchor:
                warn.append('no tamil block')
            elif sim < 0.6:
                warn.append(f'tamil match {sim:.2f}')
        if k and no - segs[k - 1]['no'] > 1:
            warn.append(f'sutras {segs[k - 1]["no"] + 1}..{no - 1} not found')
        translation = '\n'.join(fix_ocr_latin(l['text']) for l in body)
        if s['merged'] and rows and not rows[-1]['translation']:
            rows[-1]['translation'] = translation
            rows[-1]['warnings'] = '; '.join(w for w in rows[-1]['warnings'].split('; ') if w and w != 'no translation')
        if not translation:
            warn.append('no translation')
        rows.append({
            'book_no': no,
            'edition_no': edition_no,
            'title': clean_title(' '.join(l['text'] for l in lines[tt:ts])),
            'transliteration': '\n'.join(translit),
            'translation': translation,
            'pages': ','.join(str(p) for p in sorted({l['page'] for l in lines[tt:s['body_end']]})),
            'tamil_sim': '' if sim is None else f'{sim:.2f}',
            'translit_sim': f'{s["t_score"]:.2f}',
            'anchor_sim': f'{scores[no]:.2f}',
            'num_read': '' if num is None else str(num),
            'warnings': '; '.join(warn),
        })
    return rows


def parse_prologue(ocr_dir, csv_lines):
    lines = collect_lines(ocr_dir, PROLOGUE_PAGES[0], PROLOGUE_PAGES[-1])
    gen = [transliterate(t) for t in csv_lines[0]]
    cands = [i for i, l in enumerate(lines) if candidate_line(l)]
    anchor = max(cands, key=lambda i: block_score(lines, i, strip_marks(''.join(gen)), len(gen)))
    t_end, score = translit_end(lines, anchor, gen, len(lines))
    body = body_lines(lines, t_end, len(lines))
    return {'book_no': 0, 'edition_no': '', 'title': 'Prologue',
            'transliteration': '\n'.join(repair_translit(lines, anchor, t_end, gen)),
            'translation': '\n'.join(fix_ocr_latin(l['text']) for l in body),
            'pages': ','.join(map(str, PROLOGUE_PAGES)),
            'tamil_sim': '', 'translit_sim': f'{score:.2f}', 'anchor_sim': '',
            'num_read': '', 'warnings': '' if score >= 0.75 else f'translit match {score:.2f}'}


# ---------------------------------------------------------------- csv
def load_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        rd = csv.DictReader(f)
        rows = list(rd)
        fields = [c for c in rd.fieldnames if c not in NEW_COLS]
    csv_lines = {}
    for g, row in enumerate(rows, start=1):
        csv_lines[g - 1] = [ws(x) for x in row['பாடல்'].split('\n') if ws(x)]
    return rows, fields, csv_lines


def main():
    ocr_dir = sys.argv[1]
    csv_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'data', 'final', 'tholkappiyam.csv')
    report = sys.argv[3] if len(sys.argv) > 3 else os.path.join(ROOT, 'data', 'work', 'reports', 'english_ocr.csv')
    rows, fields, csv_lines = load_csv(csv_path)
    found = [parse_prologue(ocr_dir, csv_lines)] + parse_sutras(ocr_dir, csv_lines)
    by_no = {r['book_no']: r for r in found}
    os.makedirs(os.path.dirname(report), exist_ok=True)
    with open(report, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(found[0].keys()))
        w.writeheader()
        w.writerows(found)
    missing = [n for n in range(len(rows)) if n not in by_no]
    for g, row in enumerate(rows, start=1):
        r = by_no.get(g - 1)
        row['english_edition_no'] = r['edition_no'] if r else ''
        row['title'] = r['title'] if r else ''
        row['transliteration'] = r['transliteration'] if r else ''
        row['translation'] = r['translation'] if r else ''
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields + NEW_COLS)
        w.writeheader()
        w.writerows(rows)
    nwarn = sum(1 for r in found if r['warnings'])
    titled = sum(1 for r in found if r['title'])
    strong = sum(1 for r in found if r['anchor_sim'] and float(r['anchor_sim']) >= ANCHOR_STRONG)
    numbad = sum(1 for r in found if 'number read as' in r['warnings'])
    print(f'sutras found: {len(found)}; strong anchors: {strong}; with title: {titled}; '
          f'with warnings: {nwarn}; printed number disagrees: {numbad}; '
          f'missing: {len(missing)} {missing[:30]}')
    print(f'wrote {csv_path} and {report}')


if __name__ == '__main__':
    main()
