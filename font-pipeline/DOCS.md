# OkiDoki Font — Documentação do Pipeline

## O que foi feito

Partindo de arquivos SVG exportados pelo Affinity Designer (que continham imagens PNG embutidas em base64, não vetores reais), foi construído um pipeline completo para gerar uma fonte TTF utilizável no Mac e em páginas web.

---

## Estrutura de arquivos

```
fontforge/
├── font_test/              # Batch 1 — maiúsculas + dígitos
│   ├── slice1.svg … slice35.svg
│   ├── renamed/            # SVGs renomeados pelo caractere
│   ├── vector_svg/         # SVGs vetoriais gerados por potrace
│   ├── OkiDoki.sfd         # Fonte fonte (FontForge source)
│   ├── OkiDoki.ttf         # Fonte final gerada
│   ├── create_font.py      # Primeira tentativa (falhou — veja problemas)
│   └── create_font2.py     # Script funcional para font_test
│
├── font_2/                 # Batch 2 — minúsculas + dígitos estilo decorativo
│   ├── slice1.svg … slice42.svg  (slice19 ausente)
│   └── _auto_work/         # Gerado automaticamente
│       ├── pngs/           # PNGs extraídos dos SVGs
│       ├── vectors/        # SVGs vetoriais gerados por potrace
│       └── mapping.json    # Mapeamento slice → caractere salvo
│
├── font2_pngs/             # PNGs do batch 2 (intermediário)
├── font2_vectors/          # Vetores do batch 2 (intermediário)
├── add_font2.py            # Script específico para adicionar font_2
├── auto_font.py            # Script automatizado (uso geral)
└── DOCS.md                 # Este arquivo
```

---

## Problemas encontrados e como foram resolvidos

### 1. SVGs não são vetores

Os arquivos exportados pelo Affinity Designer continham **imagens PNG embutidas em base64** dentro de uma tag `<image>`, não paths vetoriais. O FontForge não consegue importar esses arquivos diretamente.

**Solução:** extrair o PNG embutido e vetorizar com potrace.

```
SVG (base64 PNG) → PNG → PBM → SVG vetorial → FontForge
```

---

### 2. potrace traçando o fundo em vez da letra

Na primeira tentativa foi usado `-negate` no ImageMagick antes de passar para o potrace. Isso **inverteu** a imagem: o fundo branco virou preto, e o potrace traçou o fundo em vez da letra.

**Causa:** o potrace trata pixels **pretos como foreground** (forma). As imagens originais têm fundo transparente e letra preta — ao remover a transparência, a letra fica preta sobre branco, que é exatamente o que o potrace espera. O `-negate` quebrava isso.

**Solução:** remover o `-negate`. Pipeline correto:

```bash
magick input.png \
  -background white -alpha remove -alpha off \
  -threshold 50% \
  output.pbm
```

---

### 3. `fontforge.unitScale` não existe

A primeira versão do script usava `fontforge.unitScale` para escalar os glifos, mas essa função não existe na versão instalada via Homebrew.

**Solução:** usar a transformação por matriz afim diretamente:

```python
# Errado:
# fontforge.unitScale(scale)

# Correto:
glyph.transform((scale, 0, 0, scale, 0, 0))
```

---

### 4. Identificação manual dos caracteres

Como os SVGs tinham nomes genéricos (`slice1.svg`, `slice2.svg`...), foi necessário identificar visualmente cada caractere extraindo os PNGs e visualizando um por um.

**font_test (35 glifos):** A B C D E F G H J K L M N P Q R S T U V W X Y Z + 0-9 + d minúsculo

**font_2 (35 glifos únicos de 42 SVGs):** a-z completo + 1-9 (7 slices eram duplicatas)

Duplicatas encontradas no font_2:
- `e` → slice17 e slice23
- `s` → slice24 e slice30
- `r` → slice34 e slice35
- `o` → slice13, slice37 e slice41
- `l` → slice40 e slice42
- `1` → slice39 (já existia no font_test)

---

## Fonte final

**Arquivo:** `font_test/OkiDoki.ttf`
**Instalada em:** `~/Library/Fonts/OkiDoki.ttf`

**60 glifos:**
```
0123456789
ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz
```

> Nota: `I` e `O` maiúsculos estavam ausentes no batch original (font_test).

