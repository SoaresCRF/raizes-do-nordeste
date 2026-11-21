from typing import Annotated

from pydantic import StringConstraints

from src.api.schemas.base import DataHoraUtc, EsquemaEntrada, EsquemaSaida
from src.api.schemas.campos import Email, Nome, Senha
from src.domain.usuario import FinalidadeConsentimento, Perfil

TAMANHO_MAXIMO_VERSAO_TERMO = 20


class NovoCliente(EsquemaEntrada):
    nome: Nome
    email: Email
    senha: Senha
    consentimento_fidelidade: bool


class UsuarioCriado(EsquemaSaida):
    id: int
    nome: str
    email: str
    perfil: Perfil


class ConsentimentoRegistrado(EsquemaSaida):
    finalidade: FinalidadeConsentimento
    concedido: bool
    registrado_em: DataHoraUtc


class NovoConsentimento(EsquemaEntrada):
    finalidade: FinalidadeConsentimento
    concedido: bool
    versao_termo: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, min_length=1, max_length=TAMANHO_MAXIMO_VERSAO_TERMO
        ),
    ]
