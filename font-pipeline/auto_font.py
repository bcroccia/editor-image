#!/usr/bin/env python3
"""
auto_font.py — Pipeline automatizado para criar/atualizar a fonte OkiDoki.

Uso:
    python3 auto_font.py <pasta_com_slices> [--font <caminho_do_sfd>]

Exemplos:
    python3 auto_font.py font_2/
    python3 auto_font.py font_3/ --font font_test/OkiDoki.sfd

Fluxo:
    1. Extrai PNG de cada SVG (base64 embutido)
    2. Identifica o caractere:
       a. Tesseract OCR (rápido, local)
       b. Claude Vision API (se tesseract incerto)
       c. Input manual (fallback)
    3. Vetoriza com potrace
    4. Adiciona/atualiza glifos na fonte
    5. Gera TTF e instala em ~/Library/Fonts/
"""

import os, sys, re, base64, subprocess, shutil, argparse, json
from pathlib import Path

# Carrega .env se existir (ex: ANTHROPIC_API_KEY=sk-ant-...)
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

# ─── Dependências ────────────────────────────────────────────────────────────
try:
    import pytesseract
    from PIL import Image, ImageOps, ImageFilter
except ImportError:
    sys.exit("Erro: instale com  pip3 install pytesseract Pillow")

try:
    import anthropic
except ImportError:
    sys.exit("Erro: instale com  pip3 install anthropic")

try:
    import fontforge
except ImportError:
    sys.exit("Erro: fontforge não encontrado. Use  brew install fontforge")

# ─── Configurações ───────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OCR_CONFIDENCE_THRESHOLD = 80   # abaixo disso → chama Claude (fontes decorativas raramente passam)
EM           = 1000
ASCENT       = 800
DESCENT      = 200
SIDE_BEARING = 30

# Caracteres válidos que a fonte suporta
VALID_CHARS = set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    "!@#$%&*()-_=+[]{}|;:',.<>?/ "
)

# ─── Passo 1: Extrai PNG do SVG ──────────────────────────────────────────────
def extract_png(svg_path: Path, out_dir: Path) -> Path | None:
    """Extrai o PNG embutido em base64 dentro do SVG."""
    content = svg_path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r'base64,([^"\']+)', content)
    if not match:
        return None
    data = base64.b64decode(match.group(1))
    png_path = out_dir / f"{svg_path.stem}.png"
    png_path.write_bytes(data)
    return png_path


# ─── Passo 2a: Tesseract OCR ─────────────────────────────────────────────────
def ocr_identify(png_path: Path) -> tuple[str, float]:
    """
    Retorna (caractere, confiança 0-100).
    confiança < OCR_CONFIDENCE_THRESHOLD → incerto.
    """
    img = Image.open(png_path).convert("L")

    # Pré-processamento: fundo branco, letra preta, escala maior
    img = ImageOps.invert(img)                       # inverte: letra vira branca
    img = img.point(lambda p: 255 if p > 50 else 0) # threshold
    img = ImageOps.invert(img)                       # volta: letra preta em fundo branco
    img = img.resize((img.width * 4, img.height * 4), Image.LANCZOS)

    # Tenta OCR com config para caractere único
    cfg = "--psm 10 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    data = pytesseract.image_to_data(img, config=cfg, output_type=pytesseract.Output.DICT)

    # Pega o resultado com maior confiança
    best_char = ""
    best_conf = 0.0
    for i, text in enumerate(data["text"]):
        text = text.strip()
        conf = float(data["conf"][i])
        if len(text) == 1 and conf > best_conf:
            best_char = text
            best_conf = conf

    return best_char, best_conf


