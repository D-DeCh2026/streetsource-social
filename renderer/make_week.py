"""Render a week of Street Source social cards from a JSON spec.
Usage: python make_week.py <scratchpad> <spec.json> <out_dir>
Card types: stat, news, releases, prompt
"""
import asyncio, json, sys, html as H
from pathlib import Path
from playwright.async_api import async_playwright
from PIL import Image

BASE = Path(sys.argv[1]); SPEC = json.loads(Path(sys.argv[2]).read_text()); OUT = Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
F = BASE / "fonts"
def ff(fam, file, wt):
    p = next(F.glob(f"*/package/files/{file}"))
    return f"@font-face{{font-family:'{fam}';src:url('file://{p}') format('woff2');font-weight:{wt}}}"
CSS_FONTS = (ff("Barlow Condensed","barlow-condensed-latin-700-normal.woff2",700)
           + ff("Archivo","archivo-latin-500-normal.woff2",500)
           + ff("Archivo","archivo-latin-700-normal.woff2",700)
           + ff("Archivo","archivo-latin-800-normal.woff2",800))
A, C, S, CU = "#1B1D21", "#ECE9E2", "#F2B705", "#55585E"
W, HT = 1080, 1440

def mark(sz, fg, ac):
    return f'''<svg viewBox="0 0 200 200" width="{sz}" height="{sz}"><path d="M26,50 C72,50 78,100 118,100" fill="none" stroke="{fg}" stroke-width="12" stroke-linecap="round"/><path d="M26,100 L118,100" fill="none" stroke="{fg}" stroke-width="12" stroke-linecap="round"/><path d="M26,150 C72,150 78,100 118,100" fill="none" stroke="{fg}" stroke-width="12" stroke-linecap="round"/><circle cx="26" cy="50" r="11" fill="{fg}"/><circle cx="26" cy="100" r="11" fill="{fg}"/><circle cx="26" cy="150" r="11" fill="{fg}"/><line x1="116" y1="100" x2="156" y2="100" stroke="{ac}" stroke-width="20"/><polygon points="150,74 188,100 150,126" fill="{ac}"/></svg>'''

def page(bg, fg, body, src="", foot_fg=None):
    foot_fg = foot_fg or fg
    srcline = f'<div class="src">{H.escape(src)}</div>' if src else '<div></div>'
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>{CSS_FONTS}
html,body{{margin:0}} body{{width:{W}px;height:{HT}px;background:{bg};color:{fg};overflow:hidden;font-family:'Archivo'}}
.card{{box-sizing:border-box;width:100%;height:100%;padding:96px 90px 80px;display:flex;flex-direction:column}}
.kick{{align-self:flex-start;font-weight:800;font-size:34px;letter-spacing:.1em;padding:14px 26px;border-radius:10px}}
.bc{{font-family:'Barlow Condensed';font-weight:700;text-transform:uppercase;letter-spacing:.03em;line-height:.95}}
.main{{flex:1;display:flex;flex-direction:column;justify-content:center}}
.sub{{font-weight:500;font-size:44px;line-height:1.3;margin-top:40px}}
.foot{{display:flex;justify-content:space-between;align-items:center;color:{foot_fg};opacity:.85}}
.brand{{display:flex;align-items:center;gap:14px;font-family:'Barlow Condensed';font-weight:700;font-size:34px;letter-spacing:.08em}}
.src{{font-size:26px;font-weight:500}}
.rel{{list-style:none;margin:0;padding:0}} .rel li{{padding:20px 0;border-bottom:2px solid rgba(236,233,226,.18)}}
.rel .ar{{font-family:'Barlow Condensed';font-weight:700;font-size:56px;letter-spacing:.03em;text-transform:uppercase;line-height:1}}
.rel .ti{{font-size:32px;font-weight:500;color:#B9B6AE;margin-top:6px}}
</style></head><body><div class="card">{body}
<div class="foot"><div class="brand">{mark(54, foot_fg, A if bg==S else S)}STREET SOURCE</div>{srcline}</div></div></body></html>'''

def render(c):
    t = c["type"]
    if t == "stat":
        body = f'''<div class="kick" style="background:{S};color:{A}">{H.escape(c["kicker"])}</div>
<div class="main"><div class="bc" style="font-size:{c.get("size",260)}px;color:{S}">{H.escape(c["big"])}</div>
<div class="sub" style="color:{C}">{H.escape(c["line"])}</div></div>'''
        return page(A, C, body, c.get("src",""))
    if t == "news":
        body = f'''<div class="kick" style="background:{A};color:{C}">{H.escape(c["kicker"])}</div>
<div class="main"><div class="bc" style="font-size:{c.get("size",128)}px">{H.escape(c["head"])}</div>
<div class="sub" style="color:{CU}">{H.escape(c["line"])}</div></div>'''
        return page(C, A, body, c.get("src",""))
    if t == "releases":
        items = "".join(f'<li><div class="ar">{H.escape(a)}</div><div class="ti">{H.escape(b)}</div></li>' for a,b in c["items"])
        body = f'''<div class="kick" style="background:{S};color:{A}">{H.escape(c["kicker"])}</div>
<div class="bc" style="font-size:120px;margin:40px 0 20px">{H.escape(c["head"])}</div>
<div class="main" style="justify-content:flex-start"><ul class="rel">{items}</ul></div>'''
        return page(A, C, body, c.get("src",""))
    if t == "prompt":
        body = f'''<div class="kick" style="background:{A};color:{S}">{H.escape(c["kicker"])}</div>
<div class="main"><div class="bc" style="font-size:{c.get("size",170)}px">{H.escape(c["head"])}</div>
<div class="sub" style="font-weight:700">{H.escape(c["line"])}</div></div>'''
        return page(S, A, body, c.get("src",""))
    raise ValueError(t)

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={"width":W,"height":HT})
        for c in SPEC:
            f = OUT / f'{c["file"]}.html'; f.write_text(render(c))
            await pg.goto(f"file://{f}"); await pg.evaluate("document.fonts.ready"); await pg.wait_for_timeout(250)
            png = OUT / f'{c["file"]}.png'
            await pg.screenshot(path=str(png))
            # shrink file size for upload: palette PNG
            Image.open(png).convert("RGB").quantize(colors=64, method=Image.Quantize.MEDIANCUT).save(png, optimize=True)
            # overflow check
            over = await pg.evaluate("document.querySelector('.card').scrollHeight > document.querySelector('.card').clientHeight")
            print(c["file"], "OVERFLOW" if over else "ok", png.stat().st_size)
        await b.close()
asyncio.run(main())

# contact sheet
ims = [Image.open(OUT / f'{c["file"]}.png') for c in SPEC]
s = 300; h = int(s*4/3); cols = 4; rows = (len(ims)+cols-1)//cols
sheet = Image.new("RGB", (cols*(s+6), rows*(h+6)), "white")
for i, im in enumerate(ims):
    sheet.paste(im.convert("RGB").resize((s,h), Image.LANCZOS), ((i%cols)*(s+6), (i//cols)*(h+6)))
sheet.save(OUT / "_contact.png")
