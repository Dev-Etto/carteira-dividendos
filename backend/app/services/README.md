# Casos de uso (`app/services`)

Cada módulo cuida de um assunto e é o único lugar onde banco, motor e providers se encontram. Os routers chamam funções daqui; os services não conhecem HTTP.

| Módulo | Assunto |
| --- | --- |
| `sync.py` | Atualização de dados em etapas (ver abaixo). |
| `snapshot.py` | Monta, a partir do banco, os snapshots que o motor avalia. |
| `evaluation.py` | Roda o motor, grava as avaliações e lê a que vale para o usuário. |
| `methods.py` | Lista as metodologias e guarda a escolha do usuário. |
| `assets.py` | Lista, ficha, histórico, cadastro e favoritos de ativos. |
| `portfolio.py`, `transactions.py` | Posição da carteira e operações de compra e venda. |
| `fixed_income.py` | Aplicações de renda fixa e reserva de emergência. |
| `profile.py` | Questionário, perfil, divisão-alvo e limites das regras. |
| `planner.py` | Plano do aporte do mês. |
| `dashboard.py`, `macro.py` | Painel inicial e indicadores do Banco Central. |
| `upsert.py` | Inserção ou atualização em lote, usada por todas as gravações. |

## Atualização de dados

`sync.py` roda as etapas em ordem: `universo`, `macro`, `tesouro`, `cvm`, `itr`, `bancos`, `fiis`, `etfs`, `mercado`, `avaliacoes`. Cada etapa é independente: uma falha é registrada em `sync_runs` e as seguintes continuam. `make sync ETAPAS=macro,mercado` roda só algumas.

Para criar uma etapa, escreva a função que grava os dados, inclua o nome em `STEPS` e a função no mapa de etapas. A etapa precisa poder rodar de novo sem duplicar nada, por isso use `upsert`.

## Avaliações

- **Ações** têm uma avaliação por metodologia de seleção registrada, todas calculadas na etapa `avaliacoes`. Reavaliar uma ação reavalia o lote, porque métodos de ranking comparam as ações entre si.
- **FIIs e ETFs** têm um motor só; a avaliação deles é gravada com a própria classe (`fii`, `etf`) no lugar do método.
- `latest_evaluations` devolve, numa consulta só, a avaliação mais recente de cada ativo na metodologia escolhida. Use-a em qualquer tela que mostre nota ou veredito, e nunca filtre `Evaluation` à mão.
