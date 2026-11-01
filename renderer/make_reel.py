"""Build the Friday "What Dropped" Reel (1080x1920 MP4, silent) from Street Source's public release list.

Spec (one line of JSON in the Image Specs sheet, path ending in .mp4):
  {"type": "reel", "friday": "2026-11-06", "barcodes": ["...", ...]}
  - barcodes: optional, in the order to show. If missing, up to 8 releases from that date are picked
    (vinyl with cover art first, one per artist and title).
  - head: optional intro headline (default "WHAT DROPPED").

Music is added in Instagram when posting, so the file has no audio.

Usage: python renderer/make_reel.py <dir containing fonts/> <spec.json> <out.mp4>
"""
import asyncio, datetime as dt, html as H, json, os, subprocess, sys, tempfile, urllib.request
from pathlib import Path
from playwright.async_api import async_playwright

FEED = os.environ.get("RELEASES_FEED", "https://streetsource.app/api/public/releases")
A, C, S, CU = "#1B1D21", "#ECE9E2", "#F2B705", "#55585E"
W, HT = 1080, 1920
SLIDE_SECONDS, INTRO_SECONDS, OUTRO_SECONDS, MAX_ITEMS = 1.6, 2.0, 2.2, 10

BASE, SPEC, OUT = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text()), Path(sys.argv[3])
F = BASE / "fonts"


def ff(fam, file, wt):
    p = next(F.glob(f"*/package/files/{file}"))
    return f"@font-face{{font-family:'{fam}';src:url('file://{p}') format('woff2');font-weight:{wt}}}"


FONTS = (ff("Barlow Condensed", "barlow-condensed-latin-700-normal.woff2", 700)
         + ff("Archivo", "archivo-latin-500-normal.woff2", 500) + ff("Archivo", "archivo-latin-800-normal.woff2", 800))
MARK = f'''<svg viewBox="0 0 200 200" width="64" height="64"><g fill="none" stroke="{C}" stroke-width="12" stroke-linecap="round"><path d="M26,50 C72,50 78,100 118,100"/><path d="M26,100 L118,100"/><path d="M26,150 C72,150 78,100 118,100"/></g><circle cx="26" cy="50" r="11" fill="{C}"/><circle cx="26" cy="100" r="11" fill="{C}"/><circle cx="26" cy="150" r="11" fill="{C}"/><line x1="116" y1="100" x2="156" y2="100" stroke="{S}" stroke-width="20"/><polygon points="150,74 188,100 150,126" fill="{S}"/></svg>'''


def page(body):
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>{FONTS}
html,body{{margin:0}} body{{width:{W}px;height:{HT}px;background:{A};color:{C};overflow:hidden;font-family:'Archivo'}}
.card{{box-sizing:border-box;width:100%;height:100%;padding:150px 90px 130px;display:flex;flex-direction:column}}
.kick{{align-self:flex-start;background:{S};color:{A};font-weight:800;font-size:38px;letter-spacing:.1em;padding:14px 28px;border-radius:10px}}
.bc{{font-family:'Barlow Condensed';font-weight:700;text-transform:uppercase;letter-spacing:.03em;line-height:.95}}
.main{{flex:1;display:flex;flex-direction:column;justify-content:center}}
.cover{{width:900px;height:900px;object-fit:cover;border-radius:8px;box-shadow:0 30px 80px rgba(0,0,0,.5);background:#2a2d33}}
.blank{{width:900px;height:900px;border-radius:8px;background:#2a2d33;display:flex;align-items:center;justify-content:center}}
.sub{{font-size:44px;font-weight:500;color:#B9B6AE;margin-top:18px;line-height:1.25}}
.foot{{display:flex;align-items:center;gap:16px;font-family:'Barlow Condensed';font-weight:700;font-size:40px;letter-spacing:.08em;opacity:.9}}
</style></head><body><div class="card">{body}<div class="foot">{MARK}STREET SOURCE</div></div></body></html>'''


def fetch(friday):
    if FEED.startswith("file://"):  # local testing: a saved copy of the feed
        return json.loads(Path(FEED[7:]).read_text())["items"]
    url = f"{FEED}?start={friday}&end={friday}"
    req = urllib.request.Request(url, headers={"User-Agent": "streetsource-social"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read().decode())["items"]


def choose(items, barcodes):
    if barcodes:
        by = {i["barcode"]: i for i in items}
        return [by[b] for b in barcodes if b in by][:MAX_ITEMS]
    seen, out = set(), []
    rank = lambda i: (0 if i.get("image") else 1, 0 if (i.get("kind") or i.get("format") or "").lower().startswith(("vinyl", "lp")) else 1)
    for i in sorted(items, key=rank):
        key = (i["artist"].lower(), i["title"].split("[")[0].strip().lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(i)
    return out[:8]


def nice_date(iso):
    d = dt.date.fromisoformat(iso)
    return d.strftime("%a %b ") + str(d.day)


async def main():
    friday = SPEC["friday"]
    picks = choose(fetch(friday), SPEC.get("barcodes") or [])
    if not picks:
        sys.exit(f"No releases found for {friday}.")
    tmp = Path(tempfile.mkdtemp())
    slides = []
    intro = page(f'''<div class="kick">{H.escape(nice_date(friday).upper())}</div><div class="main">
<div class="bc" style="font-size:260px">{H.escape(SPEC.get("head", "What dropped"))}</div>
<div class="sub" style="font-size:56px">{len(picks)} new releases at your local record store.</div></div>''')
    slides.append((intro, INTRO_SECONDS))
    for i in picks:
        art = f'<img class="cover" src="{H.escape(i["image"])}">' if i.get("image") else \
              f'<div class="blank bc" style="font-size:90px;color:{CU}">NEW</div>'
        title = i["title"]
        slides.append((page(f'''<div class="kick">WHAT DROPPED</div><div class="main">{art}
<div class="bc" style="font-size:92px;margin-top:56px">{H.escape(i["artist"])}</div>
<div class="sub">{H.escape(title)}</div></div>'''), SLIDE_SECONDS))
    outro = page(f'''<div class="kick">SHOP LOCAL</div><div class="main">
<div class="bc" style="font-size:200px">Get them at your local shop.</div></div>''')
    slides.append((outro, OUTRO_SECONDS))

    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": W, "height": HT})
        lines = []
        for n, (html, secs) in enumerate(slides):
            f = tmp / f"s{n:02d}.html"; f.write_text(html)
            await pg.goto(f"file://{f}", wait_until="networkidle")
            await pg.evaluate("document.fonts.ready")
            await pg.wait_for_timeout(200)
            png = tmp / f"s{n:02d}.png"
            await pg.screenshot(path=str(png))
            lines += [f"file '{png}'", f"duration {secs}"]
        await b.close()
    lines.append(f"file '{tmp / f's{len(slides) - 1:02d}.png'}'")  # ffmpeg concat needs the last frame repeated
    (tmp / "list.txt").write_text("\n".join(lines) + "\n")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"),
                    "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                    "-movflags", "+faststart", str(OUT)], check=True)
    print(f"{OUT}: {len(picks)} releases, " + ", ".join(f'{i["artist"]} - {i["title"]}' for i in picks))


asyncio.run(main())
