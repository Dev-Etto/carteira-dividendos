# Carteira de Dividendos

Assistente local para montar e manter uma carteira focada em dividendos pelo **método Barsi**. Ele avalia ações por regras explícitas, explica cada nota em linguagem simples, cuida da reserva de emergência e diz onde colocar o aporte do mês.

> O app aplica regras e explica o resultado. **Não é recomendação de investimento**: a decisão é sua.

## Como rodar (macOS)

Pré-requisitos: [uv](https://docs.astral.sh/uv/) (`brew install uv`) e Node 22+.

```bash
make setup     # instala dependências e cria backend/.env e frontend/.env.local
make sync      # primeira carga de dados (alguns minutos)
make dev       # API em http://localhost:8000/docs e telas em http://localhost:3000
```

Depois disso, a API atualiza os dados sozinha todo dia às 19h enquanto estiver rodando. Você também pode atualizar pela tela **Configurações**.

**Token da brapi (opcional):** crie um token gratuito em [brapi.dev](https://brapi.dev) e coloque em `backend/.env` (`BRAPI_TOKEN=...`) para cotações mais frescas. Sem ele, o app usa o fechamento diário do Yahoo Finance.

## O que já funciona (Fase 1)

| Tela | O que faz |
| --- | --- |
| Onboarding | Questionário de perfil, reserva de emergência (6 a 12 meses de gastos) e divisão-alvo da carteira |
| Início | Próximo passo recomendado, reserva, renda passiva × meta, divisão atual × alvo, oportunidades, Selic/CDI/IPCA |
| Explorar | Ranking das ações com nota, veredito, preço-teto e margem; adicionar novas ações |
| Ficha do ativo | Checklist de regras (✓ ! ✕) com explicação, preço-teto, Bazin, Graham, gráficos, riscos e fonte de cada dado |
| Carteira | Posições, preço médio, resultado, yield on cost, alertas de concentração, operações |
| Aporte do mês | Plano de compras: reserva → classes abaixo do alvo → melhores ações; registra as compras |
| Renda fixa | Reserva de emergência, aplicações, comparador isento × tributado, taxas do Tesouro Direto |
| Aprender | Glossário com tudo o que aparece no app e trilha "Comece aqui" |
| Configurações | Atualização de dados, perfil, divisão-alvo e limites das regras |

FIIs e ETFs entram na Fase 2. Até lá, a parte do aporte destinada a eles fica em Tesouro Selic, identificada no plano.

## Como as ações são avaliadas

Regras do método Barsi + regras setoriais + sustentabilidade do dividendo. Cada regra tem peso e pode ser **eliminatória**:

- **Qualidade:** setor perene (BESST), histórico de proventos (eliminatória, ≥ 10 anos ideal / 5 mínimo), consistência, lucro, ROE médio 5 anos, endividamento, payout, liquidez (eliminatória)
- **Setor:** Basileia e inadimplência (bancos), índice combinado (seguros), segmento e concessões (energia e saneamento), limite de dívida maior para setores regulados
- **Sustentabilidade:** fluxo de caixa livre × proventos, provento pago com dívida
- **Preço:** preço-teto Barsi (média de proventos de 5 anos ÷ 6%), DY fora do normal, barato em relação ao próprio histórico

Nota = soma ponderada (✓ = 1, ! = 0,5, ✕ = 0) sobre as regras com dado. **Comprar**: nota ≥ 70 e preço abaixo do teto. **Aguardar**: nota ≥ 70 e preço acima do teto. **Evitar**: nota < 50 ou eliminatória reprovada. Todos os limites são editáveis em Configurações.

Indicadores setoriais (Basileia, inadimplência, índice combinado, vencimento de concessões) ainda são cadastrados à mão em `backend/app/data/sector_metrics.csv`. Formato (valores ilustrativos, confira no RI de cada empresa):

```csv
ticker,chave,valor,referencia,fonte
ITUB4,basileia,14.2,3T26,RI do banco
ITUB4,inadimplencia,2.1,3T26,RI do banco
ITUB4,inadimplencia_sistema,3.4,3T26,BCB
BBSE3,indice_combinado,72,3T26,RI
TAEE11,concessao_anos,18,2026,manual
```

Enquanto não estiverem cadastrados, essas regras aparecem como "sem dado" e não entram na nota.

## De onde vêm os dados

| Dado | Fonte |
| --- | --- |
| Selic, CDI, IPCA 12m | Banco Central, API SGS (séries 432, 4389, 13522) |
| Tesouro Direto | Tesouro Transparente, CSV de preços e taxas |
| Balanços (DRE, BP, DFC, DVA) | CVM Dados Abertos, DFP anual |
| CNPJ ↔ ticker | CVM, FCA (valores mobiliários) |
| Preços, proventos, desdobramentos | Yahoo Finance via `yfinance` (não oficial) |
| Cotação do dia | brapi (plano gratuito, opcional) |

Ações do universo inicial ficam em `backend/app/data/universo.csv` e podem ser adicionadas pela tela Explorar.

## Estrutura

```
backend/            FastAPI + SQLAlchemy + Alembic (SQLite em backend/data/)
  app/api/routers/  endpoints REST finos (documentação em /docs)
  app/services/     casos de uso: ativos, carteira, operações, renda fixa, perfil, aporte, painel, sync
  app/engine/       motor de regras puro (ações, renda fixa, carteira, aporte, perfil)
  app/providers/    coletores: bcb, tesouro, cvm, market (brapi + Yahoo)
  app/core/         configuração e erros de domínio
  tools/            verificador das regras da casa e exportação do OpenAPI
  tests/            pytest: motor, carteira, aporte, renda fixa, parsers, sync, API e regras da casa
frontend/           Next.js + Tailwind + Recharts; tipos gerados do OpenAPI (make types); testes com Vitest
```

## Desenvolvimento

```bash
make check    # lint + testes, o mesmo que a CI roda
make lint     # ruff, mypy e regras da casa (back); eslint, tsc e prettier (front)
make test     # pytest com cobertura mínima (back) e vitest (front)
make format   # aplica ruff format e prettier
make types    # regenera os tipos do front após mudar schemas da API
```

Os padrões de código (sem comentários de linha, sem `else`/`elif`, sem `if` aninhado) e a arquitetura estão em [CONTRIBUTING.md](CONTRIBUTING.md).