# ─── Passo 2b: Claude Vision API ─────────────────────────────────────────────
def claude_identify(png_path: Path) -> str:
    """Envia a imagem para Claude e pede para identificar o caractere."""
    if not ANTHROPIC_API_KEY:
        print("    [Claude] ANTHROPIC_API_KEY não definida — pulando")
        return ""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    img_data = base64.standard_b64encode(png_path.read_bytes()).decode()

    msg = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=10,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img_data,
                    },
                },
                {
                    "type": "text",
                    "text": (
                        "This is a single character from a decorative font. "
                        "Reply with ONLY the single character (letter, digit, or symbol). "
                        "No explanation. Just the character."
                    ),
                },
            ],
        }],
    )

    result = msg.content[0].text.strip()
    # Garante que é só 1 caractere
    if len(result) == 1:
        return result
    # Às vezes Claude responde com aspas: "a" → extrai
    match = re.search(r'[A-Za-z0-9!@#$%&*()\-_=+\[\]{}|;:\'",.<>?/]', result)
    return match.group(0) if match else ""


# ─── Passo 2: Identificação híbrida ─────────────────────────────────────────
def identify_char(png_path: Path, filename: str) -> str:
    """
    1. Tesseract
    2. Se confiança baixa → Claude
    3. Se ambos falham → input manual
    """
    ocr_char, ocr_conf = ocr_identify(png_path)
    print(f"    Tesseract: '{ocr_char}' (confiança {ocr_conf:.0f}%)")

    if ocr_char and ocr_conf >= OCR_CONFIDENCE_THRESHOLD:
        print(f"    → Usando OCR: '{ocr_char}'")
        return ocr_char

    # Tesseract incerto → tenta Claude
    print(f"    Confiança baixa — consultando Claude Vision...")
    claude_char = claude_identify(png_path)
    if claude_char:
        print(f"    Claude: '{claude_char}'")
        # Se OCR e Claude concordam, usa direto
        if ocr_char and ocr_char.lower() == claude_char.lower():
            print(f"    → Ambos concordam: '{claude_char}'")
            return claude_char
        # Se só Claude respondeu
        if not ocr_char:
            print(f"    → Usando Claude: '{claude_char}'")
            return claude_char
        # Se discordam → mostra ambos e pede confirmação
        print(f"    ⚠ Discordância: OCR='{ocr_char}' vs Claude='{claude_char}'")

    # Fallback: input manual
    print(f"    Arquivo: {filename}")
    while True:
        user_input = input(f"    Digite o caractere (ou Enter para '{ocr_char or claude_char}'): ").strip()
        if not user_input:
            result = ocr_char or claude_char
        else:
            result = user_input[0]
        if result:
            print(f"    → Manual: '{result}'")
            return result
        print("    Por favor, digite um caractere.")


