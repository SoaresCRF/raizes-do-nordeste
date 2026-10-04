from typing import Annotated

from email_validator import EmailNotValidError, validate_email
from fastapi import Path
from pydantic import AfterValidator, StringConstraints
from pydantic_core import PydanticCustomError

from src.api.schemas.base import recusar_caractere_nulo

# Tamanhos das colunas de `usuario` (tabelas.py).
TAMANHO_MAXIMO_EMAIL = 160
TAMANHO_MAXIMO_NOME = 120
TAMANHO_MINIMO_SENHA = 8
# Comporta frases-senha e impede que uma senha enorme faça o argon2 trabalhar à toa.
TAMANHO_MAXIMO_SENHA = 128

# Teto do `integer` do Postgres das colunas de id; acima dele o banco recusa e dá 500.
ID_MAXIMO = 2_147_483_647


def _normalizar_email(valor: str) -> str:
    try:
        endereco = validate_email(valor, check_deliverability=False)
    except EmailNotValidError:
        raise PydanticCustomError("email_invalido", "E-mail inválido") from None
    # Unicidade (RN25) e login não diferenciam maiúsculas de minúsculas.
    return endereco.normalized.lower()


Email = Annotated[
    str, StringConstraints(max_length=TAMANHO_MAXIMO_EMAIL), AfterValidator(_normalizar_email)
]
Nome = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=TAMANHO_MAXIMO_NOME)
]
Senha = Annotated[
    str, StringConstraints(min_length=TAMANHO_MINIMO_SENHA, max_length=TAMANHO_MAXIMO_SENHA)
]

# No contrato e nos erros de validação o parâmetro se chama `id`; no código, o nome
# da função diz de qual recurso é (unidade_id, produto_id...).
IdDoRecurso = Annotated[int, Path(alias="id", gt=0, le=ID_MAXIMO)]

# Textos de query string não passam pelo EsquemaEntrada.
SemCaractereNulo = AfterValidator(recusar_caractere_nulo)
