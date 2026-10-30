from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer, field_validator
from pydantic.alias_generators import to_camel
from pydantic_core import PydanticCustomError

CARACTERE_NULO = "\x00"


def recusar_caractere_nulo(valor: str) -> str:
    if CARACTERE_NULO in valor:
        raise PydanticCustomError("caractere_nulo", "Texto com caractere nulo")
    return valor


class EsquemaSaida(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True, from_attributes=True)


class EsquemaEntrada(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, extra="forbid")

    @field_validator("*")
    @classmethod
    def _recusar_caractere_nulo_nos_textos(cls, valor: object) -> object:
        return recusar_caractere_nulo(valor) if isinstance(valor, str) else valor


def _formatar_data_hora(valor: datetime) -> str:
    return valor.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


DataHoraUtc = Annotated[datetime, PlainSerializer(_formatar_data_hora, return_type=str)]

ValorMonetario = Annotated[Decimal, PlainSerializer(float, return_type=float)]
