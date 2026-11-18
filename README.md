# Carteira de Dividendos

Assistente **local e de código aberto** para montar e manter uma carteira de renda passiva com dividendos, seguindo metodologias conhecidas de investidores brasileiros e estrangeiros, com o **método Barsi** como padrão. Ele avalia ações por regras explícitas, explica cada nota em português simples, cuida da reserva de emergência e diz onde colocar o aporte do mês.

> O app aplica regras e mostra o porquê de cada resultado. **Não é recomendação de investimento**: a decisão é sempre sua.

## Propósito

Investir para viver de dividendos é simples de explicar e difícil de manter: comprar boas pagadoras de proventos, a preço justo, todo mês, sem se deixar levar pelo humor do mercado. Na prática, isso exige olhar balanços, calcular preço-teto, acompanhar a reserva e decidir para onde vai cada aporte.

Este projeto existe para tirar esse trabalho braçal do caminho sem tirar o entendimento. Ele foi pensado para quem está começando e quer aprender o método enquanto aplica, e para quem já investe e quer disciplina e transparência no processo.

## Abordagem

- **Regras explícitas, não caixa-preta.** Cada ação passa por um checklist (✓ ok, ! atenção, ✕ reprovada). A nota é a soma ponderada dessas regras, e cada linha diz qual dado foi usado, de onde veio e por que passou ou não.
- **Metodologias que você escolhe.** O método Barsi é o padrão, e a arquitetura recebe outras (Bazin, Graham, Fórmula Mágica, ARCA) sem mexer no resto do app. Veja [Metodologias](#metodologias).
- **Método Barsi como base.** Setores perenes BEST (bancos, energia, seguros, saneamento, telecom), longo histórico de proventos, lucro consistente, dívida controlada e compra só abaixo do preço-teto. Em cima disso entram regras por setor e a sustentabilidade do dividendo.
- **Você no controle.** Todos os limites (yield-alvo, ROE mínimo, dívida máxima, notas de corte) são editáveis na tela de Configurações.
- **Reserva primeiro.** O plano de aporte completa a reserva de emergência antes de qualquer ação, depois equilibra as classes abaixo da divisão-alvo e só então escolhe as melhores ações.
- **Local e privado.** Tudo roda na sua máquina, num SQLite. Não há conta, nuvem nem envio da sua carteira para lugar nenhum.
- **Dados públicos.** Banco Central, Tesouro Transparente, CVM e Yahoo Finance; nenhuma assinatura obrigatória.

## Como funciona

```
 fontes públicas              API (FastAPI)                         telas (Next.js)
┌──────────────────┐   ┌──────────────────────────────────┐   ┌──────────────────────┐
│ Banco Central    │   │ providers  baixam e interpretam  │   │ Início   Explorar    │
│ Tesouro Direto   │──▶│ sync       grava no SQLite       │──▶│ Ficha    Carteira    │
│ CVM (DFP e FIIs) │   │ engine     regras ações e FIIs   │   │ Aporte   Renda fixa  │
│ Yahoo / brapi    │   │ services   casos de uso + API    │   │ Aprender Config.     │
└──────────────────┘   └──────────────────────────────────┘   └──────────────────────┘
```

1. **Coleta:** a API baixa os dados ao subir pela primeira vez e depois todo dia às 19h (ou quando você pede, em Configurações).
2. **Avaliação:** o motor de regras recalcula nota, veredito e preço-teto de cada ação a cada atualização.
3. **Uso:** no onboarding você responde um questionário de perfil; o app sugere a divisão-alvo e o tamanho da reserva. A partir daí, a cada mês, informa quanto vai aportar e recebe um plano de compras, que registra na carteira com um clique depois de executar na corretora.

## Como rodar

O único requisito é o [Docker](https://docs.docker.com/get-docker/) (Docker Desktop no macOS e no Windows).

```bash
git clone https://github.com/Dev-Etto/carteira-dividendos.git
cd carteira-dividendos
docker compose up -d --build
```

Pronto:

- **Telas:** http://localhost:3000
- **API e documentação:** http://localhost:8000/docs

Na primeira vez, a API baixa todos os dados sozinha. Isso leva alguns minutos; o andamento aparece em **Configurações**. Os dados ficam num volume do Docker e sobrevivem a `docker compose down` e a atualizações da imagem.

| Comando                                       | O que faz                                            |
| --------------------------------------------- | ---------------------------------------------------- |
| `docker compose up -d --build` (ou `make up`) | sobe ou atualiza API e telas                         |
| `docker compose down` (ou `make down`)        | para tudo, mantendo os dados                         |
| `docker compose logs -f` (ou `make logs`)     | acompanha os logs                                    |
| `docker compose down -v`                      | para tudo e **apaga** os dados, para começar do zero |

**Configuração opcional:** crie um arquivo `.env` na raiz do projeto.

```env
BRAPI_TOKEN=seu_token   # token gratuito de https://brapi.dev para cotações mais frescas (sem ele, usa o fechamento do Yahoo)
SYNC_HOUR=19            # hora da atualização automática diária
CVM_YEARS=6             # anos de balanços da CVM a baixar
```

## Telas

| Tela           | O que faz                                                                                                                                              |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Onboarding     | Questionário de perfil, reserva de emergência (6 a 12 meses de gastos) e divisão-alvo da carteira                                                      |
| Início         | Próximo passo recomendado, reserva, renda passiva × meta, divisão atual × alvo, oportunidades, Selic/CDI/IPCA                                          |
| Explorar       | Ranking de ações e de FIIs com nota, veredito, preço-teto (ou preço máximo pelo P/VP) e margem; ETFs com checklist e favoritos; adicionar novos ativos |
| Ficha do ativo | Checklist de regras com explicação, preço-teto, Bazin, Graham, gráficos, riscos e fonte de cada dado                                                   |
| Carteira       | Posições, preço médio, resultado, yield on cost, alertas de concentração e histórico de operações editável                                             |
| Aporte do mês  | Plano de compras: reserva → classes abaixo do alvo → melhores ações e FIIs e ETFs favoritos; registra compras e aplicações de uma vez                  |
| Renda fixa     | Reserva de emergência, aplicações, comparador isento × tributado e taxas do Tesouro Direto                                                             |
| Aprender       | Glossário com tudo o que aparece no app e a trilha "Comece aqui"                                                                                       |
| Configurações  | Atualização de dados, perfil, divisão-alvo e limites das regras                                                                                        |

## Metodologias

Uma metodologia é um jeito de investir com nome e autor. O app separa dois tipos:

- **Seleção** escolhe as ações. O app avalia cada ação por todas as metodologias a cada atualização e mostra o veredito da que você escolheu; a ficha da ação mostra os vereditos nas outras, para comparar.
- **Divisão** define quanto vai para cada classe (renda fixa, ações, FIIs, ETFs). Trocar a divisão troca a divisão-alvo pela sugerida pela metodologia.

A escolha fica em Configurações e muda vereditos, recomendações e o plano de aporte. O app nunca sugere vender para rebalancear: o equilíbrio vem pelos aportes.

| Metodologia                           | Tipo    | Situação           |
| ------------------------------------- | ------- | ------------------ |
| Barsi (Luiz Barsi Filho)              | seleção | disponível, padrão |
| Perfil de risco (questionário do app) | divisão | disponível, padrão |
| Bazin (Décio Bazin)                   | seleção | disponível         |
| Graham (Benjamin Graham)              | seleção | disponível         |
| Fórmula Mágica (Joel Greenblatt)      | seleção | disponível         |
| ARCA (Thiago Nigro)                   | divisão | disponível         |

Como criar uma metodologia nova está em [`backend/app/engine/README.md`](backend/app/engine/README.md#metodologias-metodos).

## Como as ações são avaliadas pelo método Barsi

Regras do método Barsi, regras setoriais e sustentabilidade do dividendo. Cada regra tem peso e pode ser **eliminatória**:

- **Qualidade:** setor perene, histórico de proventos (eliminatória; 10 anos ideal, 5 no mínimo), consistência, lucro, ROE médio de 5 anos, endividamento, payout e liquidez (eliminatória)
- **Setor:** Basileia e inadimplência (bancos), índice combinado (seguros), segmento e concessões (energia e saneamento), limite de dívida maior para setores regulados
- **Sustentabilidade:** fluxo de caixa livre × proventos, provento pago com dívida
- **Preço:** preço-teto Barsi (média de proventos de 5 anos ÷ yield-alvo de 6%), DY fora do normal, preço em relação ao próprio histórico

**Nota** = soma ponderada (✓ = 1, ! = 0,5, ✕ = 0) sobre as regras que têm dado. **Comprar:** nota alta e preço abaixo do teto. **Aguardar:** nota alta e preço acima do teto. **Evitar:** nota baixa ou eliminatória reprovada. As notas de corte (70 e 50 por padrão) e os demais limites são editáveis em Configurações.

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

## Como as ações são avaliadas pelo método Bazin

Décio Bazin (_Faça Fortuna com Ações_, 1992) olhava poucos números:

- **Dividend yield dos últimos 12 meses ≥ 6%.** Decide entre comprar e aguardar, sem mexer na nota. O preço-teto é proventos de 12 meses ÷ 6%.
- **Pagou proventos em cada um dos últimos 3 anos** (eliminatória).
- **Dívida líquida ÷ patrimônio ≤ 1.** O livro só diz "dívida moderada"; a medida é escolha do app. Bancos e seguradoras ficam de fora desta regra.
- **Liquidez** (eliminatória), como em todo o app.
- **Yield abaixo de 4%** aparece como aviso: era quando o Bazin vendia. O app nunca sugere vender.

Todos os limites ficam em Configurações, na seção "Ações pelo Bazin".

## Como as ações são avaliadas pelo método Graham

Os critérios do investidor defensivo de Benjamin Graham (_O Investidor Inteligente_, cap. 14), com a adaptação ao Brasil do [estudo da USP de Palazzo et al. (2018)](http://revistas.usp.br/rcf/article/download/150635/147416/312645):

| Critério            | Livro (EUA, 1972)                         | No app                                                        |
| ------------------- | ----------------------------------------- | ------------------------------------------------------------- |
| Tamanho             | receita ≥ US$ 100 mi                      | receita > R$ 300 mi                                           |
| Condição financeira | ativo circulante ≥ 2 × passivo circulante | liquidez corrente ≥ 1,22 (bancos e seguradoras ficam de fora) |
| Lucro               | em cada um dos 10 anos                    | em cada um dos 5 anos (eliminatória)                          |
| Proventos           | 20 anos sem interrupção                   | 5 anos sem interrupção                                        |
| Crescimento         | lucro por ação +1/3 em 10 anos            | lucro +2,66% ao ano (média dos 3 primeiros × 3 últimos anos)  |
| P/L                 | ≤ 15 × lucro médio de 3 anos              | ≤ 1 ÷ juro real do Tesouro IPCA+, ou 15 fixo                  |
| P/L × P/VP          | ≤ 22,5                                    | ≤ 22,5                                                        |

Os dois critérios de preço decidem entre comprar e aguardar, sem mexer na nota. O preço-teto é o valor de Graham, √(22,5 × LPA × VPA). Os limites ficam em Configurações, na seção "Ações pelo Graham".

## Como as ações entram na Fórmula Mágica

Joel Greenblatt (_The Little Book That Beats the Market_, 2005) não avalia cada ação sozinha: ele monta um ranking.

1. Ficam de fora bancos, seguradoras, energia e saneamento, como no livro, e as ações que reprovam em liquidez.
2. Cada ação recebe duas posições: **earnings yield** (EBIT ÷ valor de mercado + dívida líquida) e **retorno sobre o capital** (EBIT ÷ capital de giro líquido + imobilizado), com os números do último balanço.
3. A soma das posições dá o ranking. O primeiro terço recebe "comprar"; o resto fica "neutro". Não há "evitar".

O método busca valorização e ignora dividendos, e o livro manda trocar a carteira a cada ano; o app só avisa, nunca sugere vender. Como quase todas as ações do BEST ficam de fora, o universo inclui também ações líquidas de outros setores.

## Como a carteira se divide pelo ARCA

Thiago Nigro (_Do Mil ao Milhão_, 2018) divide a carteira em quatro classes:

| Classe                    | No app                                                | Alvo inicial |
| ------------------------- | ----------------------------------------------------- | ------------ |
| **A**ções brasileiras     | ações e ETFs de índice brasileiro (BOVA11, DIVO11…)   | 25%          |
| **R**eal estate           | FIIs                                                  | 25%          |
| **C**aixa                 | renda fixa (a reserva de emergência continua à parte) | 25%          |
| **A**tivos internacionais | ETFs de índice estrangeiro (IVVB11…)                  | 25%          |

Cada classe pode ficar entre 10% e 40%. Na ficha de cada ETF você diz se o índice é brasileiro ou estrangeiro; o aporte da classe internacional é dividido entre os ETFs estrangeiros favoritos. O método não diz quando rebalancear, então o app equilibra só pelos aportes. Conta no exterior, câmbio e BDRs ficam de fora.

## Como os FIIs são avaliados

O tipo do fundo (papel, tijolo, fundo de fundos ou híbrido) vem da carteira que ele declara à CVM, não do segmento informado, que muitas vezes não ajuda. As faixas mudam com o tipo:

- **Filtro de entrada (eliminatórias):** patrimônio ≥ R$ 500 mi, liquidez ≥ R$ 1 mi por dia e ao menos 4 anos de funcionamento
- **Isenção de IR:** negociado em bolsa e com pelo menos 100 cotistas
- **Estabilidade:** rendimentos dos últimos 12 meses ÷ 12 meses anteriores ≥ 0,9
- **Rendimento:** papel comparado ao CDI líquido de IR (render muito acima também é alerta de crédito arriscado); tijolo comparado ao juro real do Tesouro IPCA+
- **Preço:** P/VP como faixa de segurança, não como ranking. Papel até 1,08 e tijolo até 1,15; desconto muito grande é sinal de problema, não de pechincha
- **Carteira:** maior crédito ≤ 6% do patrimônio (papel); maior imóvel ≤ 25% da receita, 8 ou mais imóveis e vacância ≤ 10% (tijolo); taxa de administração ≤ 1% ao ano

Os dados vêm dos informes mensal e trimestral da CVM. Quando um informe é contraditório (por exemplo, imóvel 100% vago gerando receita), a regra fica "sem dado" em vez de usar um número errado.

## Como os ETFs entram

ETFs replicam um índice: não há empresa para avaliar pelo método Barsi, então eles não recebem nota. Cada ETF tem um checklist que só informa:

- **Liquidez** (eliminatória): ≥ R$ 1 mi por dia, ideal ≥ R$ 5 mi
- **Patrimônio:** ideal ≥ R$ 500 mi
- **Taxa de administração:** ideal ≤ 0,5% ao ano
- **Distribui proventos:** repassa os dividendos ou reinveste

Taxa e distribuição não estão em nenhuma fonte gratuita estruturada (o Yahoo não traz proventos de ETFs brasileiros), então você informa os dois na ficha do ETF. Você marca com ★ os ETFs que quer no aporte, e a fatia de ETFs é dividida em partes iguais entre os favoritos que não reprovaram em liquidez.

## De onde vêm os dados

| Dado                                                             | Fonte                                                                         |
| ---------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Selic, CDI, IPCA 12m                                             | Banco Central, API SGS (séries 432, 4389, 13522)                              |
| Tesouro Direto                                                   | Tesouro Transparente, CSV de preços e taxas                                   |
| Balanços (DRE, BP, DFC, DVA), incluindo circulante e imobilizado | CVM Dados Abertos, DFP anual                                                  |
| CNPJ ↔ ticker                                                    | CVM, FCA (valores mobiliários)                                                |
| FIIs: patrimônio, cotistas, composição, imóveis, vacância        | CVM Dados Abertos, informes mensal e trimestral de FII                        |
| ETFs: patrimônio                                                 | CVM Dados Abertos, cadastro de classes de fundos (ligado ao ticker pelo nome) |
| Preços, proventos, desdobramentos                                | Yahoo Finance via `yfinance` (não oficial)                                    |
| Cotação do dia                                                   | brapi (plano gratuito, opcional)                                              |

As ações, os FIIs e os ETFs do universo inicial ficam em `backend/app/data/universo.csv`, e outros podem ser adicionados pela tela Explorar.

## Stacks

| Camada    | Tecnologias                                                                                                                                                                                                                                                                                                                                  |
| --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| API       | Python 3.12, [FastAPI](https://fastapi.tiangolo.com/), [Pydantic](https://docs.pydantic.dev/) v2, [Uvicorn](https://www.uvicorn.org/)                                                                                                                                                                                                        |
| Dados     | [SQLite](https://www.sqlite.org/), [SQLAlchemy](https://www.sqlalchemy.org/) 2, [Alembic](https://alembic.sqlalchemy.org/) para migrações                                                                                                                                                                                                    |
| Coleta    | [httpx](https://www.python-httpx.org/) com [tenacity](https://tenacity.readthedocs.io/) (retry), [pandas](https://pandas.pydata.org/) para os CSVs da CVM, [yfinance](https://github.com/ranaroussi/yfinance), [APScheduler](https://apscheduler.readthedocs.io/) para a atualização diária, [Typer](https://typer.tiangolo.com/) para a CLI |
| Telas     | [Next.js](https://nextjs.org/) 16 (App Router), React 19, TypeScript, [Tailwind CSS](https://tailwindcss.com/) 4, [Recharts](https://recharts.org/), fonte Figtree                                                                                                                                                                           |
| Contrato  | OpenAPI gerado pelo FastAPI e tipos do front gerados com [openapi-typescript](https://openapi-ts.dev/)                                                                                                                                                                                                                                       |
| Qualidade | [uv](https://docs.astral.sh/uv/), [Ruff](https://docs.astral.sh/ruff/), [mypy](https://mypy-lang.org/), [pytest](https://docs.pytest.org/) com cobertura mínima, [ESLint](https://eslint.org/), [Prettier](https://prettier.io/), [Vitest](https://vitest.dev/), regras da casa próprias                                                     |
| Entrega   | Docker e Docker Compose; CI no GitHub Actions com lint, testes e build das imagens                                                                                                                                                                                                                                                           |

Os padrões de projeto usados estão documentados nos READMEs de cada área: **Strategy** e **Registry** nas metodologias, camadas com dependências apontando para dentro (routers → services → motor), e providers isolados das gravações.

## Desenvolvimento

Para mexer no código sem Docker, você precisa de [uv](https://docs.astral.sh/uv/) e Node 22+.

```bash
make setup    # instala dependências e cria backend/.env e frontend/.env.local
make dev      # API em http://localhost:8000/docs e telas em http://localhost:3000, com recarga automática
make sync     # força uma atualização de dados (ex.: make sync ETAPAS=macro,mercado)
make check    # lint + testes, o mesmo que a CI roda
make format   # aplica ruff format e prettier
make types    # regenera os tipos do front após mudar schemas da API
```

```
backend/            FastAPI + SQLAlchemy + Alembic (SQLite em backend/data/)
  app/api/routers/  endpoints REST finos
  app/services/     casos de uso: ativos, avaliações, metodologias, carteira, renda fixa, perfil, aporte, sync
  app/engine/       motor de regras puro (ações, FIIs, ETFs, metodologias, aporte, perfil)
  app/providers/    coletores: bcb, tesouro, cvm, cvm_fii, cvm_etf, market (brapi + Yahoo)
  tests/            pytest: motor, carteira, aporte, renda fixa, parsers, sync, API e regras da casa
frontend/           Next.js + Tailwind + Recharts; tipos gerados do OpenAPI; testes com Vitest
docker-compose.yml  API e telas prontas para uso
```

Cada área tem um README com o padrão a seguir:

| Área                                      | README                                                             |
| ----------------------------------------- | ------------------------------------------------------------------ |
| Backend (camadas, migrações, testes)      | [backend/README.md](backend/README.md)                             |
| Motor de regras e metodologias            | [backend/app/engine/README.md](backend/app/engine/README.md)       |
| Casos de uso, atualização e avaliações    | [backend/app/services/README.md](backend/app/services/README.md)   |
| Fontes externas                           | [backend/app/providers/README.md](backend/app/providers/README.md) |
| Frontend (estrutura, componentes, tokens) | [frontend/README.md](frontend/README.md)                           |

As regras de código valem para o repositório todo e estão em [CONTRIBUTING.md](CONTRIBUTING.md). Contribuições são bem-vindas: abra uma issue ou um pull request.

## Licença

[MIT](LICENSE). Use, modifique e distribua à vontade, mantendo o aviso de copyright.
