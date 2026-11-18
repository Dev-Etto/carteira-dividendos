# Carteira de Dividendos

Assistente **local e de código aberto** para montar e manter uma carteira de renda passiva com dividendos, seguindo o **método Barsi**. Ele avalia ações por regras explícitas, explica cada nota em português simples, cuida da reserva de emergência e diz onde colocar o aporte do mês.

> O app aplica regras e mostra o porquê de cada resultado. **Não é recomendação de investimento**: a decisão é sempre sua.

## Propósito

Investir para viver de dividendos é simples de explicar e difícil de manter: comprar boas pagadoras de proventos, a preço justo, todo mês, sem se deixar levar pelo humor do mercado. Na prática, isso exige olhar balanços, calcular preço-teto, acompanhar a reserva e decidir para onde vai cada aporte.

Este projeto existe para tirar esse trabalho braçal do caminho sem tirar o entendimento. Ele foi pensado para quem está começando e quer aprender o método enquanto aplica, e para quem já investe e quer disciplina e transparência no processo.

## Abordagem

- **Regras explícitas, não caixa-preta.** Cada ação passa por um checklist (✓ ok, ! atenção, ✕ reprovada). A nota é a soma ponderada dessas regras, e cada linha diz qual dado foi usado, de onde veio e por que passou ou não.
- **Método Barsi como base.** Setores perenes (bancos, energia, saneamento, seguros, telecom), longo histórico de proventos, lucro consistente, dívida controlada e compra só abaixo do preço-teto. Em cima disso entram regras por setor e a sustentabilidade do dividendo.
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

| Comando | O que faz |
| --- | --- |
| `docker compose up -d --build` (ou `make up`) | sobe ou atualiza API e telas |
| `docker compose down` (ou `make down`) | para tudo, mantendo os dados |
| `docker compose logs -f` (ou `make logs`) | acompanha os logs |
| `docker compose down -v` | para tudo e **apaga** os dados, para começar do zero |

**Configuração opcional:** crie um arquivo `.env` na raiz do projeto.

```env
BRAPI_TOKEN=seu_token   # token gratuito de https://brapi.dev para cotações mais frescas (sem ele, usa o fechamento do Yahoo)
SYNC_HOUR=19            # hora da atualização automática diária
CVM_YEARS=6             # anos de balanços da CVM a baixar
```

## Telas

| Tela | O que faz |
| --- | --- |
| Onboarding | Questionário de perfil, reserva de emergência (6 a 12 meses de gastos) e divisão-alvo da carteira |
| Início | Próximo passo recomendado, reserva, renda passiva × meta, divisão atual × alvo, oportunidades, Selic/CDI/IPCA |
| Explorar | Ranking de ações e de FIIs com nota, veredito, preço-teto (ou preço máximo pelo P/VP) e margem; ETFs com checklist e favoritos; adicionar novos ativos |
| Ficha do ativo | Checklist de regras com explicação, preço-teto, Bazin, Graham, gráficos, riscos e fonte de cada dado |
| Carteira | Posições, preço médio, resultado, yield on cost, alertas de concentração e histórico de operações editável |
| Aporte do mês | Plano de compras: reserva → classes abaixo do alvo → melhores ações e FIIs e ETFs favoritos; registra compras e aplicações de uma vez |
| Renda fixa | Reserva de emergência, aplicações, comparador isento × tributado e taxas do Tesouro Direto |
| Aprender | Glossário com tudo o que aparece no app e a trilha "Comece aqui" |
| Configurações | Atualização de dados, perfil, divisão-alvo e limites das regras |


## Como as ações são avaliadas

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

| Dado | Fonte |
| --- | --- |
| Selic, CDI, IPCA 12m | Banco Central, API SGS (séries 432, 4389, 13522) |
| Tesouro Direto | Tesouro Transparente, CSV de preços e taxas |
| Balanços (DRE, BP, DFC, DVA) | CVM Dados Abertos, DFP anual |
| CNPJ ↔ ticker | CVM, FCA (valores mobiliários) |
| FIIs: patrimônio, cotistas, composição, imóveis, vacância | CVM Dados Abertos, informes mensal e trimestral de FII |
| ETFs: patrimônio | CVM Dados Abertos, cadastro de classes de fundos (ligado ao ticker pelo nome) |
| Preços, proventos, desdobramentos | Yahoo Finance via `yfinance` (não oficial) |
| Cotação do dia | brapi (plano gratuito, opcional) |

As ações, os FIIs e os ETFs do universo inicial ficam em `backend/app/data/universo.csv`, e outros podem ser adicionados pela tela Explorar.

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
  app/services/     casos de uso: ativos, carteira, operações, renda fixa, perfil, aporte, painel, sync
  app/engine/       motor de regras puro (ações, renda fixa, carteira, aporte, perfil)
  app/providers/    coletores: bcb, tesouro, cvm, market (brapi + Yahoo)
  tests/            pytest: motor, carteira, aporte, renda fixa, parsers, sync, API e regras da casa
frontend/           Next.js + Tailwind + Recharts; tipos gerados do OpenAPI; testes com Vitest
docker-compose.yml  API e telas prontas para uso
```

Os padrões de código e a arquitetura estão em [CONTRIBUTING.md](CONTRIBUTING.md). Contribuições são bem-vindas: abra uma issue ou um pull request.

## Licença

[MIT](LICENSE). Use, modifique e distribua à vontade, mantendo o aviso de copyright.
