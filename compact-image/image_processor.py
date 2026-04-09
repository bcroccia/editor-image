#!/usr/bin/env python3
"""
Processador de Imagens para Web
================================
Este script realiza 4 operações:
1. Converte imagens (HEIC, PNG, JPG, etc.) para AVIF ou WebP
2. Compacta para tamanho otimizado para web
3. Corta a imagem para 85% da altura original (remove 15% inferior)
4. Renomeia arquivos em massa com enumeração

Dependências:
    pip install Pillow pillow-heif

Uso:
    python image_processor.py                    # Processa todas as imagens no diretório atual
    python image_processor.py -i imagem.heic    # Processa uma imagem específica
    python image_processor.py -d /caminho/pasta # Processa todas as imagens de uma pasta
    python image_processor.py --format webp     # Força saída em WebP ao invés de AVIF
    python image_processor.py --rename projeto  # Renomeia para projeto_001, projeto_002, etc.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Optional, Tuple

try:
    from PIL import Image
except ImportError:
    print("Erro: Pillow não instalado. Execute: pip install Pillow")
    sys.exit(1)

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIF_SUPPORT = True
except ImportError:
    HEIF_SUPPORT = False
    print("Aviso: pillow-heif não instalado. Arquivos HEIC não serão suportados.")
    print("Para suporte a HEIC, execute: pip install pillow-heif")


# Formatos de entrada suportados
SUPPORTED_INPUT_FORMATS = {
    '.heic', '.heif',  # Apple HEIC
    '.png',            # PNG
    '.jpg', '.jpeg',   # JPEG
    '.webp',           # WebP
    '.bmp',            # Bitmap
    '.tiff', '.tif',   # TIFF
    '.gif',            # GIF (primeira frame)
}

# Configurações padrão para web
WEB_CONFIG = {
    'max_width': 1920,      # Largura máxima (Full HD)
    'max_height': 1080,     # Altura máxima (Full HD)
    'quality_avif': 65,     # Qualidade AVIF (0-100, menor = mais compacto)
    'quality_webp': 80,     # Qualidade WebP (0-100)
    'crop_height_ratio': 0.85,  # Cortar para 85% da altura
}


def check_avif_support() -> bool:
    """Verifica se o sistema suporta AVIF."""
    try:
        # Tenta criar uma imagem pequena e salvar como AVIF
        test_img = Image.new('RGB', (10, 10), color='red')
        from io import BytesIO
        buffer = BytesIO()
        test_img.save(buffer, format='AVIF', quality=50)
        return True
    except Exception:
        return False


def get_output_format(prefer_avif: bool = True) -> Tuple[str, str]:
    """
    Retorna o formato de saída e extensão.
    Prioriza AVIF, mas usa WebP como fallback.
    """
    if prefer_avif and check_avif_support():
        return 'AVIF', '.avif'
    return 'WEBP', '.webp'


def crop_image_height(img: Image.Image, ratio: float = 0.85) -> Image.Image:
    """
    Corta a imagem para uma porcentagem da altura original.

    Args:
        img: Imagem PIL
        ratio: Proporção da altura a manter (0.85 = mantém 85%, remove 15% inferior)

    Returns:
        Imagem cortada
    """
    width, height = img.size
    new_height = int(height * ratio)

    # Crop: (left, upper, right, lower)
    # Mantém a parte superior da imagem
    return img.crop((0, 0, width, new_height))


def resize_for_web(img: Image.Image, max_width: int = 1920, max_height: int = 1080) -> Image.Image:
    """
    Redimensiona a imagem mantendo proporção para caber nos limites.

    Args:
        img: Imagem PIL
        max_width: Largura máxima
        max_height: Altura máxima

    Returns:
        Imagem redimensionada (ou original se já for menor)
    """
    width, height = img.size

    # Se a imagem já é menor que os limites, não redimensiona
    if width <= max_width and height <= max_height:
        return img

    # Calcula a proporção para manter aspecto
    ratio = min(max_width / width, max_height / height)
    new_size = (int(width * ratio), int(height * ratio))

    # LANCZOS é o melhor filtro para redução de tamanho
    return img.resize(new_size, Image.Resampling.LANCZOS)


def process_image(
    input_path: str,
    output_dir: Optional[str] = None,
    output_format: str = 'AVIF',
    crop_ratio: float = 0.85,
    max_width: int = 1920,
    max_height: int = 1080,
    quality: Optional[int] = None,
    output_name: Optional[str] = None
) -> Optional[str]:
    """
    Processa uma imagem: converte, compacta e corta.

    Args:
        input_path: Caminho da imagem de entrada
        output_dir: Diretório de saída (None = mesmo diretório)
        output_format: 'AVIF' ou 'WEBP'
        crop_ratio: Proporção da altura a manter
        max_width: Largura máxima
        max_height: Altura máxima
        quality: Qualidade de compressão (None = usar padrão)
        output_name: Nome do arquivo de saída (sem extensão). Se None, usa o nome original.

    Returns:
        Caminho do arquivo de saída ou None se falhar
    """
    input_path = Path(input_path)

    # Verifica se o formato é suportado
    if input_path.suffix.lower() not in SUPPORTED_INPUT_FORMATS:
        print(f"  ⚠ Formato não suportado: {input_path.suffix}")
        return None

    # Verifica suporte a HEIC
    if input_path.suffix.lower() in {'.heic', '.heif'} and not HEIF_SUPPORT:
        print(f"  ⚠ HEIC não suportado. Instale pillow-heif")
        return None

    try:
        # Abre a imagem
        img = Image.open(input_path)

        # Converte para RGB se necessário (AVIF e WebP não suportam todos os modos)
        if img.mode in ('RGBA', 'LA', 'PA'):
            # Preserva transparência para WebP, converte para RGB para AVIF
            if output_format == 'AVIF':
                # AVIF suporta RGBA, mas para fotos RGB é melhor
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[3])
                else:
                    background.paste(img)
                img = background
        elif img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')

        original_size = img.size

        # 1. Corta a altura (85% da altura original)
        img = crop_image_height(img, crop_ratio)
        cropped_size = img.size

        # 2. Redimensiona para web se necessário
        img = resize_for_web(img, max_width, max_height)
        final_size = img.size

        # Define qualidade
        if quality is None:
            quality = WEB_CONFIG['quality_avif'] if output_format == 'AVIF' else WEB_CONFIG['quality_webp']

        # Define caminho de saída
        extension = '.avif' if output_format == 'AVIF' else '.webp'
        filename = output_name if output_name else input_path.stem
        if output_dir:
            output_path = Path(output_dir) / (filename + extension)
        else:
            output_path = input_path.parent / (filename + extension)

        # Cria diretório de saída se não existir
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Salva a imagem
        save_kwargs = {'quality': quality}
        if output_format == 'AVIF':
            save_kwargs['speed'] = 6  # Velocidade de encoding (0-10, maior = mais rápido)

        img.save(output_path, format=output_format, **save_kwargs)

        # Calcula tamanhos
        original_file_size = input_path.stat().st_size / 1024  # KB
        output_file_size = output_path.stat().st_size / 1024    # KB
        compression_ratio = (1 - output_file_size / original_file_size) * 100

        print(f"  ✓ {input_path.name}")
        print(f"    Original: {original_size[0]}x{original_size[1]} ({original_file_size:.1f} KB)")
        print(f"    Cortado:  {cropped_size[0]}x{cropped_size[1]}")
        print(f"    Final:    {final_size[0]}x{final_size[1]} ({output_file_size:.1f} KB)")
        print(f"    Compressão: {compression_ratio:.1f}% menor")
        print(f"    Salvo em: {output_path.name}")

        return str(output_path)

    except Exception as e:
        print(f"  ✗ Erro ao processar {input_path.name}: {e}")
        return None


def generate_numbered_name(prefix: str, number: int, digits: int = 3) -> str:
    """
    Gera um nome de arquivo com numeração.

    Args:
        prefix: Prefixo do nome (ex: "projeto")
        number: Número atual
        digits: Quantidade de dígitos (ex: 3 -> 001, 002)

    Returns:
        Nome formatado (ex: "projeto_001")
    """
    return f"{prefix}_{str(number).zfill(digits)}"


def rename_files_only(
    directory: str,
    prefix: str,
    output_dir: Optional[str] = None,
    start_number: int = 1,
    digits: int = 3
) -> Tuple[int, int]:
    """
    Renomeia arquivos em massa sem processar (apenas copia com novo nome).

    Args:
        directory: Diretório com as imagens
        prefix: Prefixo para o novo nome
        output_dir: Diretório de saída (None = mesmo diretório)
        start_number: Número inicial
        digits: Quantidade de dígitos na numeração

    Returns:
        Tupla (sucesso, falhas)
    """
    import shutil

    directory = Path(directory)

    if not directory.exists():
        print(f"Erro: Diretório não encontrado: {directory}")
        return 0, 0

    print(f"\n{'='*60}")
    print(f"Renomeador de Arquivos em Massa")
    print(f"{'='*60}")
    print(f"Prefixo: {prefix}")
    print(f"Numeração: {digits} dígitos (início: {start_number})")
    print(f"Diretório: {directory}")
    print(f"{'='*60}\n")

    # Encontra todas as imagens
    images = []
    for ext_pattern in SUPPORTED_INPUT_FORMATS:
        images.extend(directory.glob(f"*{ext_pattern}"))
        images.extend(directory.glob(f"*{ext_pattern.upper()}"))

    # Remove duplicatas e ordena por nome
    images = sorted(set(images), key=lambda x: x.name.lower())

    if not images:
        print("Nenhuma imagem encontrada.")
        return 0, 0

    print(f"Encontradas {len(images)} imagens para renomear:\n")

    # Define diretório de saída
    out_dir = Path(output_dir) if output_dir else directory
    out_dir.mkdir(parents=True, exist_ok=True)

    success = 0
    failed = 0
    current_number = start_number

    for img_path in images:
        try:
            new_name = generate_numbered_name(prefix, current_number, digits)
            new_path = out_dir / (new_name + img_path.suffix.lower())

            shutil.copy2(img_path, new_path)

            print(f"  ✓ {img_path.name} -> {new_path.name}")
            success += 1
            current_number += 1
        except Exception as e:
            print(f"  ✗ Erro ao renomear {img_path.name}: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Concluído: {success} sucesso, {failed} falhas")
    print(f"{'='*60}")

    return success, failed


def process_directory(
    directory: str,
    output_dir: Optional[str] = None,
    prefer_avif: bool = True,
    crop_ratio: float = 0.85,
    max_width: int = 1920,
    max_height: int = 1080,
    rename_prefix: Optional[str] = None,
    start_number: int = 1,
    digits: int = 3
) -> Tuple[int, int]:
    """
    Processa todas as imagens em um diretório.

    Args:
        directory: Diretório com as imagens
        output_dir: Diretório de saída
        prefer_avif: Priorizar AVIF sobre WebP
        crop_ratio: Proporção da altura a manter
        max_width: Largura máxima
        max_height: Altura máxima
        rename_prefix: Prefixo para renomear (None = manter nome original)
        start_number: Número inicial para renomeação
        digits: Quantidade de dígitos na numeração

    Returns:
        Tupla (sucesso, falhas)
    """
    directory = Path(directory)

    if not directory.exists():
        print(f"Erro: Diretório não encontrado: {directory}")
        return 0, 0

    # Determina formato de saída
    output_format, ext = get_output_format(prefer_avif)
    print(f"\n{'='*60}")
    print(f"Processador de Imagens para Web")
    print(f"{'='*60}")
    print(f"Formato de saída: {output_format}")
    print(f"Corte de altura: {crop_ratio*100:.0f}%")
    print(f"Tamanho máximo: {max_width}x{max_height}")
    if rename_prefix:
        print(f"Renomear para: {rename_prefix}_XXX")
    print(f"Diretório: {directory}")
    print(f"{'='*60}\n")

    # Encontra todas as imagens
    images = []
    for ext_pattern in SUPPORTED_INPUT_FORMATS:
        images.extend(directory.glob(f"*{ext_pattern}"))
        images.extend(directory.glob(f"*{ext_pattern.upper()}"))

    # Remove duplicatas e ordena
    images = sorted(set(images), key=lambda x: x.name.lower())

    if not images:
        print("Nenhuma imagem encontrada.")
        return 0, 0

    print(f"Encontradas {len(images)} imagens para processar:\n")

    success = 0
    failed = 0
    current_number = start_number

    # Cria diretório de saída se especificado
    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    for img_path in images:
        # Define nome de saída
        output_name = None
        if rename_prefix:
            output_name = generate_numbered_name(rename_prefix, current_number, digits)

        result = process_image(
            str(img_path),
            output_dir=output_dir,
            output_format=output_format,
            crop_ratio=crop_ratio,
            max_width=max_width,
            max_height=max_height,
            output_name=output_name
        )
        if result:
            success += 1
            current_number += 1
        else:
            failed += 1
        print()

    print(f"{'='*60}")
    print(f"Concluído: {success} sucesso, {failed} falhas")
    print(f"{'='*60}")

    return success, failed


def main():
    parser = argparse.ArgumentParser(
        description='Converte, compacta, corta e renomeia imagens para web',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python image_processor.py                     # Processa imagens no diretório atual
  python image_processor.py -i foto.heic        # Processa uma imagem específica
  python image_processor.py -d /caminho/pasta   # Processa pasta específica
  python image_processor.py -o ./output         # Salva em pasta específica
  python image_processor.py --format webp       # Usa WebP ao invés de AVIF
  python image_processor.py --crop 0.90         # Corta para 90% da altura
  python image_processor.py --max-width 1280    # Define largura máxima

Renomeação em massa:
  python image_processor.py --rename projeto              # Renomeia: projeto_001, projeto_002...
  python image_processor.py --rename foto --start 10     # Começa do 10: foto_010, foto_011...
  python image_processor.py --rename img --digits 4      # 4 dígitos: img_0001, img_0002...
  python image_processor.py --rename-only casa           # Só renomeia (não converte/compacta)
        """
    )

    parser.add_argument('-i', '--input', help='Imagem específica para processar')
    parser.add_argument('-d', '--directory', default='.', help='Diretório com imagens (padrão: atual)')
    parser.add_argument('-o', '--output', help='Diretório de saída (padrão: mesmo da entrada)')
    parser.add_argument('--format', choices=['avif', 'webp'], default='avif',
                       help='Formato de saída (padrão: avif)')
    parser.add_argument('--crop', type=float, default=0.85,
                       help='Proporção da altura a manter (padrão: 0.85 = 85%%)')
    parser.add_argument('--max-width', type=int, default=1920,
                       help='Largura máxima (padrão: 1920)')
    parser.add_argument('--max-height', type=int, default=1080,
                       help='Altura máxima (padrão: 1080)')
    parser.add_argument('--quality', type=int, help='Qualidade de compressão (0-100)')
    parser.add_argument('--no-crop', action='store_true', help='Não cortar a imagem')

    # Argumentos de renomeação
    parser.add_argument('--rename', metavar='PREFIX',
                       help='Renomeia arquivos com prefixo e numeração (ex: projeto -> projeto_001)')
    parser.add_argument('--rename-only', metavar='PREFIX',
                       help='Apenas renomeia arquivos (sem converter/compactar)')
    parser.add_argument('--start', type=int, default=1,
                       help='Número inicial para renomeação (padrão: 1)')
    parser.add_argument('--digits', type=int, default=3,
                       help='Quantidade de dígitos na numeração (padrão: 3)')

    args = parser.parse_args()

    # Define ratio de corte
    crop_ratio = 1.0 if args.no_crop else args.crop

    # Modo: apenas renomear (sem processar)
    if args.rename_only:
        success, failed = rename_files_only(
            args.directory,
            prefix=args.rename_only,
            output_dir=args.output,
            start_number=args.start,
            digits=args.digits
        )
        sys.exit(0 if failed == 0 else 1)

    # Processa imagem única
    if args.input:
        output_format, _ = get_output_format(args.format.upper() == 'AVIF')
        if args.format.upper() == 'WEBP':
            output_format = 'WEBP'

        print(f"\nProcessando: {args.input}")
        print(f"Formato: {output_format}")
        print()

        result = process_image(
            args.input,
            output_dir=args.output,
            output_format=output_format,
            crop_ratio=crop_ratio,
            max_width=args.max_width,
            max_height=args.max_height,
            quality=args.quality
        )
        sys.exit(0 if result else 1)

    # Processa diretório (com ou sem renomeação)
    success, failed = process_directory(
        args.directory,
        output_dir=args.output,
        prefer_avif=(args.format.upper() == 'AVIF'),
        crop_ratio=crop_ratio,
        max_width=args.max_width,
        max_height=args.max_height,
        rename_prefix=args.rename,
        start_number=args.start,
        digits=args.digits
    )
    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
