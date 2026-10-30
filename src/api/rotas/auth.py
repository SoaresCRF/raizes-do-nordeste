from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Body

from src.api.autenticacao import UsuarioLogado
from src.api.dependencias import ConexaoBanco, ServicoToken
from src.api.openapi import auth as documentacao
from src.api.schemas.auth import Credenciais, TokensEmitidos, UsuarioDaSessao
from src.application.auth.sessoes import encerrar_sessao, iniciar_sessao

roteador = APIRouter(prefix="/auth", tags=["Auth"])


@roteador.post("/login", **documentacao.LOGIN)
def entrar(
    credenciais: Annotated[Credenciais, Body(openapi_examples=documentacao.EXEMPLOS_LOGIN)],
    conexao: ConexaoBanco,
    servico_token: ServicoToken,
) -> TokensEmitidos:
    sessao = iniciar_sessao(conexao, servico_token, credenciais.email, credenciais.senha)
    return TokensEmitidos(
        access_token=sessao.access_token,
        expires_in=int(servico_token.validade.total_seconds()),
        user=UsuarioDaSessao.model_validate(sessao.usuario),
    )


@roteador.post("/logout", status_code=HTTPStatus.NO_CONTENT, **documentacao.LOGOUT)
def sair(usuario: UsuarioLogado, conexao: ConexaoBanco) -> None:
    encerrar_sessao(conexao, usuario.sessao_id)
