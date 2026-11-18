# Fontes externas (`app/providers`)

Cada provider baixa uma fonte e a transforma em objetos simples (dataclasses de `base.py` ou do próprio módulo). Eles **não gravam no banco**: quem grava é `services/sync.py`.

| Módulo | Fonte |
| --- | --- |
| `bcb.py` | Banco Central, API SGS: Selic, CDI e IPCA. |
| `tesouro.py` | Tesouro Transparente: preços e taxas do Tesouro Direto. |
| `cvm.py` | CVM: balanços anuais (DFP), trimestrais (ITR) e cadastro das companhias (FCA). |
| `cvm_fii.py` | CVM: informes mensal e trimestral dos FIIs. |
| `cvm_etf.py` | CVM: cadastro de classes de fundos, para o patrimônio dos ETFs. |
| `market.py` | Yahoo Finance (preços, proventos, desdobramentos) e brapi (cotação). |

## Regras

- Baixe sempre com `base.py`: ele repete a requisição com espera crescente e guarda os arquivos grandes da CVM em cache no disco.
- Interprete de forma defensiva: um campo ausente ou contraditório vira `None`, nunca um número inventado.
- Cada parser é testado com um arquivo de exemplo pequeno, sem rede (`respx` para as respostas HTTP).
