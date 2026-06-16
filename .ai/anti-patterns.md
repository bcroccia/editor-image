# Anti-patterns — não fazer

> Coisas que parecem certas mas quebram. Append ao descobrir.

## Geral

### NUNCA `any` em TypeScript
Usar `unknown` + narrow.

### NUNCA `throw new Error('string')`
Custom error class.

### NUNCA editar arquivo sem `Read` nesta sessão
Edit rejeita.

### NUNCA criar arquivo com nome genérico
Banidos: `utils.ts`, `helpers.ts`, `common.ts`, `misc.ts`, `Component.tsx` sem qualificador, `index.tsx` segurando componente.

### NUNCA explorar >3 arquivos manualmente
Spawn `Plan` ou `Explore` agent.

## Específico do projeto

<!-- Append ao descobrir -->

