import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import Connection

from src.domain.erros.erros import CredenciaisInvalidas, NaoAutenticado
from src.domain.usuario.usuario import Usuario, UsuarioAutenticado
from src.infrastructure.database.repositorios.sessoes import RepositorioSessoes
from src.infrastructure.database.repositorios.usuarios import RepositorioUsuarios
from src.infrastructure.seguranca.hash_senha import HashSenha
from src.infrastructure.seguranca.token import (
    TokenJwt,
    gerar_refresh_token,
    resumir_refresh_token,
)

VALIDADE_REFRESH_TOKEN = timedelta(days=7)
MENSAGEM_CREDENCIAIS_INVALIDAS = "E-mail ou senha inválidos"
MENSAGEM_SESSAO_ENCERRADA = "Sessão encerrada; faça login novamente"
MENSAGEM_REFRESH_INVALIDO = "Refresh token inválido ou expirado"
# E-mail inexistente também passa por uma verificação argon2: sem ela, a resposta
# mais rápida revelaria quais e-mails estão cadastrados.
_HASH_DE_REFERENCIA = HashSenha().gerar(secrets.token_urlsafe())


@dataclass(frozen=True)
class SessaoIniciada:
    access_token: str
    refresh_token: str
    usuario: Usuario


def fazer_login(
    conexao: Connection, hash_senha: HashSenha, token_jwt: TokenJwt, email: str, senha: str
) -> SessaoIniciada:
    usuario = RepositorioUsuarios(conexao).buscar_por_email(email)
    if usuario is None:
        hash_senha.confere(senha, _HASH_DE_REFERENCIA)
        raise CredenciaisInvalidas(MENSAGEM_CREDENCIAIS_INVALIDAS)
    if not hash_senha.confere(senha, usuario.senha_hash) or not usuario.ativo:
        raise CredenciaisInvalidas(MENSAGEM_CREDENCIAIS_INVALIDAS)

    refresh_token = gerar_refresh_token()
    sessao = RepositorioSessoes(conexao).criar(
        usuario.id,
        resumir_refresh_token(refresh_token),
        datetime.now(UTC) + VALIDADE_REFRESH_TOKEN,
    )
    return SessaoIniciada(token_jwt.emitir(usuario, sessao.id), refresh_token, usuario)


def autenticar(conexao: Connection, token_jwt: TokenJwt, access_token: str) -> UsuarioAutenticado:
    usuario = token_jwt.ler(access_token)
    if not RepositorioSessoes(conexao).esta_ativa(usuario.sessao_id, usuario.id):
        raise NaoAutenticado(MENSAGEM_SESSAO_ENCERRADA)
    return usuario


def encerrar_sessao(conexao: Connection, sessao_id: int) -> None:
    RepositorioSessoes(conexao).revogar(sessao_id)


def renovar_acesso(conexao: Connection, token_jwt: TokenJwt, refresh_token: str) -> str:
    sessao = RepositorioSessoes(conexao).buscar_ativa_por_refresh(
        resumir_refresh_token(refresh_token)
    )
    if sessao is None:
        raise NaoAutenticado(MENSAGEM_REFRESH_INVALIDO)
    usuario = RepositorioUsuarios(conexao).buscar_por_id(sessao.usuario_id)
    if usuario is None or not usuario.ativo:
        raise NaoAutenticado(MENSAGEM_REFRESH_INVALIDO)
    return token_jwt.emitir(usuario, sessao.id)
