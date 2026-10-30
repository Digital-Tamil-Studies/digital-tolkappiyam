#!/usr/bin/env python3
"""Stage 2: dictionary csv + corpus -> app/data/dict.js, app/data/thol.js,
data/work/reports/gloss_coverage.csv.

Headwords in data/source/thol_dictionary_metadata_all_5947.csv look like
    பொருள்¹  பொருள்²            superscript = sense number
    நிலை²-த்தல்  அஃகு-தல்        verb lemma: stem-suffix
    இயல்(லு)-தல்                 bracketed alternates
    கூறியது கூறல்                multi-word terms
They are normalised into lookup *keys*; the display form is kept.

Every distinct corpus token is resolved to a key offline (exact, sandhi strip,
suffix strip, then data/manual/token_map.csv), so the browser only does a map
lookup. data/work/reports/gloss_coverage.csv lists every token with its match for review.

References like (தொல். 1051:2) use another edition's numbering, so each one is
resolved by matching the quoted sutra fragment against sutras near that number.
"""
import csv, json, os, re, collections
from build_corpus import ws, strip_punct, tokenize_line

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT_CSV = os.path.join(ROOT, "data", "source", "thol_dictionary_metadata_all_5947.csv")
OVERRIDES_CSV = os.path.join(ROOT, "data", "manual", "token_map.csv")
REPORT_CSV = os.path.join(ROOT, "data", "work", "reports", "gloss_coverage.csv")
OUT_THOL = os.path.join(ROOT, "app", "data", "thol.js")
OUT_DICT = os.path.join(ROOT, "app", "data", "dict.js")

SUP = "¹²³⁴⁵⁶⁷⁸⁹⁰"
SUP_MAP = {c: str(i) for i, c in enumerate("⁰¹²³⁴⁵⁶⁷⁸⁹")}
VERB_SUFFIX_RE = re.compile(r"^(.*?)-(த்தல்|தல்|த\(ற\)ல்|ட்டல்|ரல்|றல்|ல்)$")

# Inflection endings tried (longest first) when a token has no exact key.
SUFFIXES = sorted([
    "ும்மே", "ும்", "ே", "ின்", "ினும்", "ொடு", "ோடு", "ால்", "ான்", "க்கு", "கு", "ாக", "ான",
    "அது", "து", "ார்", "ின", "ன்", "ர்", "ள்", "ை", "ோ", "ாய்", "ிய", "ும்மே", "ே", "ாம்",
    "வும்", "யும்", "த்து", "த்தின்", "த்தும்", "த்தே", "ிற்று", "ீற்று", "ான", "ிடை",
], key=len, reverse=True)
SANDHI_RE = re.compile(r"^(.+?)([கசதப])்$")


# ---------------------------------------------------------------- headwords
def parse_headword(raw):
    """-> (display, sense_no, keys:set). display keeps hyphen/brackets, drops superscript."""
    w = ws(raw)
    sense = "".join(SUP_MAP[c] for c in w if c in SUP_MAP) or None
    display = "".join(c for c in w if c not in SUP_MAP)
    display = re.sub(r"\s+", " ", display).strip()
    base = re.sub(r"\s*\([^)]*\)", "", display).strip()      # drop (…) alternates
    keys = {base, base.replace("-", "")}
    m = VERB_SUFFIX_RE.match(base)
    if m:
        stem, suf = m.group(1), m.group(2).replace("(", "").replace(")", "")
        keys.update({stem, stem + suf})
    # bracketed alternate: இயல்(லு)-தல் -> இயலு, இயலுதல்
    m2 = re.match(r"^(.*?)\(([^)]*)\)(.*)$", display)
    if m2 and m2.group(2) and not re.search(r"\s", m2.group(2)):
        alt = (m2.group(1) + m2.group(2) + m2.group(3)).replace("-", "")
        keys.add(alt)
        if m2.group(3).startswith("-"):
            keys.add(m2.group(1) + m2.group(2))
    return display, sense, {k for k in keys if k}


def lemma_of(display):
    base = re.sub(r"\s*\([^)]*\)", "", display).strip()
    return base.replace("-", "")


# ---------------------------------------------------------------- references
REF_RE = re.compile(r"தொல்\.?\s*(\d+)(?::\s*([\d\-, ]+))?")


def words_of(text):
    return {strip_punct(w) for w in re.split(r"\s+", text) if len(strip_punct(w)) > 1}


def resolve_ref(ref, meaning, sutra_flat_by_g, max_g, window=8, threshold=0.6):
    """Return the global id of the cited sutra, or None.

    The cited edition's numbering differs from ours, so we look at sutras within
    +-window of the cited number and pick the one that contains most words of
    the quoted fragment. Words are matched as substrings of the sutra text with
    spaces removed, which tolerates sandhi joins such as அவன்இவன்.
    """
    m = REF_RE.search(ref or "")
    if not m:
        return None
    n = int(m.group(1))
    frags = []
    last = meaning.rsplit(".", 1)[-1].strip()
    if last:
        frags.append(last)
    parts = re.split(r"[,;]", meaning)
    if len(parts) > 1 and parts[-1].strip():
        frags.append(parts[-1].strip())
    tail = re.split(r"\s+", meaning.strip())[-8:]
    frags.append(" ".join(tail))
    best, best_score = None, 0.0
    for frag in frags:
        q = [w for w in words_of(frag)]
        if len(q) < 2:
            continue
        for g in range(max(1, n - window), min(max_g, n + window) + 1):
            flat = sutra_flat_by_g[g]
            score = sum(1 for w in q if w in flat) / len(q)
            if score > best_score or (score == best_score and best is not None and abs(g - n) < abs(best - n)):
                best, best_score = g, score
        if best_score >= threshold:
            break
    return best if best_score >= threshold else None


