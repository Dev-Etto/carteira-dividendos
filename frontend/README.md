# Frontend

Telas em Next.js (App Router) com Tailwind. Elas só falam com a API em `/api`, que o Next repassa para o backend.

## Estrutura

| Pasta             | O que vai nela                                                                                                       |
| ----------------- | -------------------------------------------------------------------------------------------------------------------- |
| `src/app/`        | Uma pasta por rota (`page.tsx`). Partes grandes de uma tela ficam ao lado dela (ex.: `ativo/[ticker]/EtfParts.tsx`). |
| `src/components/` | Componentes usados por mais de uma tela. `ui.tsx` reúne os básicos.                                                  |
| `src/lib/`        | Funções puras e hooks: formatação, links, séries de gráfico, `useApi`. Cada arquivo puro tem seu `*.test.ts`.        |
| `src/lib/api/`    | Cliente da API e `schema.d.ts`, gerado do OpenAPI (`make types`). Não edite o gerado.                                |
| `src/content/`    | Textos longos, como o glossário.                                                                                     |

## Padrões

- **Componentes de `ui.tsx` primeiro:** `PageHeader`, `Card`, `Stat`, `VerdictBadge`, `ScorePill`, `Button`, `Field` (com `error`), `FieldRow`, `inputCls`, `Loading`, `ErrorBox`, `Empty`, `Help`. Uma tela nova se monta com eles antes de criar estilo próprio. `FieldRow` é o `Field` em linha, para listas de ajustes: rótulo e descrição à esquerda, campo numa coluna fixa à direita (todos alinhados) e um `footer` opcional embaixo do campo, fora do `<label>`, para ações como "Restaurar padrão".
- **Telas com seções:** a seção ativa fica na URL (`/config?secao=regras&grupo=fii`), lida com `useSearchParams` dentro de um `<Suspense>` e trocada por `<Link replace scroll={false}>`. As seções ficam todas montadas e só a ativa aparece (`hidden`), para trocar de seção sem perder o que foi digitado. Formulários de ajustes terminam numa barra de salvar (`SaveBar` em `app/config/parts.tsx`) que mostra as alterações não salvas e oferece "Descartar".
- **Cores só por token:** as cores e sombras ficam em `src/app/globals.css` (`bg`, `surface`, `ink`, `muted`, `accent`, `good`, `warn`, `bad`…). Use as classes do token (`text-muted`, `bg-accent-soft`), nunca um hexadecimal no componente. O app é só no tema claro.
- **Dados da API:** `useApi<T>(caminho)` para ler, com `loading`, `error` e `reload`; `api.post`/`api.put` para gravar. Os tipos vêm de `src/lib/api/client.ts`, que dá nomes curtos aos do `schema.d.ts`.
- **Números digitados** passam por `parseNumber` e `decimalStr` (`src/lib/format.ts`), que entendem "1.500,50". Para mostrar, use `brl`, `pct`, `num` e `dateBr`.
- **Campos de formulário** usam os inputs de `src/components/inputs.tsx`, nunca um `<input>` cru com `inputCls` para números, tickers ou datas. Cada um aplica a máscara de `src/lib/masks.ts` ao digitar e já traz o `inputMode` certo; o estado continua sendo o texto digitado (não se perde "12," no meio da digitação) e só vira número no envio.

  | Componente     | Quando usar                                           | Máscara                                     | Validação (`src/lib/validation.ts`) |
  | -------------- | ----------------------------------------------------- | ------------------------------------------- | ----------------------------------- |
  | `MoneyInput`   | Valores em R$ (preço, aporte, saldo, liquidez)        | dígitos, pontos de milhar, vírgula, 2 casas | `checkMoney`                        |
  | `PercentInput` | Percentuais digitados de 0 a 100 (taxa, divisão-alvo) | como moeda, com até 4 casas e sem o "%"     | `checkPercent` (com `max`)          |
  | `DecimalInput` | Números sem unidade com casas (P/VP, Dívida/EBITDA)   | como moeda, com `decimals` casas (4)        | `checkDecimal`                      |
  | `IntegerInput` | Quantidade de cotas, prazo em dias, anos, nota        | só dígitos                                  | `checkInteger`                      |
  | `TickerInput`  | Código de negociação da B3                            | maiúsculas, letras e dígitos, até 6         | `checkTicker` (PETR4, HGLG11)       |
  | `DateInput`    | Datas (seletor nativo, AAAA-MM-DD)                    | —                                           | `checkDate` (com `min`/`max`)       |

  Todos recebem `value` e `onValueChange(texto)`, e aceitam as demais props de `<input>` (inclusive `ref`). As funções `check*` devolvem `{ value, error }`: vazio não é erro (`value: null`), e `canSubmit(obrigatórios, opcionais)` diz se o botão de enviar pode ser habilitado. Passe o `error` para o `Field`: a mensagem aparece embaixo do campo depois que o usuário sai dele, e o input ganha `aria-invalid`, borda vermelha e `aria-describedby`. O botão fica desabilitado enquanto houver erro.

- **Termo novo na tela** ganha um verbete em `src/content/glossario.ts` e um `<Help slug="…" />` ao lado.
- **Efeitos:** não chame `setState` direto dentro de `useEffect`; derive o valor na renderização ou atualize na resposta da requisição (o lint barra).

## Comandos

```bash
npm run dev        # http://localhost:3000, espera a API em http://localhost:8000
npm run lint       # ESLint, incluindo as regras da casa (sem comentários, sem else, sem if aninhado)
npm run typecheck
npm test           # Vitest
```
