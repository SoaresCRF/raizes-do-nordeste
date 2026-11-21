import secrets
from dataclasses import dataclass

from sqlalchemy import Connection

from src.domain.erros import CredenciaisInvalidas, NaoAutenticado
from src.domain.usuario import Usuario, UsuarioAutenticado
from src.infrastructure.database.repositorios.sessoes import RepositorioSessoes
from src.infrastructure.database.repositorios.usuarios import RepositorioUsuarios
from src.infrastructure.seguranca.hash_senha import gerar_hash_senha, senha_confere
from src.infrastructure.seguranca.token import ServicoTokenJwt

MENSAGEM_CREDENCIAIS_INVALIDAS = "E-mail ou senha inválidos"
MENSAGEM_SESSAO_ENCERRADA = "Sessão encerrada; faça login novamente"
_HASH_DE_REFERENCIA = gerar_hash_senha(secrets.token_urlsafe())


@dataclass(frozen=True)
class SessaoIniciada:
    access_token: str
    usuario: Usuario


def iniciar_sessao(
    conexao: Connection, servico_token: ServicoTokenJwt, email: str, senha: str
) -> SessaoIniciada:
    usuario = RepositorioUsuarios(conexao).buscar_por_email(email)
    if usuario is None:
        senha_confere(senha, _HASH_DE_REFERENCIA)
        raise CredenciaisInvalidas(MENSAGEM_CREDENCIAIS_INVALIDAS)
    if not senha_confere(senha, usuario.senha_hash) or not usuario.ativo:
        raise CredenciaisInvalidas(MENSAGEM_CREDENCIAIS_INVALIDAS)

    sessao = RepositorioSessoes(conexao).inserir(usuario.id)
    return SessaoIniciada(servico_token.emitir(usuario, sessao.id), usuario)


def autenticar(
    conexao: Connection, servico_token: ServicoTokenJwt, access_token: str
) -> UsuarioAutenticado:
    usuario = servico_token.validar(access_token)
    if not RepositorioSessoes(conexao).esta_ativa(usuario.sessao_id, usuario.id):
        raise NaoAutenticado(MENSAGEM_SESSAO_ENCERRADA)
    return usuario


def encerrar_sessao(conexao: Connection, sessao_id: int) -> None:
    RepositorioSessoes(conexao).revogar(sessao_id)
