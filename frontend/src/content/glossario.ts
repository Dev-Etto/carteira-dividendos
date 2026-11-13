export type Termo = {
  slug: string;
  termo: string;
  curto: string;
  explicacao: string;
  exemplo?: string;
  categoria: "básico" | "ações" | "renda fixa" | "carteira" | "setores";
};

export const GLOSSARIO: Termo[] = [
  {
    slug: "dividendos",
    termo: "Dividendos e proventos",
    curto: "Parte do lucro que a empresa divide com quem tem as ações.",
    explicacao:
      'Quando uma empresa lucra, ela pode reinvestir o dinheiro ou dividir entre os sócios. A parte dividida é o dividendo. "Proventos" é o nome geral para tudo o que você recebe por ter o ativo: dividendos, JCP e rendimentos de FIIs. Na estratégia de dividendos, você reinveste esses proventos para comprar mais ações, que pagam mais proventos — a bola de neve.',
    exemplo: "Você tem 100 ações e a empresa paga R$ 1,50 por ação: recebe R$ 150.",
    categoria: "básico",
  },
  {
    slug: "dividend-yield",
    termo: "Dividend yield (DY)",
    curto: "Quanto a ação paga por ano em proventos, em % do preço.",
    explicacao:
      'DY = proventos pagos nos últimos 12 meses ÷ preço atual. É como o "aluguel" da ação. Cuidado: DY muito alto pode ser um provento extraordinário (que não se repete) ou o preço ter despencado por algum problema.',
    exemplo: "Ação a R$ 40 que pagou R$ 3,20 em 12 meses: DY de 8%.",
    categoria: "básico",
  },
  {
    slug: "data-com",
    termo: "Data-com",
    curto: "Último dia para comprar e ter direito ao provento anunciado.",
    explicacao:
      "Quem tem a ação no fim da data-com recebe o provento, mesmo que venda no dia seguinte. No dia seguinte (data-ex), o preço costuma cair mais ou menos o valor do provento — por isso dividendo não é dinheiro grátis.",
    categoria: "básico",
  },
  {
    slug: "jcp",
    termo: "Juros sobre capital próprio (JCP)",
    curto: "Outra forma de a empresa distribuir lucro, com IR retido na fonte.",
    explicacao:
      "Funciona como um dividendo, mas a empresa pode descontar o JCP do imposto dela. Para você, o imposto de renda já vem retido: o valor que cai na conta é o líquido.",
    categoria: "básico",
  },
  {
    slug: "bola-de-neve",
    termo: "Efeito bola de neve",
    curto: "Reinvestir proventos para comprar mais ativos que pagam mais proventos.",
    explicacao:
      'Cada provento reinvestido compra mais ações, que no próximo pagamento geram mais proventos. Com o tempo, a renda cresce sozinha, mesmo sem novos aportes. É a base do método Barsi, que chama isso de "carteira previdenciária".',
    categoria: "básico",
  },
  {
    slug: "aporte",
    termo: "Aporte",
    curto: "Dinheiro novo que você coloca nos investimentos.",
    explicacao:
      "O app usa os aportes para manter a carteira equilibrada: em vez de vender o que subiu, ele direciona o dinheiro novo para o que está abaixo do alvo.",
    categoria: "básico",
  },
  {
    slug: "diversificacao",
    termo: "Diversificação",
    curto: "Não colocar todos os ovos na mesma cesta.",
    explicacao:
      "Ter vários ativos de setores diferentes faz com que um problema em uma empresa não derrube sua renda inteira. O app sugere no máximo 20% das ações em um único ativo e 30% em um único setor.",
    categoria: "carteira",
  },
  {
    slug: "besst",
    termo: "BESST",
    curto: "Bancos, Energia, Saneamento, Seguros e Telecom: os setores preferidos do Barsi.",
    explicacao:
      "Luiz Barsi prefere setores perenes: serviços que as pessoas usam em qualquer cenário econômico. Isso deixa lucros e dividendos mais previsíveis do que em setores cíclicos, como mineração e siderurgia.",
    categoria: "ações",
  },
  {
    slug: "historico-proventos",
    termo: "Histórico de proventos",
    curto: "Quantos anos seguidos a empresa pagou proventos.",
    explicacao:
      "Uma empresa que pagou proventos por 10 anos seguidos atravessou crises, juros altos e baixos sem parar de remunerar o acionista. Menos de 5 anos é pouco histórico: é regra eliminatória no app.",
    categoria: "ações",
  },
  {
    slug: "consistencia-proventos",
    termo: "Consistência dos proventos",
    curto: "Se os proventos tiveram quedas fortes nos últimos anos.",
    explicacao:
      "Mais importante que pagar muito em um ano é pagar sempre. O app conta quantas vezes os proventos caíram mais de 30% de um ano para o outro nos últimos 5 anos.",
    categoria: "ações",
  },
  {
    slug: "lucro",
    termo: "Lucro líquido",
    curto: "O que sobra para a empresa depois de pagar tudo, inclusive impostos.",
    explicacao: "Dividendo sai do lucro. Empresa com prejuízo frequente não tem como sustentar dividendos.",
    categoria: "ações",
  },
  {
    slug: "roe",
    termo: "ROE (retorno sobre o patrimônio)",
    curto: "Quanto de lucro a empresa gera para cada real dos sócios.",
    explicacao:
      "ROE = lucro ÷ patrimônio líquido. Um ROE de 15% quer dizer que, para cada R$ 100 que os sócios têm na empresa, ela gera R$ 15 de lucro por ano. Quanto maior e mais estável, melhor.",
    categoria: "ações",
  },
  {
    slug: "divida-ebitda",
    termo: "Dívida líquida ÷ EBITDA",
    curto: "Quantos anos de geração de caixa seriam necessários para pagar a dívida.",
    explicacao:
      "Dívida líquida = dívidas − dinheiro em caixa. EBITDA é uma medida do caixa gerado pela operação. Uma relação de 2 quer dizer 2 anos de geração de caixa. Setores regulados, como energia e saneamento, aguentam um pouco mais de dívida porque a receita é previsível.",
    categoria: "ações",
  },
  {
    slug: "payout",
    termo: "Payout",
    curto: "Quanto do lucro a empresa distribui como proventos.",
    explicacao:
      "Payout de 60% = distribui 60% do lucro e reinveste 40%. Muito baixo rende pouco; acima de 100% a empresa distribui mais do que ganha, o que não se sustenta.",
    categoria: "ações",
  },
  {
    slug: "liquidez",
    termo: "Liquidez",
    curto: "Facilidade de comprar e vender o ativo sem mexer no preço.",
    explicacao:
      "Medida pelo volume médio negociado por dia. Ativos com pouca liquidez podem ser difíceis de vender quando você precisar. É regra eliminatória no app.",
    categoria: "ações",
  },
  {
    slug: "preco-teto",
    termo: "Preço-teto (Barsi)",
    curto: "O preço máximo a pagar para receber o yield desejado.",
    explicacao:
      "Preço-teto = média dos proventos por ação dos últimos 5 anos ÷ yield-alvo (6% no método Barsi). Comprando abaixo do teto, você garante pelo menos 6% ao ano em proventos se a empresa mantiver a média. A margem de segurança é quanto o preço está abaixo do teto.",
    exemplo: "Média de R$ 2,40 por ano ÷ 6% = teto de R$ 40. A ação a R$ 34 tem 15% de margem.",
    categoria: "ações",
  },
  {
    slug: "dy-anormal",
    termo: "Yield fora do normal",
    curto: "Quando o DY atual está muito acima da média histórica da empresa.",
    explicacao:
      "Pode ser um provento extraordinário (venda de um ativo, por exemplo), que não vai se repetir, ou uma queda forte do preço por algum problema. Nos dois casos, o DY atual engana.",
    categoria: "ações",
  },
  {
    slug: "percentil",
    termo: "Barato em relação a si mesmo",
    curto: "Compara o múltiplo de hoje (P/L ou P/VP) com a história da própria empresa.",
    explicacao:
      "Se o P/L atual está entre os 30% mais baixos dos últimos 5 anos, a ação está barata em relação ao próprio histórico. Não garante nada, mas evita comprar no topo.",
    categoria: "ações",
  },
  {
    slug: "p-l",
    termo: "P/L (preço ÷ lucro)",
    curto: "Quantos anos de lucro você paga ao comprar a ação.",
    explicacao:
      "P/L 8 = você paga 8 vezes o lucro anual por ação. Comparar com a própria empresa e com o setor é mais útil do que olhar o número sozinho.",
    categoria: "ações",
  },
  {
    slug: "p-vp",
    termo: "P/VP (preço ÷ valor patrimonial)",
    curto: "Quanto você paga em relação ao patrimônio da empresa.",
    explicacao: "P/VP 1 = você paga exatamente o valor do patrimônio. É o múltiplo mais usado para bancos e FIIs.",
    categoria: "ações",
  },
  {
    slug: "bazin",
    termo: "Preço-teto de Bazin",
    curto: "Proventos dos últimos 12 meses ÷ 6%.",
    explicacao:
      "Parecido com o teto Barsi, mas usa só o último ano. Reage mais rápido, mas é mais sensível a proventos extraordinários. O app mostra como segunda opinião.",
    categoria: "ações",
  },
  {
    slug: "graham",
    termo: "Valor de Graham",
    curto: "√(22,5 × lucro por ação × valor patrimonial por ação).",
    explicacao:
      "Fórmula de Benjamin Graham para um preço justo de empresas estáveis. Não serve bem para empresas de crescimento. É só uma segunda opinião.",
    categoria: "ações",
  },
  {
    slug: "fluxo-de-caixa-livre",
    termo: "Fluxo de caixa livre",
    curto: "O dinheiro que sobra depois de operar e investir.",
    explicacao:
      "Lucro contábil pode não virar dinheiro. O fluxo de caixa livre mostra o dinheiro que realmente sobrou. Se ele cobre os proventos com folga, o dividendo é sustentável.",
    categoria: "ações",
  },
  {
    slug: "provento-com-divida",
    termo: "Provento pago com dívida",
    curto: "Quando a empresa se endivida para manter os dividendos.",
    explicacao:
      "Se a dívida cresce mais rápido que a geração de caixa enquanto a empresa distribui quase todo o lucro, parte do dividendo está vindo de empréstimos. Isso não dura.",
    categoria: "ações",
  },
  {
    slug: "basileia",
    termo: "Índice de Basileia",
    curto: "Quanto capital próprio o banco tem para absorver perdas.",
    explicacao:
      "O mínimo regulatório no Brasil é de cerca de 10,5%. Bancos com índice alto têm folga para pagar dividendos mesmo em crises.",
    categoria: "setores",
  },
  {
    slug: "inadimplencia",
    termo: "Inadimplência",
    curto: "Percentual de empréstimos com mais de 90 dias de atraso.",
    explicacao:
      "Inadimplência acima da média do sistema indica mais perdas com crédito pela frente, o que reduz o lucro e os dividendos do banco.",
    categoria: "setores",
  },
  {
    slug: "indice-combinado",
    termo: "Índice combinado",
    curto: "Quanto a seguradora gasta (sinistros + despesas) para cada R$ 100 de prêmios.",
    explicacao: "Abaixo de 100% a operação de seguros dá lucro. Quanto menor, melhor.",
    categoria: "setores",
  },
  {
    slug: "segmentos-energia",
    termo: "Segmentos de energia",
    curto: "Transmissão, geração e distribuição têm riscos diferentes.",
    explicacao:
      "Transmissão recebe uma receita fixa por contrato, corrigida pela inflação. Geração depende de chuvas e preço da energia. Distribuição depende de consumo, inadimplência e revisões da ANEEL.",
    categoria: "setores",
  },
  {
    slug: "concessao",
    termo: "Concessão",
    curto: "Contrato com o governo para explorar um serviço por um prazo.",
    explicacao:
      "Energia e saneamento operam por concessões com data para acabar. Perto do vencimento, há risco de não renovar ou renovar em condições piores.",
    categoria: "setores",
  },
  {
    slug: "reserva-de-emergencia",
    termo: "Reserva de emergência",
    curto: "Dinheiro para imprevistos, guardado em aplicação segura e com resgate imediato.",
    explicacao:
      "Fica entre 6 e 12 meses dos seus gastos, dependendo da estabilidade da sua renda. Ela vem antes de ações e FIIs: sem reserva, um imprevisto obriga você a vender na hora errada.",
    categoria: "renda fixa",
  },
  {
    slug: "tesouro-selic",
    termo: "Tesouro Selic",
    curto: "Título do governo que acompanha a Selic, com resgate em 1 dia útil.",
    explicacao: "É o investimento mais seguro do país e quase não oscila. Ideal para a reserva de emergência.",
    categoria: "renda fixa",
  },
  {
    slug: "selic",
    termo: "Selic",
    curto: "A taxa básica de juros da economia, definida pelo Copom.",
    explicacao: "Quando a Selic sobe, a renda fixa rende mais e ações e FIIs tendem a cair; quando desce, o contrário.",
    categoria: "renda fixa",
  },
  {
    slug: "cdi",
    termo: "CDI",
    curto: "Taxa de referência dos CDBs, sempre muito próxima da Selic.",
    explicacao: "Um CDB que paga 100% do CDI rende praticamente a Selic, antes do imposto de renda.",
    categoria: "renda fixa",
  },
  {
    slug: "ipca",
    termo: "IPCA",
    curto: "O índice oficial de inflação.",
    explicacao: "Títulos IPCA+ pagam a inflação mais uma taxa fixa, protegendo o poder de compra no longo prazo.",
    categoria: "renda fixa",
  },
  {
    slug: "fgc",
    termo: "FGC",
    curto: "Fundo que garante até R$ 250 mil por CPF por instituição em CDB, LCI e LCA.",
    explicacao:
      "Se o banco quebrar, o FGC devolve até esse limite. Tesouro Direto não precisa de FGC: o risco é do governo federal.",
    categoria: "renda fixa",
  },
  {
    slug: "ir-regressivo",
    termo: "IR regressivo",
    curto: "O imposto da renda fixa cai quanto mais tempo você deixa o dinheiro aplicado.",
    explicacao: "22,5% até 180 dias, 20% até 360, 17,5% até 720 e 15% depois disso. LCI e LCA são isentas para pessoa física.",
    categoria: "renda fixa",
  },
  {
    slug: "preco-medio",
    termo: "Preço médio",
    curto: "Quanto você pagou, em média, por cada ação, incluindo taxas.",
    explicacao:
      "Preço médio = custo total das compras ÷ quantidade. Vendas não mudam o preço médio. É a base para calcular lucro e imposto.",
    categoria: "carteira",
  },
  {
    slug: "yield-on-cost",
    termo: "Yield on cost",
    curto: "Proventos dos últimos 12 meses ÷ quanto você pagou.",
    explicacao:
      "Mostra o yield sobre o seu custo, não sobre o preço de hoje. Comprando bem e com a empresa crescendo, ele aumenta com os anos.",
    categoria: "carteira",
  },
  {
    slug: "veredito",
    termo: "Nota e veredito",
    curto: "Como o app resume as regras em uma decisão.",
    explicacao:
      "Cada regra vale ✅ (1 ponto), ⚠️ (meio ponto) ou ❌ (zero), multiplicado pelo peso. Nota ≥ 70 com preço dentro do limite = comprar; nota ≥ 70 com preço alto = aguardar; nota < 50 ou regra eliminatória reprovada = evitar. Não é recomendação: é a aplicação de regras que você pode ver e ajustar.",
    categoria: "carteira",
  },
];

export const GLOSSARIO_POR_SLUG: Record<string, Termo> = Object.fromEntries(GLOSSARIO.map((t) => [t.slug, t]));

export const TRILHA_INICIO = [
  {
    titulo: "1. Monte a reserva de emergência",
    texto: "Antes de tudo, guarde de 6 a 12 meses de gastos no Tesouro Selic ou em um CDB de liquidez diária.",
    slug: "reserva-de-emergencia",
  },
  {
    titulo: "2. Entenda o que são proventos",
    texto: "Dividendos, JCP e rendimentos de FIIs: o dinheiro que os ativos pagam a você.",
    slug: "dividendos",
  },
  {
    titulo: "3. Conheça o método Barsi",
    texto: "Setores perenes (BESST), empresas que pagam há muitos anos e comprar abaixo do preço-teto.",
    slug: "besst",
  },
  {
    titulo: "4. Saiba quando o preço está bom",
    texto: "Preço-teto e margem de segurança dizem se vale comprar agora ou esperar.",
    slug: "preco-teto",
  },
  {
    titulo: "5. Diversifique e reinvista",
    texto: "Vários setores, aportes todo mês e proventos reinvestidos: a bola de neve.",
    slug: "bola-de-neve",
  },
];
