#!/usr/bin/env python3
"""Package the deployable site into one zip.

    python3 scripts/package_site.py             -> dist/tholkappiyam-YYYYMMDD.zip
    python3 scripts/package_site.py out.zip     -> that path

Run scripts/build.py first. The zip holds the contents of app/:

    index.html
    assets/app.js  assets/styles.css
    data/thol.js   data/dict.js   data/notes.js

Unzip into any folder of a static web host; all paths are relative.
"""
import os, shutil, sys, time, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app")
FILES = ["index.html", "assets/app.js", "assets/styles.css", "data/thol.js", "data/dict.js", "data/notes.js"]


def main(argv):
    out = argv[0] if argv else os.path.join(ROOT, "dist", f"tholkappiyam-{time.strftime('%Y%m%d')}.zip")
    missing = [f for f in FILES if not os.path.exists(os.path.join(APP, f))]
    if missing:
        sys.exit("missing: " + ", ".join(missing) + "\nRun 'python3 scripts/build.py' first.")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)

    def entry(name):
        # fixed 644 mode so the files are world-readable after unzip on any host
        info = zipfile.ZipInfo(name, date_time=time.localtime()[:6])
        info.external_attr = 0o644 << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        return info

    raw = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for rel in FILES:
            full = os.path.join(APP, rel)
            with open(full, "rb") as src, z.open(entry(rel), "w") as dst:
                shutil.copyfileobj(src, dst, 1 << 20)
            raw += os.path.getsize(full)
    print(f"wrote {out}: {len(FILES)} files, {raw/1e6:.1f} MB -> {os.path.getsize(out)/1e6:.1f} MB zipped")


if __name__ == "__main__":
    main(sys.argv[1:])
