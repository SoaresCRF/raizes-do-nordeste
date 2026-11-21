from typing import Annotated

from pydantic import AfterValidator, StringConstraints
from pydantic_core import PydanticCustomError

from src.api.schemas.base import EsquemaEntrada, EsquemaSaida
from src.api.schemas.campos import Nome
from src.domain.unidade import TipoUnidade

TAMANHO_MAXIMO_CIDADE = 80
TAMANHO_MAXIMO_REGIAO = 40
UFS = frozenset(
    {
        "AC",
        "AL",
        "AM",
        "AP",
        "BA",
        "CE",
        "DF",
        "ES",
        "GO",
        "MA",
        "MG",
        "MS",
        "MT",
        "PA",
        "PB",
        "PE",
        "PI",
        "PR",
        "RJ",
        "RN",
        "RO",
        "RR",
        "RS",
        "SC",
        "SE",
        "SP",
        "TO",
    }
)


def _normalizar_uf(valor: str) -> str:
    sigla = valor.upper()
    if sigla not in UFS:
        raise PydanticCustomError("uf_invalida", "UF inválida")
    return sigla


Cidade = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=TAMANHO_MAXIMO_CIDADE)
]
Regiao = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=TAMANHO_MAXIMO_REGIAO)
]
Uf = Annotated[str, StringConstraints(strip_whitespace=True), AfterValidator(_normalizar_uf)]


class NovaUnidade(EsquemaEntrada):
    nome: Nome
    cidade: Cidade
    uf: Uf
    regiao: Regiao
    tipo: TipoUnidade


class AlteracaoUnidade(NovaUnidade):
    ativa: bool


class UnidadeResposta(EsquemaSaida):
    id: int
    nome: str
    cidade: str
    uf: str
    regiao: str
    tipo: TipoUnidade
    ativa: bool
