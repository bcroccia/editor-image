# .ai/ — Conhecimento do projeto para LLM

Docs escritos para o agente trabalhar mais rápido. Lê isso ANTES de tarefa complexa.

## Índice

| Doc | Quando ler |
|-----|------------|
| [architecture.md](architecture.md) | Vai mexer em estrutura, criar arquivo novo, ou não sabe onde algo mora |
| [data-flow.md](data-flow.md) | Bug ou feature em fluxo crítico |
| [bugs.md](bugs.md) | SEMPRE no início (10 seg). Bug recorrente? Já tem causa raiz aqui |
| [anti-patterns.md](anti-patterns.md) | Antes de editar — checar se a 'solução óbvia' já foi tentada e quebra |
| [debug-playbook.md](debug-playbook.md) | Sintoma estranho? Receita de 'se X então cheque Y' |

## Hábito obrigatório

1. **Resolveu bug não-trivial** → append em `bugs.md` (sintoma + causa raiz + commit + arquivos)
2. **Descobriu anti-padrão** → append em `anti-patterns.md`
3. **Mudou fluxo de dados** → atualizar `data-flow.md`
4. **Criou skill/script** → mencionar em `debug-playbook.md`

Doc desatualizado = pior que ausente. Mantém ou apaga.

## Não confundir com

- `.codesight/CODESIGHT.md` → autogen (rotas, libs, deps)
- `~/.claude/projects/.../memory/` → memória GLOBAL da Brunna (perfil, stacks remotas)
- `CLAUDE.md` (raiz) → regras do agente p/ este projeto (não duplicar)

