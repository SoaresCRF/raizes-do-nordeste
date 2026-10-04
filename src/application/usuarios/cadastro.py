from sqlalchemy import Connection

from src.domain.erros.erros import RecursoNaoEncontrado
from src.domain.usuario.usuario import FinalidadeConsentimento, Perfil, Usuario, validar_lotacao
from src.infrastructure.database.repositorios.consentimentos import RepositorioConsentimentos
from src.infrastructure.database.repositorios.unidades import RepositorioUnidades
from src.infrastructure.database.repositorios.usuarios import RepositorioUsuarios
from src.infrastructure.seguranca.hash_senha import HashSenha

VERSAO_TERMO_VIGENTE = "1.0"


def cadastrar_cliente(
    conexao: Connection,
    hash_senha: HashSenha,
    nome: str,
    email: str,
    senha: str,
    consentimento_fidelidade: bool,
) -> Usuario:
    cliente = RepositorioUsuarios(conexao).inserir(
        nome, email, hash_senha.gerar(senha), Perfil.CLIENTE, None
    )
    # A escolha é registrada mesmo quando negada: o histórico de consentimento
    # mostra o que o cliente decidiu no cadastro (RF30, RNF05).
    RepositorioConsentimentos(conexao).inserir(
        cliente.id,
        FinalidadeConsentimento.FIDELIDADE,
        consentimento_fidelidade,
        VERSAO_TERMO_VIGENTE,
    )
    return cliente


def cadastrar_funcionario(
    conexao: Connection,
    hash_senha: HashSenha,
    nome: str,
    email: str,
    senha: str,
    perfil: Perfil,
    unidade_id: int | None,
) -> Usuario:
    validar_lotacao(perfil, unidade_id)
    if unidade_id is not None and not RepositorioUnidades(conexao).existe(unidade_id):
        raise RecursoNaoEncontrado(f"Unidade {unidade_id} não encontrada")
    return RepositorioUsuarios(conexao).inserir(
        nome, email, hash_senha.gerar(senha), perfil, unidade_id
    )
