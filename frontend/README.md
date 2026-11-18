# Frontend

Telas em Next.js (App Router) com Tailwind. Elas só falam com a API em `/api`, que o Next repassa para o backend.

## Estrutura

| Pasta | O que vai nela |
| --- | --- |
| `src/app/` | Uma pasta por rota (`page.tsx`). Partes grandes de uma tela ficam ao lado dela (ex.: `ativo/[ticker]/EtfParts.tsx`). |
| `src/components/` | Componentes usados por mais de uma tela. `ui.tsx` reúne os básicos. |
| `src/lib/` | Funções puras e hooks: formatação, links, séries de gráfico, `useApi`. Cada arquivo puro tem seu `*.test.ts`. |
| `src/lib/api/` | Cliente da API e `schema.d.ts`, gerado do OpenAPI (`make types`). Não edite o gerado. |
| `src/content/` | Textos longos, como o glossário. |

## Padrões

- **Componentes de `ui.tsx` primeiro:** `PageHeader`, `Card`, `Stat`, `VerdictBadge`, `ScorePill`, `Button`, `Field`, `inputCls`, `Loading`, `ErrorBox`, `Empty`, `Help`. Uma tela nova se monta com eles antes de criar estilo próprio.
- **Cores só por token:** as cores e sombras ficam em `src/app/globals.css` (`bg`, `surface`, `ink`, `muted`, `accent`, `good`, `warn`, `bad`…). Use as classes do token (`text-muted`, `bg-accent-soft`), nunca um hexadecimal no componente. O app é só no tema claro.
- **Dados da API:** `useApi<T>(caminho)` para ler, com `loading`, `error` e `reload`; `api.post`/`api.put` para gravar. Os tipos vêm de `src/lib/api/client.ts`, que dá nomes curtos aos do `schema.d.ts`.
- **Números digitados** passam por `parseNumber` e `decimalStr` (`src/lib/format.ts`), que entendem "1.500,50". Para mostrar, use `brl`, `pct`, `num` e `dateBr`.
- **Termo novo na tela** ganha um verbete em `src/content/glossario.ts` e um `<Help slug="…" />` ao lado.
- **Efeitos:** não chame `setState` direto dentro de `useEffect`; derive o valor na renderização ou atualize na resposta da requisição (o lint barra).

## Comandos

```bash
npm run dev        # http://localhost:3000, espera a API em http://localhost:8000
npm run lint       # ESLint, incluindo as regras da casa (sem comentários, sem else, sem if aninhado)
npm run typecheck
npm test           # Vitest
```
