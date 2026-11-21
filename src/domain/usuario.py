from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from src.domain.erros import (
    AcessoNegado,
)


class Perfil(StrEnum):
    CLIENTE = "CLIENTE"
    ATENDENTE = "ATENDENTE"
    COZINHA = "COZINHA"
    GERENTE = "GERENTE"
    ADMIN = "ADMIN"


PERFIS_LOTADOS_EM_UNIDADE = (Perfil.ATENDENTE, Perfil.COZINHA, Perfil.GERENTE)
MENSAGEM_SEM_ACESSO_A_UNIDADE = "Usuário sem acesso à unidade {unidade_id}"


class FinalidadeConsentimento(StrEnum):
    FIDELIDADE = "FIDELIDADE"


VERSAO_TERMO_VIGENTE = "1.0"


@dataclass
class Usuario:
    id: int
    nome: str
    email: str
    senha_hash: str
    perfil: Perfil
    unidade_id: int | None
    ativo: bool
    anonimizado_em: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass
class Consentimento:
    id: int
    usuario_id: int
    finalidade: FinalidadeConsentimento
    concedido: bool
    versao_termo: str
    registrado_em: datetime
    created_at: datetime
    updated_at: datetime


@dataclass
class Sessao:
    id: int
    usuario_id: int
    revogada_em: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class UsuarioAutenticado:
    id: int
    perfil: Perfil
    unidade_id: int | None
    sessao_id: int


def verificar_acesso_a_unidade(usuario: UsuarioAutenticado, unidade_id: int) -> None:
    if usuario.perfil in PERFIS_LOTADOS_EM_UNIDADE and usuario.unidade_id != unidade_id:
        raise AcessoNegado(MENSAGEM_SEM_ACESSO_A_UNIDADE.format(unidade_id=unidade_id))


def obter_unidade_restrita(usuario: UsuarioAutenticado) -> int | None:
    if usuario.perfil not in PERFIS_LOTADOS_EM_UNIDADE:
        return None
    return usuario.unidade_id
