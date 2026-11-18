# Motor de regras (`app/engine`)

Regras de negócio **puras**: recebem dados em memória e devolvem resultados. Nada aqui acessa banco, rede ou API, por isso tudo é testado com objetos montados no próprio teste.

## Peças

| Arquivo | O que faz |
| --- | --- |
| `types.py` | Entradas (`StockSnapshot`, `FiiSnapshot`, `EtfSnapshot`) e saídas (`RuleResult`, `Evaluation`). |
| `score.py` | Nota ponderada e veredito (`comprar`, `aguardar`, `evitar`) a partir das regras. |
| `config.py` | Limites padrão de todas as regras. Toda regra lê seus limites daqui, e o usuário pode mudá-los em Configurações. |
| `acoes.py`, `fii.py`, `etf.py` | Regras por classe de ativo. |
| `metodos/` | Metodologias de investimento (ver abaixo). |
| `aporte.py`, `carteira.py`, `renda_fixa.py`, `perfil.py` | Plano de aporte, posição da carteira, reserva de emergência e questionário. |

## Como uma regra é escrita

Cada regra é uma função que recebe o snapshot e os limites e devolve um `RuleResult` com `status` (`ok`, `warn`, `fail` ou `na`), peso, se é eliminatória, o valor medido, o limite usado e uma explicação em português simples. Para criar uma regra:

1. adicione os limites em `config.py`, com valores que tenham fonte;
2. escreva a função e inclua-a na lista de regras da classe;
3. sem dado, devolva `na`: a regra some da nota em vez de puxá-la para baixo;
4. explique o resultado para quem está começando e cite a fonte na docstring;
5. crie o verbete no glossário do front (`frontend/src/content/glossario.ts`) e um teste em `backend/tests/`.

## Metodologias (`metodos/`)

Uma metodologia é um jeito de investir com nome e autor. Há dois tipos, cada um com um contrato em `metodos/base.py` (padrão **Strategy**):

| Contrato | Responde | Exemplos |
| --- | --- | --- |
| `MetodoSelecao` | Quais ações comprar: avalia o lote inteiro de ações e devolve uma `Evaluation` por ticker. | Barsi, Bazin, Graham, Fórmula Mágica |
| `MetodoDivisao` | Como dividir a carteira: o peso-alvo de cada classe. | Perfil de risco, ARCA |

O lote vai inteiro para o método de seleção porque alguns, como a Fórmula Mágica, ranqueiam as ações entre si. Métodos que avaliam cada ação sozinha herdam de `MetodoPorAtivo` e só implementam `evaluate_one`.

As metodologias ficam num **registro** (`metodos/registro.py`, padrão Registry). O resto do app só conhece o registro:

- a atualização avalia as ações por **todas** as metodologias de seleção e guarda uma avaliação por método;
- as telas mostram a avaliação da metodologia escolhida no perfil, e a ficha da ação mostra as outras para comparar;
- a divisão-alvo sugerida vem da metodologia de divisão escolhida.

### Como adicionar uma metodologia

1. Crie `metodos/<nome>.py` com uma classe que implementa o contrato e um `MethodInfo` (chave, nome, autor, resumo e foco).
2. Coloque os limites novos em `config.py`, com prefixo do método (ex.: `bazin_`).
3. Registre a instância em `SELECTION_METHODS` ou `ALLOCATION_METHODS`, em `registro.py`.
4. Teste o método isolado em `backend/tests/` e crie o verbete no glossário.

Não é preciso mexer em services, rotas, banco ou telas: a metodologia aparece em Configurações e na ficha sozinha. Uma chave que sair do registro cai no padrão (`barsi` e `perfil`), então o perfil de quem a usava continua funcionando.
