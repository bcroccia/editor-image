#!/bin/bash
# Script de setup para o processador de imagens

echo "Criando ambiente virtual..."
python3 -m venv venv

echo "Ativando ambiente virtual..."
source venv/bin/activate

echo "Instalando dependências..."
pip install --upgrade pip
pip install Pillow pillow-heif

echo ""
echo "Setup completo!"
echo ""
echo "Para usar o processador de imagens:"
echo "  1. Ative o ambiente: source venv/bin/activate"
echo "  2. Execute: python image_processor.py --help"
echo ""
echo "Exemplos:"
echo "  python image_processor.py -d ./images                    # Processa todas imagens"
echo "  python image_processor.py -i ./images/foto.heic          # Processa uma imagem"
echo "  python image_processor.py -d ./images -o ./output        # Salva em pasta output"
echo "  python image_processor.py -d ./images --format webp      # Usa WebP ao invés de AVIF"
