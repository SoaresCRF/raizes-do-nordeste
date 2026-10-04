from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from src.domain.erros.erros import MENSAGEM_DADOS_INVALIDOS, DadosInvalidos, DetalheErro


class Perfil(StrEnum):
    CLIENTE = "CLIENTE"
    ATENDENTE = "ATENDENTE"
    COZINHA = "COZINHA"
    GERENTE = "GERENTE"
    ADMIN = "ADMIN"


PERFIS_LOTADOS_EM_UNIDADE = (Perfil.ATENDENTE, Perfil.COZINHA, Perfil.GERENTE)


def validar_lotacao(perfil: Perfil, unidade_id: int | None) -> None:
    """Funcionário de unidade tem unidade; ADMIN atua na rede toda e não tem (RF02)."""
    if perfil == Perfil.CLIENTE:
        detalhe = DetalheErro("perfil", "CLIENTE não é perfil de funcionário")
    elif perfil in PERFIS_LOTADOS_EM_UNIDADE and unidade_id is None:
        detalhe = DetalheErro("unidadeId", f"Obrigatório para o perfil {perfil}")
    elif perfil not in PERFIS_LOTADOS_EM_UNIDADE and unidade_id is not None:
        detalhe = DetalheErro("unidadeId", f"Não se aplica ao perfil {perfil}")
    else:
        return
    raise DadosInvalidos(MENSAGEM_DADOS_INVALIDOS, [detalhe])


class FinalidadeConsentimento(StrEnum):
    FIDELIDADE = "FIDELIDADE"
    MARKETING = "MARKETING"


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
    refresh_token_hash: str
    expira_em: datetime
    revogada_em: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class UsuarioAutenticado:
    id: int
    perfil: Perfil
    unidade_id: int | None
    sessao_id: int
