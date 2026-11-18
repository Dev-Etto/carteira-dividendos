# Backend

API em FastAPI que coleta dados públicos, aplica as regras de investimento e guarda tudo num SQLite local.

## Camadas

As dependências apontam sempre para dentro: um router chama um service; um service usa o motor, os providers e o banco; o motor não conhece nada de fora.

```
app/api/routers/  HTTP  ──▶  app/services/  casos de uso  ──▶  app/engine/     regras puras
                                         │                 ├──▶  app/providers/  fontes externas
                                         │                 └──▶  app/db/         modelos e sessão
                                         └── app/schemas/  contrato da API (Pydantic)
```

| Pasta | Responsabilidade | Leia |
| --- | --- | --- |
| `app/api/routers/` | Recebe a requisição, chama um service e devolve um schema. Sem SQL e sem regra de negócio. | |
| `app/services/` | Casos de uso: avaliação, carteira, aporte, perfil, sincronização. | [README](app/services/README.md) |
| `app/engine/` | Regras de negócio puras, incluindo as metodologias de investimento. | [README](app/engine/README.md) |
| `app/providers/` | Baixa e interpreta BCB, Tesouro, CVM, Yahoo e brapi. | [README](app/providers/README.md) |
| `app/schemas/` | Entrada e saída da API. O front gera os tipos a partir daqui (`make types`). | |
| `app/db/` | Modelos SQLAlchemy e sessão. | |
| `alembic/versions/` | Migrações, numeradas (`0001`, `0002`…). | ver abaixo |
| `app/core/` | Configuração (`config.py`) e erros de domínio (`errors.py`). | |
| `app/jobs/` | Agendador da atualização diária e a CLI `sync`. | |
| `app/data/` | CSVs versionados: universo inicial de ativos e indicadores setoriais. | |
| `tools/` | Verificador das regras da casa (`style_rules.py`) e exportação do OpenAPI. | |

## Convenções

- **Erros de domínio:** services levantam `NotFoundError`, `ConflictError` ou `BusinessRuleError`; `app/main.py` traduz para 404, 409 e 422. Um service nunca importa nada de HTTP.
- **Consultas em lote:** carregue o que a requisição precisa de uma vez (`latest_evaluations`, `load_portfolio`), nunca consulte dentro de um laço.
- **Dinheiro do usuário** é `Decimal`; dados de mercado são `float`.
- **Dado ausente** vira status `na` na regra e não entra na nota. Nunca invente um número.

## Migrações

Toda mudança em `app/db/models.py` vem com uma migração nova em `alembic/versions/`, escrita à mão e testada nos dois sentidos:

```bash
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head
uv run alembic check   # confirma que modelo e migrações batem
```

O SQLite não altera tabelas no lugar; use `op.batch_alter_table`. A API aplica as migrações sozinha ao subir.

## Testes

`uv run pytest` roda tudo sem rede: os providers são testados com arquivos de exemplo e `respx`, e a API com um banco temporário. A cobertura mínima fica em `pyproject.toml` (`fail_under`).
