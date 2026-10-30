import secrets

from sqlalchemy import Connection

from src.domain.usuario.usuario import Consentimento, FinalidadeConsentimento
from src.infrastructure.database.repositorios.consentimentos import RepositorioConsentimentos
from src.infrastructure.database.repositorios.sessoes import RepositorioSessoes
from src.infrastructure.database.repositorios.usuarios import RepositorioUsuarios
from src.infrastructure.seguranca.hash_senha import gerar_hash_senha

NOME_ANONIMIZADO = "Cliente anonimizado"
DOMINIO_ANONIMIZADO = "anonimizado.invalid"


def registrar_consentimento(
    conexao: Connection,
    usuario_id: int,
    finalidade: FinalidadeConsentimento,
    concedido: bool,
    versao_termo: str,
) -> Consentimento:
    repositorio = RepositorioConsentimentos(conexao)
    return repositorio.inserir(usuario_id, finalidade, concedido, versao_termo)


def anonimizar_conta(conexao: Connection, usuario_id: int) -> None:
    senha_hash = gerar_hash_senha(secrets.token_urlsafe())
    RepositorioUsuarios(conexao).anonimizar(
        usuario_id, NOME_ANONIMIZADO, f"cliente-{usuario_id}@{DOMINIO_ANONIMIZADO}", senha_hash
    )
    RepositorioSessoes(conexao).revogar_do_usuario(usuario_id)