**Métricas:**
- EM = 1000
- Ascent = 800, Descent = 200
- Side bearing = 30 unidades

---

## Script automatizado: `auto_font.py`

Para batches futuros, basta rodar:

```bash
python3 auto_font.py <pasta_com_slices>/
```

### Dependências

```bash
brew install tesseract potrace imagemagick fontforge
pip3 install pytesseract Pillow anthropic
```

### Configuração da API key

Crie o arquivo `.env` na mesma pasta do script:

```
ANTHROPIC_API_KEY=sk-ant-SEU_KEY_AQUI
```

Ou passe na linha de comando:

```bash
python3 auto_font.py font_3/ --api-key sk-ant-SEU_KEY_AQUI
```

### Opções

| Argumento | Descrição |
|-----------|-----------|
| `input_dir` | Pasta com os arquivos `slice*.svg` |
| `--font` | Caminho para `.sfd` existente (padrão: usa `font_test/OkiDoki.sfd`) |
| `--output` | Caminho do TTF de saída |
| `--mapping` | JSON com mapeamento manual para pular identificação |
| `--api-key` | Anthropic API key |

### Como funciona a identificação híbrida

```
Para cada slice*.svg:
  1. Extrai o PNG embutido em base64
  2. Tesseract OCR tenta identificar o caractere
     ├─ confiança ≥ 80% → usa resultado do OCR
     └─ confiança < 80% → chama Claude Vision API
         ├─ OCR e Claude concordam → usa o resultado
         ├─ só Claude respondeu → usa Claude
         ├─ discordam → mostra ambos, pede confirmação manual
         └─ sem API key → pede input manual direto
  3. Deduplica: ignora slices com caractere já mapeado
```

> **Nota:** Tesseract tem desempenho fraco com fontes muito decorativas (como OkiDoki). Na prática, Claude Vision será o motor principal na maioria dos casos.

### Reuso do mapeamento

Após a primeira execução, o mapeamento é salvo em:
```
<pasta>/_auto_work/mapping.json
```

Para re-executar sem repetir a identificação:
```bash
python3 auto_font.py font_2/ --mapping font_2/_auto_work/mapping.json
```

---

## Uso da fonte em páginas web

```css
@font-face {
  font-family: 'OkiDoki';
  src: url('OkiDoki.ttf') format('truetype');
}

h1 {
  font-family: 'OkiDoki', sans-serif;
}
```

---

## Melhorias futuras

### Qualidade dos glifos

- **Kerning automático:** ajustar o espaço entre pares de letras específicos (ex: AV, To, Va) para melhorar a aparência do texto
- **Métricas por categoria:** letras com descenders (g, j, p, q, y) deveriam usar o espaço abaixo da baseline — atualmente todos os glifos são escalados para a altura do ascent, ignorando descenders
- **Hinting:** adicionar instruções de hinting para melhorar a renderização em tamanhos pequenos
- **Ligatures:** adicionar ligaduras para pares comuns como `fi`, `fl`, `ff`

### Pipeline de vetorização

- **Potrace com mais suavização:** o flag `--alphamax` e `--opttolerance` podem ser ajustados por tipo de caractere para curvas mais suaves
- **Múltiplas resoluções:** vetorizar o PNG em resolução maior antes do potrace reduz ruído nas bordas
- **Limpeza de artefatos:** alguns glifos podem ter pontos isolados ou caminhos pequenos; um passo de filtragem por tamanho mínimo de path removeria ruídos

### Identificação de caracteres

- **Few-shot no prompt do Claude:** enviar 2-3 exemplos já identificados do mesmo batch melhora a acurácia em fontes muito estilizadas
- **Cache de resultados:** evitar chamadas repetidas à API se o PNG não mudou (comparar hash do arquivo)
- **Suporte a símbolos:** atualmente o pipeline foca em letras e dígitos; adicionar suporte a pontuação e caracteres especiais

### Script e UX

- **Preview no terminal:** mostrar uma versão ASCII da imagem no terminal ao pedir input manual
- **Modo dry-run:** `--dry-run` para identificar e mapear sem gerar a fonte
- **Watch mode:** monitorar uma pasta e regenerar a fonte automaticamente ao detectar novos SVGs
- **Suporte a WOFF/WOFF2:** gerar automaticamente os formatos web além do TTF
