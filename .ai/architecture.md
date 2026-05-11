# Architecture — editor-image

> Preencher conforme aprende. Mantém tight (<300 linhas).

## Stack

- Backend: <preencher>
- Frontend: <preencher>
- DB: <preencher>

## Layout do código

```
<árvore enxuta — só as 3 camadas que importam>
```

## Tabela de tamanho (hard ceiling 400 linhas)

| Tipo | Sweet | Aceitável | Refatorar |
|------|-------|-----------|-----------|
| Util puro | 5-30 | 30-80 | >80 |
| Hook | 30-80 | 80-150 | >150 |
| Component leaf | 30-100 | 100-200 | >200 |
| Component composto | 80-200 | 200-300 | >300 |
| Service / Repo | 80-200 | 200-300 | >300 |
| Route controller | 10-50 | 50-80 | >80 |

## Convenções não-óbvias

- <append ao descobrir>

## Onde NÃO procurar

- `__pycache__/`, `node_modules/`, `dist/`, `tmp/`, `output/`

