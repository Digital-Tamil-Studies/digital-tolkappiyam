#!/usr/bin/env python3
"""Build the Tholkappiyam site data.

    python3 scripts/build.py

Stage 1 (build_corpus.py)     data/final/tholkappiyam.csv -> structure + sutras
Stage 2 (build_dictionary.py) dictionary csv  -> entries, lookup index, resolved refs,
                              token->headword map, app/data/thol.js, app/data/dict.js,
                              data/work/reports/gloss_coverage.csv
"""
import os
import build_corpus, build_dictionary

if __name__ == "__main__":
    corpus = build_corpus.main()
    build_dictionary.main(corpus)
    # commentaries for the poem view (1961 Tamil, Murugan English)
    build_dictionary.write_js(os.path.join(build_dictionary.ROOT, "app", "data", "notes.js"), "THOL_NOTES", corpus["notes"])
