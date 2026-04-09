#!/usr/bin/env python3
"""
Script to:
1. Extract PNGs from font_2 SVGs
2. Vectorize with potrace
3. Add lowercase glyphs to existing OkiDoki font
"""

import os, base64, re, subprocess, sys

BASE = os.path.dirname(os.path.abspath(__file__))
FONT2_DIR = os.path.join(BASE, 'font_2')
FONT_TEST_DIR = os.path.join(BASE, 'font_test')
VECTOR_DIR = os.path.join(BASE, 'font2_vectors')
PNG_DIR = os.path.join(BASE, 'font2_pngs')

os.makedirs(VECTOR_DIR, exist_ok=True)
os.makedirs(PNG_DIR, exist_ok=True)

# Complete mapping: slice filename -> character
# Duplicates resolved: keep first occurrence only
MAPPING = {
    'slice1.svg':  '8',
    'slice2.svg':  'm',
    'slice3.svg':  'g',
    'slice4.svg':  'q',
    'slice5.svg':  'p',
    'slice6.svg':  'd',
    'slice7.svg':  'b',
    'slice8.svg':  'w',
    'slice9.svg':  'k',
    'slice10.svg': 'h',
    'slice11.svg': '9',
    'slice12.svg': '6',
    'slice13.svg': 'o',
    'slice14.svg': '5',
    'slice15.svg': '2',
    'slice16.svg': '3',
    'slice17.svg': 'e',
    'slice18.svg': 'u',
    # slice19 missing from folder
    'slice20.svg': 'y',
    'slice21.svg': 'n',
    'slice22.svg': 'a',
    'slice23.svg': 'e',   # duplicate e — skip
    'slice24.svg': 's',
    'slice25.svg': 'x',
    'slice26.svg': 'z',
    'slice27.svg': '4',
    'slice28.svg': 'c',
    'slice29.svg': 'v',
    'slice30.svg': 's',   # duplicate s — skip
    'slice31.svg': 'f',
    'slice32.svg': '7',
    'slice33.svg': 't',
    'slice34.svg': 'r',
    'slice35.svg': 'r',   # duplicate r — skip
    'slice36.svg': 'j',
    'slice37.svg': 'o',   # duplicate o — skip
    'slice38.svg': 'i',
    'slice39.svg': '1',   # duplicate 1 (already in font_test) — include for lowercase set
    'slice40.svg': 'l',
    'slice41.svg': 'o',   # duplicate o — skip
    'slice42.svg': 'l',   # duplicate l — skip
}

# Deduplicate: only keep first occurrence of each character
seen = {}
UNIQUE_MAPPING = {}
for fname, char in MAPPING.items():
    if char not in seen:
        seen[char] = fname
        UNIQUE_MAPPING[fname] = char

print(f"Total slices: {len(MAPPING)}, unique chars: {len(UNIQUE_MAPPING)}")
print("Unique chars:", sorted(UNIQUE_MAPPING.values()))
print()

# ── Step 1: Extract PNGs ──────────────────────────────────────────────────────
print("=== Step 1: Extracting PNGs ===")
for fname in UNIQUE_MAPPING:
    svg_path = os.path.join(FONT2_DIR, fname)
    if not os.path.exists(svg_path):
        print(f"  MISSING: {svg_path}")
        continue
    with open(svg_path) as f:
        content = f.read()
    match = re.search(r'base64,([^"]+)', content)
    if not match:
        print(f"  NO BASE64: {fname}")
        continue
    png_data = base64.b64decode(match.group(1))
    char = UNIQUE_MAPPING[fname]
    png_path = os.path.join(PNG_DIR, f'{char}.png')
    with open(png_path, 'wb') as f:
        f.write(png_data)
    print(f"  {fname} -> {char}.png")

print()

