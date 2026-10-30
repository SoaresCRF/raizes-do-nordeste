from sqlalchemy import Connection

from src.domain.usuario.usuario import (
    VERSAO_TERMO_VIGENTE,
    FinalidadeConsentimento,
    Perfil,
    Usuario,
)
from src.infrastructure.database.repositorios.consentimentos import RepositorioConsentimentos
from src.infrastructure.database.repositorios.usuarios import RepositorioUsuarios
from src.infrastructure.seguranca.hash_senha import gerar_hash_senha


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
