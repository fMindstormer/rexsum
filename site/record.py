"""Record the README's demo: the standalone examples opened from disk in Chromium with JavaScript
disabled, a payment card's last digit changed from 1 to 2, then a German IBAN's. Writes
media/demo.gif and a still for reduced motion, media/demo-poster.png.
    pip install playwright pillow && python -m playwright install chromium
    python site/record.py"""
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "media"
W, H, BAR = 720, 440, 44
frames = []      # (image, milliseconds)


def font(size):
    for name in ("/System/Library/Fonts/SFNS.ttf", "/System/Library/Fonts/Helvetica.ttc",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default(size)


BOLD = font(17)


def shot(page, caption, ms):
    img = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
    canvas = Image.new("RGB", (W, H + BAR), "#202124")
    canvas.paste(img, (0, BAR))
    d = ImageDraw.Draw(canvas)
    d.text((16, BAR // 2), caption, font=BOLD, fill="#ffffff", anchor="lm")
    frames.append((canvas, ms))


def edit(page, caption, keys):
    inp = page.locator("#f")
    inp.click()
    page.keyboard.press("End")
    for k in keys:
        page.keyboard.press(k)
        shot(page, caption, 450)


with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_context(java_script_enabled=False, viewport={"width": W, "height": H}).new_page()
    for name, last, wrong, label in [("card", "1", "2", "Payment card"), ("iban_de", "0", "2", "German IBAN")]:
        page.goto((ROOT / "site" / "examples" / f"{name}.html").as_uri())
        js = "Chromium, JavaScript disabled"
        shot(page, f"{js} · {name}.html opened from disk", 1800)
        edit(page, f"{js} · {label}: last digit {last} → {wrong}", ["Backspace", wrong])
        frames[-1] = (frames[-1][0], 2600)
        if name == "card":
            poster = frames[-1][0]
        edit(page, f"{js} · {label}: back to {last}", ["Backspace", last])
        frames[-1] = (frames[-1][0], 1600)
    b.close()

OUT.mkdir(exist_ok=True)
poster.save(OUT / "demo-poster.png", optimize=True)
pal = [f.quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f, _ in frames]
pal[0].save(OUT / "demo.gif", save_all=True, append_images=pal[1:], duration=[ms for _, ms in frames], loop=0, optimize=True)
print({f.name: f"{f.stat().st_size / 1000:.0f} kB" for f in OUT.iterdir()})
