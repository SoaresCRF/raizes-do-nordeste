import secrets
from dataclasses import dataclass

from sqlalchemy import Connection

from src.domain.erros.erros import RecursoNaoEncontrado
from src.domain.usuario.usuario import Consentimento, FinalidadeConsentimento, Usuario
from src.infrastructure.database.repositorios.consentimentos import RepositorioConsentimentos
from src.infrastructure.database.repositorios.sessoes import RepositorioSessoes
from src.infrastructure.database.repositorios.usuarios import RepositorioUsuarios
from src.infrastructure.seguranca.hash_senha import HashSenha

NOME_ANONIMIZADO = "Cliente anonimizado"
# .invalid é reservado (RFC 2606): o e-mail continua único e nunca recebe mensagem.
DOMINIO_ANONIMIZADO = "anonimizado.invalid"


@dataclass(frozen=True)
class Conta:
    usuario: Usuario
    consentimentos: list[Consentimento]


def consultar_conta(conexao: Connection, usuario_id: int) -> Conta:
    usuario = RepositorioUsuarios(conexao).buscar_por_id(usuario_id)
    if usuario is None:
        raise RecursoNaoEncontrado(f"Usuário {usuario_id} não encontrado")
    return Conta(usuario, RepositorioConsentimentos(conexao).listar_vigentes(usuario_id))


def registrar_consentimento(
    conexao: Connection,
    usuario_id: int,
    finalidade: FinalidadeConsentimento,
    concedido: bool,
    versao_termo: str,
) -> Consentimento:
    repo = RepositorioConsentimentos(conexao)
    return repo.inserir(usuario_id, finalidade, concedido, versao_termo)


def anonimizar_conta(conexao: Connection, hash_senha: HashSenha, usuario_id: int) -> None:
    """Remove nome, e-mail e senha e encerra as sessões; pedidos e consentimentos ficam (RF36)."""
    # Hash de um segredo descartado: nenhuma senha volta a conferir com esta conta.
    senha_hash = hash_senha.gerar(secrets.token_urlsafe())
    RepositorioUsuarios(conexao).anonimizar(
        usuario_id, NOME_ANONIMIZADO, f"cliente-{usuario_id}@{DOMINIO_ANONIMIZADO}", senha_hash
    )
    RepositorioSessoes(conexao).revogar_do_usuario(usuario_id)
