# editor-image

Image processing toolkit for the OKI Creator platform. Three standalone services/scripts for background removal, image optimization, and font pipeline generation.

---

## Services

### `rembg-image` — Background Removal Service
REST API (FastAPI) for removing image backgrounds using [rembg](https://github.com/danielgatis/rembg). Designed for Docker Swarm deployment with CI/CD via GitHub Actions.

**Tech:** Python · FastAPI · rembg · Docker
**Endpoint:** `POST /api/rembg/process`

```bash
curl -X POST "http://localhost:8000/api/rembg/process" \
  -F "file=@image.jpg" -o output.png
```

**Run locally:**
```bash
cd rembg-image
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Docker:**
```bash
docker compose up
```

---

### `compact-image` — Web Image Optimizer
CLI script for batch converting and optimizing images for the web. Supports HEIC, PNG, JPG → AVIF/WebP conversion, resizing, cropping, and bulk renaming.

**Tech:** Python · Pillow · pillow-heif
**Formats:** AVIF (preferred), WebP fallback

```bash
cd compact-image
pip install -r requirements.txt

# Process all images in current directory
python image_processor.py

# Process a single image
python image_processor.py -i photo.heic

# Force WebP output
python image_processor.py --format webp

# Bulk rename with prefix
python image_processor.py --rename project
```

**What it does:**
- Converts HEIC/PNG/JPG to AVIF or WebP
- Resizes to web-safe dimensions (max 1920×1080)
- Crops bottom 15% of images (configurable)
- Renames files with sequential numbering (`prefix_001`, `prefix_002`, …)

---

### `font-pipeline` — Custom Font Generator
Pipeline for generating TTF fonts from SVG/PNG artwork exported from Affinity Designer. Handles the full flow: bitmap tracing → vector SVG → FontForge TTF.

**Tech:** Python · FontForge · Potrace/AutoTrace · Inkscape

**What it does:**
- Extracts embedded PNG bitmaps from Affinity Designer SVG exports
- Traces bitmaps to clean vector paths
- Maps glyphs to Unicode characters
- Outputs a usable `.ttf` font for macOS and web

See [`font-pipeline/DOCS.md`](font-pipeline/DOCS.md) for the full pipeline walkthrough.

---

## Structure

```
editor-image/
├── rembg-image/          # Background removal API (FastAPI + Docker)
├── compact-image/        # Image optimization CLI (Python scripts)
├── font-pipeline/        # Font generation pipeline
└── README.md
```

---

## Integration with OKI Creator

- **moda-service** → `rembg-image`: `POST /api/remove-bg` for brand avatar backgrounds
- **architectury** → `rembg-image`: `POST /api/remove-bg` for blueprint asset cleanup

---

## License

Part of the [OKI Creator](https://okicreator.com) platform.
