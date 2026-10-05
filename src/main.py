from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

import uvicorn
from fastapi import FastAPI

from src.api.middlewares.limite_corpo import MiddlewareLimiteCorpo
from src.api.middlewares.requisicao import MiddlewareRequisicao
from src.api.rotas import auditoria as rotas_auditoria
from src.api.rotas import auth as rotas_auth
from src.api.rotas import estoque as rotas_estoque
from src.api.rotas import fidelidade as rotas_fidelidade
from src.api.rotas import pagamentos as rotas_pagamentos
from src.api.rotas import pedidos as rotas_pedidos
from src.api.rotas import produtos as rotas_produtos
from src.api.rotas import relatorios as rotas_relatorios
from src.api.rotas import unidades as rotas_unidades
from src.api.rotas import usuarios as rotas_usuarios
from src.api.tratadores import registrar_tratadores_de_erro
from src.config.configuracao import Configuracao, carregar_configuracao
from src.infrastructure.database.conexao import criar_engine
from src.infrastructure.logging.logger import configurar_logging
from src.infrastructure.seguranca.hash_senha import HashSenha
from src.infrastructure.seguranca.token import TokenJwt

# Projeto acadêmico sem deploy (Q13): a API escuta só na máquina local.
HOST = "127.0.0.1"


def criar_app(configuracao: Configuracao) -> FastAPI:
    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
        app.state.engine = criar_engine(str(configuracao.banco_url))
        yield
        app.state.engine.dispose()

    app = FastAPI(
        title="Raízes do Nordeste",
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/docs/openapi.json",
        lifespan=ciclo_de_vida,
    )
    app.state.hash_senha = HashSenha()
    app.state.token_jwt = TokenJwt(
        configuracao.jwt_segredo, timedelta(minutes=configuracao.jwt_expiracao_minutos)
    )
    app.include_router(rotas_auth.roteador)
    app.include_router(rotas_usuarios.roteador)
    app.include_router(rotas_unidades.roteador)
    app.include_router(rotas_produtos.roteador)
    app.include_router(rotas_estoque.roteador)
    app.include_router(rotas_pedidos.roteador)
    app.include_router(rotas_pagamentos.roteador)
    app.include_router(rotas_fidelidade.roteador)
    app.include_router(rotas_auditoria.roteador)
    app.include_router(rotas_relatorios.roteador)
    registrar_tratadores_de_erro(app)
    app.add_middleware(MiddlewareLimiteCorpo)
    app.add_middleware(MiddlewareRequisicao)
    return app


def main() -> None:
    configuracao = carregar_configuracao()
    configurar_logging(configuracao.nivel_log)
    # log_config=None faz o uvicorn usar o logger JSON; o log de acesso é o do MiddlewareRequisicao.
    uvicorn.run(
        criar_app(configuracao),
        host=HOST,
        port=configuracao.porta,
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":
    main()
