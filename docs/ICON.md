# Launcher icon

The current icon is based on the Stremio launcher icon, with "AA" added by the
maintainer. It is not original artwork. Stremio's logo and trademarks belong to
Stremio. It is used here for an unofficial, non-commercial clone.

## Source

- Source image: `overlay/source-icon.webp`
- Format: WebP, 192x192, RGBA
- The source has a transparent border, which is normal for launcher artwork.
- The generator trims that border, then adds a controlled safe margin.
- Generator: `scripts/make_icon.py`
- Library: Pillow

The adaptive icon background is `#100F1F`, which matches the dark square in the
source image.

## Generated files

| File | Size | Purpose |
| --- | --- | --- |
| `overlay/icon-preview.png` | 512x512 | README preview |
| `overlay/res/drawable-nodpi/ic_launcher_foreground.png` | 432x432 | Adaptive icon foreground |
| `overlay/res/drawable-nodpi/ic_launcher_monochrome.png` | 432x432 | Android themed icon |
| `overlay/res/mipmap-mdpi/ic_launcher.webp` | 48x48 | Legacy icon |
| `overlay/res/mipmap-hdpi/ic_launcher.webp` | 72x72 | Legacy icon |
| `overlay/res/mipmap-xhdpi/ic_launcher.webp` | 96x96 | Legacy icon |
| `overlay/res/mipmap-xxhdpi/ic_launcher.webp` | 144x144 | Legacy icon |
| `overlay/res/mipmap-xxxhdpi/ic_launcher.webp` | 192x192 | Legacy icon |

## Layout rules

- Legacy icons: the visible artwork fills about 94 percent of the canvas.
- Adaptive foreground: the visible artwork is scaled to 300 px inside the
  432 px foreground. This keeps the corners and the AA mark inside a circular
  launcher mask.
- Monochrome icon: white silhouette taken from the bright parts of the source
  image, with the dark background removed.
- Transparent padding around the source is expected. The script removes the
  source padding and re-adds the correct margins for each icon type.

## Replacing the icon

1. Replace `overlay/source-icon.webp` with a new square image.
2. A 512x512 or 1024x1024 source is recommended; the current 192x192 source
   will look slightly soft when upscaled on high density screens.
3. Run:

```powershell
python scripts/make_icon.py
```

4. Build the APK normally. The build script copies `overlay/res` into the
   decoded APK.

If the new artwork has a different shape, adjust `LEGACY_CONTENT_RATIO` or
`ADAPTIVE_CONTENT_RATIO` in `scripts/make_icon.py`.