# ── Step 2: Vectorize with potrace ────────────────────────────────────────────
print("=== Step 2: Vectorizing with potrace ===")
for fname, char in UNIQUE_MAPPING.items():
    png_path = os.path.join(PNG_DIR, f'{char}.png')
    pbm_path = os.path.join(PNG_DIR, f'{char}.pbm')
    svg_out  = os.path.join(VECTOR_DIR, f'{char}.svg')

    if not os.path.exists(png_path):
        print(f"  SKIP (no png): {char}")
        continue

    # Flatten alpha channel: black letter on white background, then threshold
    r = subprocess.run(
        ['magick', png_path,
         '-background', 'white', '-alpha', 'remove', '-alpha', 'off',
         '-threshold', '50%',
         pbm_path],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print(f"  magick FAIL [{char}]: {r.stderr.strip()}")
        continue

    # Trace with potrace -> SVG
    r2 = subprocess.run(
        ['potrace', '-s', '--flat', pbm_path, '-o', svg_out],
        capture_output=True, text=True
    )
    if r2.returncode != 0:
        print(f"  potrace FAIL [{char}]: {r2.stderr.strip()}")
        continue

    print(f"  {char} -> {os.path.basename(svg_out)}")

print()

# ── Step 3: Add glyphs to existing font ──────────────────────────────────────
print("=== Step 3: Adding glyphs to OkiDoki font ===")

import fontforge

EXISTING_SFD = os.path.join(FONT_TEST_DIR, 'OkiDoki.sfd')
OUTPUT_TTF   = os.path.join(FONT_TEST_DIR, 'OkiDoki.ttf')
OUTPUT_SFD   = os.path.join(FONT_TEST_DIR, 'OkiDoki.sfd')

EM           = 1000
ASCENT       = 800
DESCENT      = 200
SIDE_BEARING = 30

# Load existing font
if os.path.exists(EXISTING_SFD):
    print(f"  Loading existing font: {EXISTING_SFD}")
    font = fontforge.open(EXISTING_SFD)
else:
    print("  Creating new font (no existing SFD found)")
    font = fontforge.font()
    font.fontname  = "OkiDokiFont"
    font.familyname = "OkiDoki"
    font.fullname  = "OkiDoki Regular"
    font.copyright = "OkiDoki"
    font.encoding  = "UnicodeFull"
    font.em        = EM
    font.ascent    = ASCENT
    font.descent   = DESCENT

success = 0
fail = 0

for fname, char in sorted(UNIQUE_MAPPING.items(), key=lambda x: x[1]):
    svg_path = os.path.join(VECTOR_DIR, f'{char}.svg')

    if not os.path.exists(svg_path):
        print(f"  SKIP (no vector): '{char}'")
        fail += 1
        continue

    unicode_val = ord(char)
    glyph_name  = f"uni{unicode_val:04X}"
    print(f"  '{char}' (U+{unicode_val:04X}) <- {os.path.basename(svg_path)}")

    try:
        glyph = font.createChar(unicode_val, glyph_name)
        glyph.importOutlines(svg_path)

        bb = glyph.boundingBox()
        glyph_w = bb[2] - bb[0]
        glyph_h = bb[3] - bb[1]

        if glyph_w <= 0 or glyph_h <= 0:
            print(f"    -> WARN: invalid bbox {bb}")
            glyph.width = 500
            fail += 1
            continue

        # Scale to ascent height
        scale = ASCENT / glyph_h
        glyph.transform((scale, 0, 0, scale, 0, 0))

        # Reposition: baseline at y=0, left edge at SIDE_BEARING
        bb2 = glyph.boundingBox()
        glyph.transform((1, 0, 0, 1, -bb2[0] + SIDE_BEARING, -bb2[1]))

        bb3 = glyph.boundingBox()
        glyph.width = int(bb3[2]) + SIDE_BEARING

        glyph.simplify()
        glyph.correctDirection()
        glyph.removeOverlap()

        print(f"    -> OK  scale={scale:.3f}  width={glyph.width}")
        success += 1

    except Exception as e:
        print(f"    -> ERROR: {e}")
        fail += 1

print()
print(f"Result: {success} OK, {fail} failed")
print()

print(f"Saving {OUTPUT_SFD}...")
font.save(OUTPUT_SFD)

print(f"Generating {OUTPUT_TTF}...")
font.generate(OUTPUT_TTF)

print()
print(f"Font updated: {OUTPUT_TTF}")
print(f"Total glyphs in font: {font.__len__()}")

# Install to macOS Fonts
fonts_dir = os.path.expanduser('~/Library/Fonts')
install_path = os.path.join(fonts_dir, 'OkiDoki.ttf')
import shutil
shutil.copy2(OUTPUT_TTF, install_path)
print(f"Installed to: {install_path}")
