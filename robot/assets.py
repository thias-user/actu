"""Outil ponctuel (pas utilisé par le robot quotidien) : icônes de l'application et QR code d'installation.

    python robot/assets.py icons
    python robot/assets.py qr https://pseudo.github.io/actu/
Nécessite : pip install pillow qrcode
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "app" / "icons"
RED = (255, 59, 48)
FONTS = ["C:/Windows/Fonts/ariblk.ttf", "C:/Windows/Fonts/seguibl.ttf", "C:/Windows/Fonts/arialbd.ttf",
         "/System/Library/Fonts/Supplemental/Arial Black.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]


def font(size):
    for f in FONTS:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def icon(size, scale=1.0):
    """Fond noir, « ACTU » en blanc, barre rouge dessous."""
    big = size * 4  # dessin en grand puis réduction = bords nets
    img = Image.new("RGB", (big, big), (0, 0, 0))
    d = ImageDraw.Draw(img)
    target_w = big * 0.70 * scale
    fs = int(big * 0.3)
    f = font(fs)
    w = d.textlength("ACTU", font=f)
    f = font(int(fs * target_w / w))
    l, t, r, b = d.textbbox((0, 0), "ACTU", font=f)
    tw, th = r - l, b - t
    bar_h = int(big * 0.045 * scale)
    gap = int(big * 0.05 * scale)
    total = th + gap + bar_h
    x = (big - tw) / 2 - l
    y = (big - total) / 2 - t
    d.text((x, y), "ACTU", font=f, fill=(255, 255, 255))
    bar_w = tw * 0.42
    by = (big - total) / 2 + th + gap
    d.rectangle([(big - tw) / 2, by, (big - tw) / 2 + bar_w, by + bar_h], fill=RED)
    return img.resize((size, size), Image.LANCZOS)


def make_icons():
    ICONS.mkdir(parents=True, exist_ok=True)
    icon(512).save(ICONS / "icon-512.png", optimize=True)
    icon(192).save(ICONS / "icon-192.png", optimize=True)
    icon(180).save(ICONS / "apple-touch-icon.png", optimize=True)
    icon(512, scale=0.72).save(ICONS / "icon-maskable-512.png", optimize=True)
    icon(64).resize((32, 32), Image.LANCZOS).save(ICONS / "favicon-32.png", optimize=True)
    print("Icônes créées dans", ICONS)


def make_qr(url):
    import qrcode
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=16, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    code = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    lines = [("Scannez avec l'appareil photo de l'iPhone", 30, (0, 0, 0)),
             ("puis dans Safari : Partager, « Sur l'écran d'accueil »", 22, (90, 90, 90)),
             (url, 22, (150, 150, 150))]
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    W = int(max([code.width + 160] + [probe.textlength(t, font=font(s)) + 100 for t, s, _ in lines]))
    H = code.height + 420
    card = Image.new("RGB", (W, H), (255, 255, 255))
    logo = icon(150)
    card.paste(logo, ((W - 150) // 2, 50))
    card.paste(code, ((W - code.width) // 2, 230))
    d = ImageDraw.Draw(card)
    y = code.height + 262
    for text, size, color in lines:
        f = font(size)
        d.text(((W - d.textlength(text, font=f)) / 2, y), text, font=f, fill=color)
        y += size + 22
    out = ROOT / "qr-code-actu.png"
    card.save(out, optimize=True)
    print("QR code :", out)


if __name__ == "__main__":
    if sys.argv[1:2] == ["icons"]:
        make_icons()
    elif sys.argv[1:2] == ["qr"] and len(sys.argv) > 2:
        make_qr(sys.argv[2])
    else:
        print(__doc__)
