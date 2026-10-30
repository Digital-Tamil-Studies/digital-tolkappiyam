#!/usr/bin/env python3
"""Stage 1: data/final/tholkappiyam.csv -> structure + sutras (in memory).

Called by build.py. Returns a dict:
    {
      "atikarams": [{"id","name","iyals":[{"id","name","count","first_g","last_g"}]}],
      "sutras":    [{"g","a","i","n","lines":[...]}],
      "notes":     {g: {...}}   commentaries for the poem view, see note_for()
    }
Global id g runs 1..N in file order; the சிறப்புப் பாயிரம் is g=1.
"""
import csv, os, re, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS_CSV = os.path.join(ROOT, "data", "final", "tholkappiyam.csv")

# ASCII ids for URLs; order here is display order.
ATIKARAM_IDS = {
    "சிறப்புப் பாயிரம்": "payiram",
    "எழுத்ததிகாரம்": "ezhuthu",
    "சொல்லதிகாரம்": "sol",
    "பொருளதிகாரம்": "porul",
}
ATIKARAM_NUM = {"payiram": 0, "ezhuthu": 1, "sol": 2, "porul": 3}

PUNCT = ".,;:!?()\"'‘’“”-–—"


def ws(s):
    """NFC-normalise and collapse whitespace (as in open_tamil_catalogues)."""
    s = unicodedata.normalize("NFC", str(s or "")).replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


def strip_punct(tok):
    return tok.strip(PUNCT)


def tokenize_line(line):
    """Return [(surface, bare), ...]; surface keeps punctuation, bare is the lookup form."""
    out = []
    for surface in line.split(" "):
        if not surface:
            continue
        out.append((surface, strip_punct(surface)))
    return out


def paras(text):
    return [ws(p) for p in str(text or "").split("\n") if ws(p)]


def note_for(r):
    """Commentary fields of one CSV row, short keys, empty ones left out.

    tt/tp/tc/te  1961 edition (புலியூர்க் கேசிகன் தெளிவுரை): title, sutra text
                 as printed, commentary paragraphs, its sutra number
    et/tr/en/ee  Murugan, Tolkāppiyam in English: title, transliteration lines,
                 translation lines, its sutra number"""
    n = {
        "tt": ws(r.get("title_1961")), "tp": paras(r.get("poem_1961")),
        "tc": paras(r.get("commentary_1961")), "te": ws(r.get("edition_no_1961")),
        "et": ws(r.get("title")), "tr": paras(r.get("transliteration")),
        "en": paras(r.get("translation")), "ee": ws(r.get("english_edition_no")),
    }
    return {k: v for k, v in n.items() if v}


def main():
    with open(CORPUS_CSV, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    need = {"அதிகாரம்", "இயல்", "பாடல் எண்", "பாடல்"}
    missing = need - set(rows[0].keys())
    if missing:
        raise SystemExit(f"{CORPUS_CSV}: missing columns {sorted(missing)}")

    atikarams, by_aid, by_iid = [], {}, {}
    sutras = []
    notes = {}
    for g, r in enumerate(rows, start=1):
        note = note_for(r)
        if note:
            notes[g] = note
        a_name, i_name = ws(r["அதிகாரம்"]), ws(r["இயல்"])
        aid = ATIKARAM_IDS.get(a_name)
        if aid is None:
            raise SystemExit(f"unknown அதிகாரம் {a_name!r} at row {g}")
        if aid not in by_aid:
            by_aid[aid] = {"id": aid, "name": a_name, "iyals": []}
            atikarams.append(by_aid[aid])
        a = by_aid[aid]
        key = (aid, i_name)
        if key not in by_iid:
            iid = f"{ATIKARAM_NUM[aid]}.{len(a['iyals']) + (0 if aid == 'payiram' else 1)}"
            by_iid[key] = {"id": iid, "name": i_name, "count": 0, "first_g": g, "last_g": g}
            a["iyals"].append(by_iid[key])
        iy = by_iid[key]
        iy["count"] += 1
        iy["last_g"] = g
        lines = [ws(l) for l in r["பாடல்"].split("\n") if ws(l)]
        # n: the sutra's sequence number in the whole work (1..1602, as in the
        # printed editions); the prologue is unnumbered (0).  The CSV's
        # பாடல் எண் restarts in every இயல் (Project Madurai) and is not used.
        sutras.append({"g": g, "a": aid, "i": iy["id"], "n": g - 1, "lines": lines})

    print(f"corpus: {len(sutras)} sutras, {sum(len(a['iyals']) for a in atikarams)} iyal, "
          f"{len(atikarams)} atikaram")
    print(f"notes: {len(notes)} sutras with commentary "
          f"({sum(1 for x in notes.values() if 'tc' in x)} Tamil, {sum(1 for x in notes.values() if 'en' in x)} English)")
    return {"atikarams": atikarams, "sutras": sutras, "notes": notes}


if __name__ == "__main__":
    main()
