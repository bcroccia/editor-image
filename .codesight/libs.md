# Libraries

- `font-pipeline/auto_font.py`
  - function extract_png: (svg_path, out_dir) -> Path | None
  - function ocr_identify: (png_path) -> tuple[str, float]
  - function claude_identify: (png_path) -> str
  - function identify_char: (png_path, filename) -> str
  - function vectorize: (png_path, out_dir, char) -> Path | None
  - function add_glyph: (font, char, svg_path) -> bool
  - _...1 more_
- `image-service/main.py` — function health_check: ()
- `image-service/test_rembg.py` — function remove_background: (image_path, output_path, api_url)
- `image-service/web/src/hooks/use-scroll-reveal.ts` — function useScrollReveal: (threshold) => void
