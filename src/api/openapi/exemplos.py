import copy
from collections.abc import Iterable
from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute, RouteContext, iter_route_contexts


def restaurar_exemplos(contrato: dict[str, Any], rotas: Iterable[RouteContext]) -> None:
    """Recoloca no contrato os exemplos de body e de resposta como foram escritos.

    O FastAPI gera o contrato com exclude_none, que apaga os null de dentro dos
    exemplos; sem eles o exemplo deixa de mostrar o contrato real.
    """
    for rota in rotas:
        if not isinstance(rota.original_route, APIRoute):
            continue
        for metodo in rota.methods:
            operacao = contrato["paths"][rota.path][metodo.lower()]
            if rota.body_field is not None and rota.body_field.field_info.openapi_examples:
                corpo = operacao["requestBody"]["content"]["application/json"]
                corpo["examples"] = copy.deepcopy(rota.body_field.field_info.openapi_examples)
            for status, resposta in rota.responses.items():
                exemplos = resposta.get("content", {}).get("application/json", {}).get("examples")
                if exemplos:
                    destino = operacao["responses"][str(status)]["content"]["application/json"]
                    destino["examples"] = copy.deepcopy(exemplos)


def preservar_exemplos(app: FastAPI) -> None:
    gerar_contrato = app.openapi

    def gerar_contrato_com_exemplos() -> dict[str, Any]:
        if app.openapi_schema is None:
            restaurar_exemplos(gerar_contrato(), iter_route_contexts(app.routes))
        return app.openapi_schema

    app.openapi = gerar_contrato_com_exemplos
