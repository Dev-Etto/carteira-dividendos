"""Questionário de perfil e alocação-alvo sugerida."""

from typing import Any

QUESTIONS: list[dict[str, Any]] = [
    {
        "id": "prazo",
        "text": "Quando você pretende usar o dinheiro que vai investir (fora a reserva)?",
        "options": [("Em menos de 2 anos", 0), ("Entre 2 e 5 anos", 1), ("Daqui a mais de 5 anos", 2)],
    },
    {
        "id": "queda",
        "text": "Seus investimentos caem 20% em um mês. O que você faz?",
        "options": [("Vendo tudo para não perder mais", 0), ("Espero passar", 1), ("Aproveito para comprar mais", 2)],
    },
    {
        "id": "objetivo",
        "text": "Qual é o seu principal objetivo?",
        "options": [
            ("Proteger o que tenho", 0),
            ("Ter uma renda mensal crescente", 1),
            ("Fazer o patrimônio crescer o máximo", 2),
        ],
    },
    {
        "id": "experiencia",
        "text": "Qual sua experiência com investimentos?",
        "options": [("Nenhuma", 0), ("Já investi em renda fixa", 1), ("Já investi em ações ou FIIs", 2)],
    },
    {
        "id": "tolerancia",
        "text": "Quanto do valor investido você aceitaria ver negativo por um tempo, sem precisar mexer?",
        "options": [("Menos de 10%", 0), ("Entre 10% e 30%", 1), ("Mais de 30%", 2)],
    },
]

ALLOCATIONS = {
    "conservador": {"renda_fixa": 50.0, "fiis": 25.0, "acoes": 20.0, "etfs": 5.0},
    "moderado": {"renda_fixa": 30.0, "fiis": 30.0, "acoes": 35.0, "etfs": 5.0},
    "arrojado": {"renda_fixa": 15.0, "fiis": 30.0, "acoes": 45.0, "etfs": 10.0},
}

DESCRIPTIONS = {
    "conservador": "Prioriza segurança. Metade em renda fixa, o resto em renda variável para começar a construir renda passiva.",
    "moderado": "Equilíbrio entre segurança e crescimento. Boa parte em ações e FIIs pagadores de dividendos.",
    "arrojado": "Aceita oscilações maiores em troca de mais crescimento. Maior peso em ações.",
}


def profile_from_answers(answers: dict[str, int]) -> str:
    total = sum(int(v) for v in answers.values())
    if total <= 3:
        return "conservador"
    if total <= 7:
        return "moderado"
    return "arrojado"
