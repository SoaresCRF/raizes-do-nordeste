from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Body

from src.api.autenticacao import UsuarioLogado
from src.api.dependencias import ConexaoBanco, ServicoHashSenha, ServicoToken
from src.api.openapi import auth as documentacao
from src.api.schemas.auth import (
    AcessoRenovado,
    Credenciais,
    RenovacaoDeAcesso,
    TokensEmitidos,
    UsuarioDaSessao,
)
from src.application.auth.sessoes import encerrar_sessao, fazer_login, renovar_acesso

roteador = APIRouter(prefix="/auth", tags=["Auth"])


@roteador.post("/login", **documentacao.LOGIN)
def entrar(
    credenciais: Annotated[Credenciais, Body(openapi_examples=documentacao.EXEMPLOS_LOGIN)],
    conexao: ConexaoBanco,
    hash_senha: ServicoHashSenha,
    token_jwt: ServicoToken,
) -> TokensEmitidos:
    sessao = fazer_login(conexao, hash_senha, token_jwt, credenciais.email, credenciais.senha)
    return TokensEmitidos(
        access_token=sessao.access_token,
        refresh_token=sessao.refresh_token,
        expires_in=int(token_jwt.validade.total_seconds()),
        user=UsuarioDaSessao.model_validate(sessao.usuario, from_attributes=True),
    )


@roteador.post("/logout", status_code=HTTPStatus.NO_CONTENT, **documentacao.LOGOUT)
def sair(usuario: UsuarioLogado, conexao: ConexaoBanco) -> None:
    encerrar_sessao(conexao, usuario.sessao_id)


# Rota pública: o refresh token do body é a credencial, porque o access token
# normalmente já expirou quando o cliente chama esta rota.
@roteador.post("/refresh", **documentacao.REFRESH)
def renovar(
    renovacao: Annotated[RenovacaoDeAcesso, Body(openapi_examples=documentacao.EXEMPLOS_REFRESH)],
    conexao: ConexaoBanco,
    token_jwt: ServicoToken,
) -> AcessoRenovado:
    return AcessoRenovado(
        access_token=renovar_acesso(conexao, token_jwt, renovacao.refresh_token),
        expires_in=int(token_jwt.validade.total_seconds()),
    )
