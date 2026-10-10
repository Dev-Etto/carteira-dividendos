"""Erros de domínio.

Os services levantam estes erros sem conhecer HTTP; `app.main` os traduz para a resposta da API
com o status de cada classe e a mensagem em `detail`.
"""


class DomainError(Exception):
    """Base dos erros de regra de negócio."""

    status_code = 422


class NotFoundError(DomainError):
    """O recurso pedido não existe."""

    status_code = 404


class BusinessRuleError(DomainError):
    """A operação viola uma regra de negócio (data futura, venda maior que a posição etc.)."""

    status_code = 422


class ConflictError(DomainError):
    """O recurso já existe."""

    status_code = 409
