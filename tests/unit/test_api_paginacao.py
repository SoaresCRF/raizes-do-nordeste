from typing import Annotated

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from src.api.schemas.paginacao import Pagina, ParametrosPaginacao, obter_paginacao

TOTAL_DE_ITENS = 25


@pytest.fixture
def cliente(app):
    @app.get("/teste/numeros", response_model=Pagina[int])
    def listar_numeros(paginacao: Annotated[ParametrosPaginacao, Depends(obter_paginacao)]):
        numeros = list(range(TOTAL_DE_ITENS))
        pagina = numeros[paginacao.offset : paginacao.offset + paginacao.limit]
        return Pagina[int].criar(pagina, TOTAL_DE_ITENS, paginacao)

    return TestClient(app)


def test_usa_page_1_e_limit_10_por_padrao(cliente):
    corpo = cliente.get("/teste/numeros").json()

    assert corpo["dados"] == list(range(10))
    assert corpo["paginacao"] == {"page": 1, "limit": 10, "total": 25, "totalPaginas": 3}


def test_ultima_pagina_traz_o_resto(cliente):
    corpo = cliente.get("/teste/numeros?page=3&limit=10").json()

    assert corpo["dados"] == [20, 21, 22, 23, 24]


def test_aceita_limit_maximo(cliente):
    assert cliente.get("/teste/numeros?limit=100").status_code == 200


@pytest.mark.parametrize(
    ("query", "campo", "problema"),
    [
        ("limit=0", "limit", "Deve ser maior ou igual a 1"),
        ("limit=101", "limit", "Deve ser menor ou igual a 100"),
        ("page=-1", "page", "Deve ser maior ou igual a 1"),
        ("page=abc", "page", "Deve ser um número inteiro"),
        ("page=1000001", "page", "Deve ser menor ou igual a 1000000"),
    ],
)
def test_rejeita_page_e_limit_fora_da_faixa(cliente, query, campo, problema):
    resposta = cliente.get(f"/teste/numeros?{query}")

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [{"field": campo, "issue": problema}]


def test_offset_pula_as_paginas_anteriores():
    assert ParametrosPaginacao(page=3, limit=10).offset == 20


def test_lista_vazia_tem_zero_paginas():
    pagina = Pagina[int].criar([], 0, ParametrosPaginacao(page=1, limit=10))

    assert pagina.paginacao.total_paginas == 0
