# Padrões de código

Estas regras valem para todo o código do repositório, no backend (Python) e no frontend (TypeScript). Quase todas são verificadas automaticamente: `make lint` local, o hook de pre-commit e a CI barram o que não estiver de acordo.

## Regras da casa

| Regra | Como fazer | Verificação |
| --- | --- | --- |
| **Sem comentários de linha** (`#`, `//`, `/* */`) | Deixe o código se explicar com nomes claros e constantes nomeadas. O que precisar de explicação vai para a docstring (Python) ou JSDoc `/** */` (TS) da função, classe ou módulo. | `STY001` · `local/no-comments` |
| **Sem `else` e sem `elif`** (inclusive `else` de `for`, `while` e `try`) | Use *guard clause* e retorno antecipado, `continue` em laços, um dicionário/mapa de casos ou uma função auxiliar. | `STY002` · `no-restricted-syntax` |
| **Sem `if` dentro de `if`** | Combine as condições (`if a and b`) ou extraia uma função com nome. Funções internas (callbacks, componentes) começam a contagem do zero. | `STY003` · `local/no-nested-if` |
| **Ternário só simples** | `x if cond else y` e `cond ? a : b` (inclusive no JSX) são permitidos; ternário dentro de ternário não. | `STY004` · `no-nested-ternary` |
| **Nada de gambiarra** | Nada de expressão solta para fugir de um `if` (`cond and f()`, `f() if c else None`), `sleep` para "dar tempo", `except Exception` genérico sem log, `type: ignore`/`eslint-disable` para calar o verificador. Se a regra atrapalha, a solução é refatorar. | revisão |

Diretivas de ferramenta são a única exceção aos comentários e só quando inevitáveis: `# noqa: CODIGO`, `# type: ignore[codigo]` e `# pragma: no cover`, sempre com o código e sem texto ao lado (a justificativa vai na docstring). No front, nenhuma diretiva é aceita.

## Arquitetura do backend

```
app/api/routers/   HTTP fino: recebe, delega a um service e devolve o schema. Sem regra de negócio, sem SQL.
app/services/      casos de uso: orquestram banco, motor e providers. Um módulo por assunto
                   (assets, portfolio, transactions, fixed_income, profile, planner, dashboard, macro, sync).
app/engine/        regras de negócio puras (método Barsi, carteira, aporte, renda fixa). Sem banco e sem rede;
                   testadas com dados em memória.
app/providers/     integração com fontes externas (BCB, Tesouro, CVM, Yahoo, brapi). Só baixam e interpretam.
app/schemas/       contrato da API (Pydantic). O front gera os tipos dele com `make types`.
app/db/            modelos SQLAlchemy, sessão e migrações (Alembic).
app/core/          configuração e erros de domínio.
tools/             verificador das regras da casa e exportação do OpenAPI.
```

- **Erros:** services levantam `NotFoundError`, `ConflictError` ou `BusinessRuleError` (`app/core/errors.py`) e não conhecem HTTP. `app/main.py` traduz para 404/409/422 com a mensagem em `detail`.
- **Dependências apontam para dentro:** routers → services → engine/providers/db. Um router nunca importa outro router; o engine não importa nada de banco, rede ou API.
- **Consultas:** carregue o que a requisição precisa uma vez (`load_portfolio`, `latest_evaluations`) em vez de consultar dentro de laços.
- **Dinheiro do usuário** (operações, aplicações) é `Decimal`; dados de mercado são `float`.

## Arquitetura do frontend

- Páginas em `src/app/`, componentes reutilizáveis em `src/components/`, utilitários puros em `src/lib/` (com testes `*.test.ts`).
- Tipos da API vêm de `src/lib/api/schema.d.ts` (gerado, não edite à mão).
- Números digitados pelo usuário passam sempre por `parseNumber`/`decimalStr` de `src/lib/format.ts`, que entendem o formato brasileiro ("1.500,50").

## Antes de abrir um PR

```bash
make format   # ruff format + prettier
make check    # lint + testes (o mesmo que a CI roda)
make types    # se mudou algum schema da API
```

Testes acompanham toda mudança de comportamento. O backend exige cobertura mínima (`fail_under` em `backend/pyproject.toml`), e a CI falha se a cobertura cair abaixo dela.

Para rodar as verificações a cada commit: `pip install pre-commit && pre-commit install` (usa `.pre-commit-config.yaml`).
