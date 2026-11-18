"""Método ARCA (Thiago Nigro, *Do Mil ao Milhão*, 2018): dividir a carteira em quatro classes,
Ações brasileiras, Real estate (FIIs), Caixa (renda fixa) e Ativos internacionais.

25% em cada uma é o ponto de partida, e cada classe pode ir de 10% a 40% (investimentos.com.br,
artigo sobre o método ARCA). ETFs de índice brasileiro contam em ações; ETFs de índice estrangeiro
formam a classe internacional. O método não publica regra numérica de rebalanceamento: o app
equilibra só pelos aportes, como nas outras divisões. Conta no exterior, câmbio e BDRs ficam de fora.
"""

from app.engine.metodos.base import MethodInfo, MetodoDivisao

INTERNATIONAL = "internacional"
CLASS_OF = {"acao": "acoes", "fii": "fiis", "etf": "acoes"}
EQUAL_SHARE = 25.0


class Arca(MetodoDivisao):
    info = MethodInfo(
        key="arca",
        label="ARCA",
        author="Thiago Nigro",
        summary="Quatro classes: ações brasileiras, FIIs, renda fixa e ativos internacionais (ETFs de índice estrangeiro), 25% em cada, ajustáveis entre 10% e 40%.",
        focus="divisao",
    )
    classes = ("acoes", "fiis", "renda_fixa", INTERNATIONAL)
    min_weight = 10.0
    max_weight = 40.0

    def targets(self, risk_profile: str) -> dict[str, float]:
        return dict.fromkeys(self.classes, EQUAL_SHARE)

    def class_of(self, asset_class: str, region: str) -> str:
        if region == INTERNATIONAL:
            return INTERNATIONAL
        return CLASS_OF.get(asset_class, asset_class)
