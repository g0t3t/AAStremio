#!/usr/bin/env python3
"""Generate AAStremio launcher icons from the source image."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "overlay" / "source-icon.webp"
RES = ROOT / "overlay" / "res"

# The source icon has a transparent border. Crop it, then add a safe margin.
LEGACY_CONTENT_RATIO = 0.94
ADAPTIVE_CONTENT_RATIO = 0.694  # 300 px in a 432 px foreground
MONO_THRESHOLD = 70


def load_content() -> Image.Image:
    with Image.open(SOURCE) as source:
        image = source.convert("RGBA")
    box = image.getchannel("A").getbbox()
    if box is None:
        raise SystemExit(f"{SOURCE} has no visible pixels")
    return image.crop(box)


def fit(content: Image.Image, canvas_size: int, content_size: int) -> Image.Image:
    scale = min(content_size / content.width, content_size / content.height)
    target = (
        max(1, round(content.width * scale)),
        max(1, round(content.height * scale)),
    )
    scaled = content.resize(target, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    x = (canvas_size - scaled.width) // 2
    y = (canvas_size - scaled.height) // 2
    canvas.alpha_composite(scaled, (x, y))
    return canvas


def legacy(size: int) -> Image.Image:
    return fit(load_content(), size, max(1, int(size * LEGACY_CONTENT_RATIO)))


def adaptive_foreground(size: int = 432) -> Image.Image:
    return fit(load_content(), size, int(size * ADAPTIVE_CONTENT_RATIO))


def monochrome(size: int = 432) -> Image.Image:
    content = load_content()
    gray = content.convert("L")
    mask = gray.point(lambda value: 255 if value > MONO_THRESHOLD else 0)
    mask = ImageChops.multiply(mask, content.getchannel("A"))

    white = Image.new("RGBA", content.size, (255, 255, 255, 255))
    mono = Image.new("RGBA", content.size, (0, 0, 0, 0))
    mono.paste(white, (0, 0), mask)
    return fit(mono, size, int(size * ADAPTIVE_CONTENT_RATIO))


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(f"Source icon not found: {SOURCE}")

    (RES / "drawable-nodpi").mkdir(parents=True, exist_ok=True)
    adaptive_foreground().save(RES / "drawable-nodpi" / "ic_launcher_foreground.png")
    monochrome().save(RES / "drawable-nodpi" / "ic_launcher_monochrome.png")

    sizes = {
        "mdpi": 48,
        "hdpi": 72,
        "xhdpi": 96,
        "xxhdpi": 144,
        "xxxhdpi": 192,
    }
    for density, px in sizes.items():
        folder = RES / f"mipmap-{density}"
        folder.mkdir(parents=True, exist_ok=True)
        legacy(px).save(folder / "ic_launcher.webp", "WEBP", quality=95, method=6)

    fit(load_content(), 512, int(512 * LEGACY_CONTENT_RATIO)).save(
        ROOT / "overlay" / "icon-preview.png"
    )
    print(f"Generated icons from {SOURCE}")


if __name__ == "__main__":
    main()
