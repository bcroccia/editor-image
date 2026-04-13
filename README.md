# editor-image

Image processing toolkit for the OKI Creator platform.

---

## Services

### `image-service` — Unified Image Processing API

REST API (FastAPI) for background removal, image compression/optimization, and AI relighting.

**Tech:** Python · FastAPI · rembg · Pillow · torch/diffusers · Docker

**Endpoints:**
- `POST /api/rembg/process` — Remove background
- `POST /api/compact-image/process` — Compress/optimize image
- `POST /api/compact-image/info` — Image info
- `POST /api/v1/remove-bg` — Legacy endpoint

```bash
cd image-service
docker compose up
```

---

### `font-pipeline` — Custom Font Generator

CLI pipeline for generating TTF fonts from SVG/PNG artwork exported from Affinity Designer.

**Tech:** Python · FontForge · Potrace/AutoTrace · Inkscape

See [`font-pipeline/DOCS.md`](font-pipeline/DOCS.md) for the full pipeline walkthrough.

---

## Structure

```
editor-image/
├── image-service/        # Unified image processing API (FastAPI + Docker)
│   ├── app/features/
│   │   ├── rembg/            # Background removal
│   │   ├── compact_image/    # Image compression
│   │   ├── ic_light/         # AI relighting
│   │   └── background_removal/ # Legacy v1 endpoint
│   ├── Dockerfile
│   └── docker-compose.yml
├── font-pipeline/        # Font generation CLI
└── README.md
```

---

## Integration with OKI Creator

- **moda-service** → `image-service`: `POST /api/v1/remove-bg` for brand avatar backgrounds
- **architectury** → `image-service`: `POST /api/v1/remove-bg` for blueprint asset cleanup

---

## License

Part of the [OKI Creator](https://okicreator.com) platform.
