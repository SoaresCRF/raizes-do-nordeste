from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer, field_validator
from pydantic.alias_generators import to_camel
from pydantic_core import PydanticCustomError

CARACTERE_NULO = "\x00"


def recusar_caractere_nulo(valor: str) -> str:
    # O Postgres não guarda o caractere nulo em texto: sem esta checagem ele chega
    # ao driver e a requisição termina em 500 em vez de 422.
    if CARACTERE_NULO in valor:
        raise PydanticCustomError("caractere_nulo", "Texto com caractere nulo")
    return valor


class EsquemaSaida(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True)


class EsquemaEntrada(BaseModel):
    # Sem validate_by_name: o body só aceita os nomes do contrato (camelCase), e
    # extra="forbid" recusa campos que o cliente não pode definir (RN08, RN09).
    model_config = ConfigDict(alias_generator=to_camel, extra="forbid")

    @field_validator("*")
    @classmethod
    def _recusar_caractere_nulo_nos_textos(cls, valor: object) -> object:
        return recusar_caractere_nulo(valor) if isinstance(valor, str) else valor


def _formatar_data_hora(valor: datetime) -> str:
    return valor.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# Mesmo formato do timestamp do erro padrão e dos exemplos do RT: "2026-02-05T12:00:00Z" (RNF24).
DataHoraUtc = Annotated[datetime, PlainSerializer(_formatar_data_hora, return_type=str)]

# Número no JSON, como nos exemplos do RT ("total": 129.70); o padrão do Pydantic
# serializaria Decimal como texto.
ValorMonetario = Annotated[Decimal, PlainSerializer(float, return_type=float)]