# ─── Passo 3: Vetorização ─────────────────────────────────────────────────────
def vectorize(png_path: Path, out_dir: Path, char: str) -> Path | None:
    """PNG → PBM → SVG vetorial via potrace."""
    # Nome de arquivo seguro para o caractere
    safe_name = f"uni{ord(char):04X}"
    pbm_path = out_dir / f"{safe_name}.pbm"
    svg_path = out_dir / f"{safe_name}.svg"

    # Flatten alpha → threshold → PBM
    r = subprocess.run(
        ["magick", str(png_path),
         "-background", "white", "-alpha", "remove", "-alpha", "off",
         "-threshold", "50%",
         str(pbm_path)],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print(f"    magick ERRO: {r.stderr.strip()}")
        return None

    # Vetorizar com potrace
    r2 = subprocess.run(
        ["potrace", "-s", "--flat", str(pbm_path), "-o", str(svg_path)],
        capture_output=True, text=True
    )
    if r2.returncode != 0:
        print(f"    potrace ERRO: {r2.stderr.strip()}")
        return None

    return svg_path


# ─── Passo 4: Adiciona glifo à fonte ─────────────────────────────────────────
def add_glyph(font, char: str, svg_path: Path) -> bool:
    """Importa o SVG vetorial como glifo na fonte."""
    unicode_val = ord(char)
    glyph_name  = f"uni{unicode_val:04X}"

    try:
        glyph = font.createChar(unicode_val, glyph_name)
        glyph.importOutlines(str(svg_path))

        bb = glyph.boundingBox()
        w, h = bb[2] - bb[0], bb[3] - bb[1]

        if w <= 0 or h <= 0:
            print(f"    AVISO: bounding box inválida {bb}")
            glyph.width = 500
            return False

        scale = ASCENT / h
        glyph.transform((scale, 0, 0, scale, 0, 0))

        bb2 = glyph.boundingBox()
        glyph.transform((1, 0, 0, 1, -bb2[0] + SIDE_BEARING, -bb2[1]))

        bb3 = glyph.boundingBox()
        glyph.width = int(bb3[2]) + SIDE_BEARING

        glyph.simplify()
        glyph.correctDirection()
        glyph.removeOverlap()
        return True

    except Exception as e:
        print(f"    ERRO no glifo: {e}")
        return False


# ─── Pipeline principal ───────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Auto font pipeline")
    parser.add_argument("input_dir", help="Pasta com arquivos slice*.svg")
    parser.add_argument("--font", default="", help="Caminho para .sfd existente (opcional)")
    parser.add_argument("--output", default="", help="Caminho de saída do TTF (padrão: <input_dir>/OkiDoki.ttf)")
    parser.add_argument("--mapping", default="", help="JSON com mapeamento manual {slice1: 'A', ...} para pular identificação")
    parser.add_argument("--api-key", default="", help="Anthropic API key (alternativa à variável ANTHROPIC_API_KEY)")
    args = parser.parse_args()

    # API key: argumento tem prioridade sobre variável de ambiente
    global ANTHROPIC_API_KEY
    if args.api_key:
        ANTHROPIC_API_KEY = args.api_key

    if not ANTHROPIC_API_KEY:
        print("⚠  ANTHROPIC_API_KEY não definida.")
        print("   Opções:")
        print("   1. Crie o arquivo .env com:  ANTHROPIC_API_KEY=sk-ant-...")
        print("   2. Use:  export ANTHROPIC_API_KEY=sk-ant-...")
        print("   3. Use:  python3 auto_font.py <pasta> --api-key sk-ant-...")
        print("   Sem a key, Claude não será usado e o fallback será manual.\n")

    input_dir = Path(args.input_dir).resolve()
    if not input_dir.exists():
        sys.exit(f"Pasta não encontrada: {input_dir}")

    # Diretórios de trabalho
    work_dir   = input_dir / "_auto_work"
    png_dir    = work_dir / "pngs"
    vector_dir = work_dir / "vectors"
    for d in [png_dir, vector_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Arquivo de saída
    output_ttf = Path(args.output) if args.output else input_dir / "OkiDoki.ttf"

    # Mapeamento manual opcional
    manual_mapping = {}
    if args.mapping and Path(args.mapping).exists():
        manual_mapping = json.loads(Path(args.mapping).read_text())
        print(f"Mapeamento manual carregado: {len(manual_mapping)} entradas")

    # Encontra todos os SVGs
    svgs = sorted(input_dir.glob("slice*.svg"), key=lambda p: int(re.search(r'\d+', p.stem).group()))
    if not svgs:
        sys.exit(f"Nenhum slice*.svg encontrado em {input_dir}")
    print(f"\nEncontrados {len(svgs)} SVGs em {input_dir}")
    print("=" * 60)

    # Carrega ou cria fonte
    sfd_path = Path(args.font) if args.font else None
    if sfd_path and sfd_path.exists():
        print(f"Carregando fonte existente: {sfd_path}")
        font = fontforge.open(str(sfd_path))
    else:
        # Procura OkiDoki.sfd no diretório padrão
        default_sfd = Path(__file__).parent / "font_test" / "OkiDoki.sfd"
        if default_sfd.exists():
            print(f"Carregando fonte existente: {default_sfd}")
            font = fontforge.open(str(default_sfd))
            sfd_path = default_sfd
        else:
            print("Criando nova fonte OkiDoki")
            font = fontforge.font()
            font.fontname   = "OkiDokiFont"
            font.familyname = "OkiDoki"
            font.fullname   = "OkiDoki Regular"
            font.copyright  = "OkiDoki"
            font.encoding   = "UnicodeFull"
            font.em         = EM
            font.ascent     = ASCENT
            font.descent    = DESCENT

    # Mapeamento final: slice → char (deduplica)
    char_to_slice = {}  # char → primeiro slice que o define
    slice_to_char = {}  # slice → char identificado
    skipped = []

    print("\n─── Identificação de caracteres ───")
    for svg in svgs:
        stem = svg.stem  # ex: "slice1"

        # 1. Mapeamento manual tem prioridade
        if stem in manual_mapping:
            char = manual_mapping[stem]
            print(f"\n[{stem}] Manual: '{char}'")
        else:
            # Extrai PNG
            png = extract_png(svg, png_dir)
            if not png:
                print(f"\n[{stem}] SKIP — sem imagem embutida")
                skipped.append(stem)
                continue

            print(f"\n[{stem}] ({svg.name})")
            char = identify_char(png, svg.name)

        if not char:
            print(f"    SKIP — caractere não identificado")
            skipped.append(stem)
            continue

        # Deduplica: se o char já foi mapeado, pula
        if char in char_to_slice:
            print(f"    SKIP — '{char}' já mapeado por {char_to_slice[char]}")
            skipped.append(stem)
            continue

        char_to_slice[char] = stem
        slice_to_char[stem] = char

    print(f"\n─── Resultado da identificação ───")
    print(f"  Únicos identificados: {len(slice_to_char)}")
    print(f"  Pulados/duplicados:   {len(skipped)}")
    print(f"  Chars: {''.join(sorted(slice_to_char.values()))}")

    # Salva mapeamento para referência futura
    mapping_out = work_dir / "mapping.json"
    mapping_out.write_text(json.dumps(slice_to_char, indent=2, ensure_ascii=False))
    print(f"  Mapeamento salvo: {mapping_out}")

    print("\n─── Vetorização ───")
    ok, fail = 0, 0
    glyph_svgs = {}  # char → svg vetorial

    for stem, char in slice_to_char.items():
        png = png_dir / f"{stem}.png"
        if not png.exists():
            # Extrai novamente se necessário
            svg_path = input_dir / f"{stem}.svg"
            png = extract_png(svg_path, png_dir)
            if not png:
                print(f"  [{stem}] SKIP — sem PNG")
                fail += 1
                continue

        print(f"  '{char}' ({stem})", end=" ")
        svg_vec = vectorize(png, vector_dir, char)
        if svg_vec:
            glyph_svgs[char] = svg_vec
            print("→ OK")
            ok += 1
        else:
            print("→ FALHOU")
            fail += 1

    print(f"  Vetorizados: {ok}, Falhas: {fail}")

    print("\n─── Adicionando glifos à fonte ───")
    ok, fail = 0, 0
    for char in sorted(glyph_svgs):
        svg_vec = glyph_svgs[char]
        print(f"  '{char}' (U+{ord(char):04X})", end=" ")
        if add_glyph(font, char, svg_vec):
            print(f"→ OK  width={font[ord(char)].width}")
            ok += 1
        else:
            print("→ FALHOU")
            fail += 1

    print(f"  Adicionados: {ok}, Falhas: {fail}")

    # Salva e gera TTF
    print(f"\n─── Gerando fonte ───")
    if sfd_path:
        print(f"  Salvando SFD: {sfd_path}")
        font.save(str(sfd_path))

    print(f"  Gerando TTF: {output_ttf}")
    font.generate(str(output_ttf))

    # Instala no Mac
    fonts_dir    = Path.home() / "Library" / "Fonts"
    install_path = fonts_dir / output_ttf.name
    shutil.copy2(output_ttf, install_path)
    print(f"  Instalado: {install_path}")

    # Conta glifos finais
    chars_in_font = [chr(g.unicode) for g in font.glyphs() if g.unicode > 0]
    print(f"\n✓ Fonte atualizada com {len(chars_in_font)} glifos")
    print(f"  Chars: {''.join(sorted(chars_in_font))}")


if __name__ == "__main__":
    main()