# ---------------------------------------------------------------- token map
def load_overrides():
    out = {}
    if not os.path.exists(OVERRIDES_CSV):
        return out
    with open(OVERRIDES_CSV, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            t, k = ws(r.get("token")), ws(r.get("key"))
            if t:
                out[t] = k
    return out


def candidates(tok):
    """Ordered guesses for a token: sandhi-stripped, then suffix-stripped stems."""
    forms = [tok]
    m = SANDHI_RE.match(tok)
    if m:
        forms.append(m.group(1))
    out = []
    for f in forms:
        for s in SUFFIXES:
            if f.endswith(s) and len(f) > len(s) + 1:
                stem = f[: -len(s)]
                out += [stem, stem + "்", stem + "ம்", stem + "ு", stem + "்தல்", stem + "தல்"]
    return forms[1:] + out


def resolve_tokens(tokens_counter, index, overrides):
    """-> {token: (key|None, method)}"""
    res = {}
    for tok in tokens_counter:
        if tok in overrides:
            k = overrides[tok]
            res[tok] = (k if k and k != "-" and k in index else None, "override")
            continue
        if tok in index:
            res[tok] = (tok, "exact"); continue
        hit = None
        for c in candidates(tok):
            if c in index:
                hit = c; break
        res[tok] = (hit, "fallback" if hit else "miss")
    return res


# ---------------------------------------------------------------- emit
def write_js(path, var, payload):
    literal = json.dumps(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), ensure_ascii=False)
    literal = literal.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(f"window.{var}=JSON.parse({literal});\n")
    print(f"wrote {os.path.relpath(path, ROOT)} ({os.path.getsize(path)/1e6:.2f} MB)")


def main(corpus):
    with open(DICT_CSV, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    need = {"word", "word_type", "meaning", "tholkappiyam_reference"}
    if need - set(rows[0].keys()):
        raise SystemExit(f"{DICT_CSV}: missing columns {sorted(need - set(rows[0].keys()))}")

    sutras = corpus["sutras"]
    max_g = len(sutras)
    sutra_flat = {s["g"]: re.sub(r"[\s" + re.escape(".,;:!?()\"'-") + "]", "", " ".join(s["lines"])) for s in sutras}

    # ---- entries grouped by display headword
    entries, by_head = [], {}
    nref_total = nref_ok = 0
    for r in rows:
        display, sense, keys = parse_headword(r["word"])
        if not display:
            continue
        e = by_head.get(display)
        if e is None:
            e = {"id": len(entries) + 1, "head": display, "lemma": lemma_of(display),
                 "keys": set(), "senses": []}
            by_head[display] = e
            entries.append(e)
        e["keys"] |= keys
        ref = ws(r["tholkappiyam_reference"])
        meaning = ws(r["meaning"])
        ref_g = None
        if ref and "தொல்" in ref:
            nref_total += 1
            ref_g = resolve_ref(ref, meaning, sutra_flat, max_g)
            nref_ok += ref_g is not None
        e["senses"].append({"no": sense, "type": ws(r["word_type"]), "meaning": meaning,
                            "ref": ref or None, "ref_g": ref_g})

    for e in entries:
        e["senses"].sort(key=lambda s: int(s["no"] or 0))
        e["keys"] = sorted(e["keys"])
    entries.sort(key=lambda e: e["lemma"])
    for i, e in enumerate(entries, start=1):
        e["id"] = i

    index = collections.defaultdict(list)
    for e in entries:
        for k in e["keys"]:
            index[k].append(e["id"])

    # ---- tokens
    counter = collections.Counter()
    for s in sutras:
        for line in s["lines"]:
            for _surface, bare in tokenize_line(line):
                if bare:
                    counter[bare] += 1
    overrides = load_overrides()
    res = resolve_tokens(counter, index, overrides)
    tokmap = {t: k for t, (k, _m) in res.items() if k}

    for s in sutras:
        s["tokens"] = [[[surf, tokmap.get(bare)] if tokmap.get(bare) else [surf]
                        for surf, bare in tokenize_line(line)] for line in s["lines"]]

    os.makedirs(os.path.dirname(REPORT_CSV), exist_ok=True)
    with open(REPORT_CSV, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["token", "count", "key", "method", "headwords"])
        for tok, cnt in counter.most_common():
            k, method = res[tok]
            heads = "; ".join(entries[i - 1]["head"] for i in index.get(k, [])) if k else ""
            w.writerow([tok, cnt, k or "", method, heads])

    total = sum(counter.values())
    by_method = collections.Counter()
    for tok, cnt in counter.items():
        k, method = res[tok]
        by_method["override" if method == "override" else ("miss" if not k else method)] += cnt
    cov = {m: f"{c/total:.1%}" for m, c in sorted(by_method.items())}
    hit_tokens = sum(c for m, c in by_method.items() if m != "miss")
    print(f"dictionary: {len(entries)} headwords, {len(rows)} senses, {len(index)} keys")
    print(f"tokens: {total} total, {len(counter)} distinct; covered {hit_tokens/total:.1%} {cov}")
    print(f"refs: {nref_ok}/{nref_total} தொல். references resolved to a sutra")

    # ---- emit
    os.makedirs(os.path.dirname(OUT_THOL), exist_ok=True)
    write_js(OUT_THOL, "THOL", {"atikarams": corpus["atikarams"], "sutras": sutras})
    write_js(OUT_DICT, "THOL_DICT", {"entries": entries, "index": dict(index)})


if __name__ == "__main__":
    import build_corpus
    main(build_corpus.main())
