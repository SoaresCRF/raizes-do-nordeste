from typing import Annotated

from pydantic import Field, StringConstraints

from src.api.schemas.base import DataHoraUtc, EsquemaEntrada, EsquemaSaida
from src.api.schemas.campos import ID_MAXIMO, Email, Nome, Senha
from src.domain.usuario.usuario import FinalidadeConsentimento, Perfil

# Tamanho da coluna versao_termo.
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


class MinhaConta(EsquemaSaida):
    id: int
    nome: str
    email: str
    perfil: Perfil
    unidade_id: int | None
    consentimentos: list[ConsentimentoRegistrado]


class NovoFuncionario(EsquemaEntrada):
    nome: Nome
    email: Email
    senha: Senha
    perfil: Perfil
    unidade_id: Annotated[int, Field(le=ID_MAXIMO)] | None = None


class FuncionarioCriado(EsquemaSaida):
    id: int
    nome: str
    email: str
    perfil: Perfil
    unidade_id: int | None


class NovoConsentimento(EsquemaEntrada):
    finalidade: FinalidadeConsentimento
    concedido: bool
    versao_termo: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, min_length=1, max_length=TAMANHO_MAXIMO_VERSAO_TERMO
        ),
    ]
