from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

import uvicorn
from fastapi import APIRouter, FastAPI

from src.api.middlewares.requisicao import MiddlewareRequisicao
from src.api.openapi.exemplos import preservar_exemplos
from src.api.openapi.geral import DESCRICAO_API, TAGS
from src.api.rotas import auditoria as rotas_auditoria
from src.api.rotas import auth as rotas_auth
from src.api.rotas import estoque as rotas_estoque
from src.api.rotas import fidelidade as rotas_fidelidade
from src.api.rotas import pagamentos as rotas_pagamentos
from src.api.rotas import pedidos as rotas_pedidos
from src.api.rotas import produtos as rotas_produtos
from src.api.rotas import unidades as rotas_unidades
from src.api.rotas import usuarios as rotas_usuarios
from src.api.tratadores import registrar_tratadores_de_erro
from src.config.configuracao import Configuracao, carregar_configuracao
from src.infrastructure.database.conexao import criar_engine
from src.infrastructure.logging.logger import configurar_logging
from src.infrastructure.seguranca.token import ServicoTokenJwt

HOST = "127.0.0.1"


ROTEADORES: list[APIRouter] = [
    rotas_auth.roteador,
    rotas_usuarios.roteador,
    rotas_unidades.roteador,
    rotas_produtos.roteador,
    rotas_estoque.roteador,
    rotas_pedidos.roteador,
    rotas_pagamentos.roteador,
    rotas_fidelidade.roteador,
    rotas_auditoria.roteador,
]


def criar_app(configuracao: Configuracao) -> FastAPI:
    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
        app.state.engine = criar_engine(str(configuracao.banco_url))
        yield
        app.state.engine.dispose()

    app = FastAPI(
        title="Raízes do Nordeste",
        version="0.1.0",
        description=DESCRICAO_API,
        openapi_tags=TAGS,
        openapi_url="/docs/openapi.json",
        lifespan=ciclo_de_vida,
    )
    app.state.servico_token = ServicoTokenJwt(
        configuracao.jwt_segredo, timedelta(minutes=configuracao.jwt_expiracao_minutos)
    )
    for roteador in ROTEADORES:
        app.include_router(roteador)
    preservar_exemplos(app)
    registrar_tratadores_de_erro(app)
    app.add_middleware(MiddlewareRequisicao)
    return app


def main() -> None:
    configuracao = carregar_configuracao()
    configurar_logging(configuracao.nivel_log)
    uvicorn.run(
        criar_app(configuracao),
        host=HOST,
        port=configuracao.porta,
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":
    main()
