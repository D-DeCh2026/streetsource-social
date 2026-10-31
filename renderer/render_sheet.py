"""Render any card listed in the Street Source Image Specs sheet that isn't in the repo yet.

The sheet (shared as "anyone with the link can view") has columns:
  A Image path   e.g. images/2026-11-02/2026-11-02_indie-share.png
  B Spec (JSON)  card spec for renderer/make_week.py (the "file" key is optional)

Usage: python renderer/render_sheet.py <dir containing fonts/>
Run from the repo root. Exits 0 when there is nothing to do.
"""
import csv, io, json, os, subprocess, sys, tempfile, urllib.request
from collections import defaultdict
from pathlib import Path

SHEET_ID = os.environ.get("SPEC_SHEET_ID", "1dT-3jIGWm3klZ5Kdbz3VGx5LCvZLEB3p_PDZowcfS4E")
URL = os.environ.get("SPEC_CSV_URL", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0")
FONTS_BASE = sys.argv[1]
ROOT = Path.cwd()

try:
    raw = urllib.request.urlopen(URL, timeout=60).read().decode("utf-8")
except Exception as e:
    raw = "<" + str(e)
if raw.lstrip().startswith("<"):
    sys.exit("The Image Specs sheet isn't readable. Set its sharing to 'Anyone with the link: Viewer'.")

todo = defaultdict(list)
for i, row in enumerate(csv.reader(io.StringIO(raw))):
    if i == 0 or len(row) < 2 or not row[0].strip() or not row[1].strip():
        continue
    path = Path(row[0].strip())
    if path.suffix != ".png" or path.parts[0] != "images" or ".." in path.parts:
        print(f"skip row {i+1}: bad path {path}"); continue
    if (ROOT / path).exists():
        continue
    try:
        spec = json.loads(row[1])
    except json.JSONDecodeError as e:
        print(f"skip row {i+1}: bad JSON ({e})"); continue
    spec["file"] = path.stem
    todo[path.parent].append(spec)

if not todo:
    print("nothing to render"); sys.exit(0)

for folder, specs in todo.items():
    out = ROOT / folder
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(specs, f)
    subprocess.run([sys.executable, str(ROOT / "renderer/make_week.py"), FONTS_BASE, f.name, str(out)], check=True)
    for junk in list(out.glob("*.html")) + [out / "_contact.png"]:
        junk.unlink(missing_ok=True)
    # keep a record of every spec rendered in this folder
    rec = out / "spec.json"
    existing = json.loads(rec.read_text()) if rec.exists() else []
    names = {s["file"] for s in specs}
    rec.write_text(json.dumps([s for s in existing if s.get("file") not in names] + specs, indent=1))
    print(f"rendered {len(specs)} in {folder}")
