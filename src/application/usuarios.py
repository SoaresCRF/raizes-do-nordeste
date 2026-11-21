import secrets

from sqlalchemy import Connection

from src.domain.usuario import (
    VERSAO_TERMO_VIGENTE,
    Consentimento,
    FinalidadeConsentimento,
    Perfil,
    Usuario,
)
from src.infrastructure.database.repositorios.consentimentos import RepositorioConsentimentos
from src.infrastructure.database.repositorios.sessoes import RepositorioSessoes
from src.infrastructure.database.repositorios.usuarios import RepositorioUsuarios
from src.infrastructure.seguranca.hash_senha import gerar_hash_senha

NOME_ANONIMIZADO = "Cliente anonimizado"
DOMINIO_ANONIMIZADO = "anonimizado.invalid"


def cadastrar_cliente(
    conexao: Connection,
    nome: str,
    email: str,
    senha: str,
    consentimento_fidelidade: bool,
) -> Usuario:
    cliente = RepositorioUsuarios(conexao).inserir(
        nome, email, gerar_hash_senha(senha), Perfil.CLIENTE, None
    )
    RepositorioConsentimentos(conexao).inserir(
        cliente.id,
        FinalidadeConsentimento.FIDELIDADE,
        consentimento_fidelidade,
        VERSAO_TERMO_VIGENTE,
    )
    return cliente


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
