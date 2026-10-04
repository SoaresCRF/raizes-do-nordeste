from typing import Annotated

import pytest
from fastapi import Query
from fastapi.testclient import TestClient
from pydantic import Field

from src.api.erros import STATUS_POR_ERRO
from src.api.schemas.base import EsquemaEntrada
from src.api.validacao import detalhes_de_validacao
from src.domain.erros.erros import (
    DetalheErro,
    ErroDominio,
    EstoqueInsuficiente,
    RecursoNaoEncontrado,
)
from src.domain.pedido.pedido import CanalPedido

PEDIDO_VALIDO = {"canalPedido": "TOTEM", "itens": [{"produtoId": 1, "quantidade": 2}]}


class ItemTeste(EsquemaEntrada):
    produto_id: int
    quantidade: int = Field(gt=0)


class PedidoTeste(EsquemaEntrada):
    canal_pedido: CanalPedido
    itens: list[ItemTeste]


@pytest.fixture
def cliente(app):
    @app.post("/teste/pedidos")
    def criar_pedido(pedido: PedidoTeste):
        return {"canalPedido": pedido.canal_pedido}

    @app.get("/teste/pedidos/{pedido_id}")
    def obter_pedido(pedido_id: int):
        raise RecursoNaoEncontrado(f"Pedido {pedido_id} não encontrado")

    @app.post("/teste/estoque/saidas")
    def registrar_saida():
        raise EstoqueInsuficiente(
            "Não há quantidade suficiente para um ou mais itens.",
            [DetalheErro("itens[0].quantidade", "Disponível: 1")],
        )

    @app.get("/teste/estoque")
    def consultar_estoque(limit: Annotated[int, Query(ge=1)]):
        return {"limit": limit}

    return TestClient(app)


def _detalhes(resposta) -> list[dict]:
    return resposta.json()["details"]


def test_aceita_body_valido_em_camel_case(cliente):
    resposta = cliente.post("/teste/pedidos", json=PEDIDO_VALIDO)

    assert resposta.status_code == 200
    assert resposta.json() == {"canalPedido": "TOTEM"}


def test_erro_de_dominio_usa_status_do_catalogo_e_formato_padrao(cliente):
    resposta = cliente.post("/teste/estoque/saidas")
    corpo = resposta.json()

    assert resposta.status_code == 409
    assert corpo["error"] == "ESTOQUE_INSUFICIENTE"
    assert corpo["message"] == "Não há quantidade suficiente para um ou mais itens."
    assert corpo["details"] == [{"field": "itens[0].quantidade", "issue": "Disponível: 1"}]
    assert corpo["path"] == "/teste/estoque/saidas"
    assert corpo["requestId"]


def test_recurso_nao_encontrado_devolve_404_com_o_id(cliente):
    resposta = cliente.get("/teste/pedidos/9001")

    assert resposta.status_code == 404
    assert resposta.json()["error"] == "RECURSO_NAO_ENCONTRADO"
    assert resposta.json()["message"] == "Pedido 9001 não encontrado"


def test_todo_erro_de_dominio_tem_status_http():
    assert set(ErroDominio.__subclasses__()) == set(STATUS_POR_ERRO)


def test_codigos_dos_erros_de_dominio_sao_unicos():
    codigos = [erro.codigo for erro in ErroDominio.__subclasses__()]

    assert len(codigos) == len(set(codigos))


def test_json_malformado_devolve_400(cliente):
    resposta = cliente.post(
        "/teste/pedidos",
        content=b'{"canalPedido": ',
        headers={"Content-Type": "application/json"},
    )

    assert resposta.status_code == 400
    assert resposta.json()["error"] == "JSON_INVALIDO"
    assert resposta.json()["details"] == []


def test_campo_obrigatorio_ausente_devolve_422_com_o_campo(cliente):
    resposta = cliente.post("/teste/pedidos", json={"itens": PEDIDO_VALIDO["itens"]})

    assert resposta.status_code == 422
    assert resposta.json()["error"] == "VALIDACAO_FALHOU"
    assert _detalhes(resposta) == [{"field": "canalPedido", "issue": "Campo obrigatório"}]


def test_campo_nao_previsto_no_body_e_rejeitado(cliente):
    resposta = cliente.post("/teste/pedidos", json=PEDIDO_VALIDO | {"desconto": 10})

    assert resposta.status_code == 422
    assert _detalhes(resposta) == [{"field": "desconto", "issue": "Campo não permitido"}]


def test_nome_de_campo_em_snake_case_e_rejeitado(cliente):
    corpo = {"canal_pedido": "TOTEM", "itens": PEDIDO_VALIDO["itens"]}

    resposta = cliente.post("/teste/pedidos", json=corpo)

    assert resposta.status_code == 422
    assert {"field": "canalPedido", "issue": "Campo obrigatório"} in _detalhes(resposta)
    assert {"field": "canal_pedido", "issue": "Campo não permitido"} in _detalhes(resposta)


def test_campo_aninhado_aponta_o_indice_do_item(cliente):
    corpo = PEDIDO_VALIDO | {"itens": [{"produtoId": 1, "quantidade": 0}]}

    resposta = cliente.post("/teste/pedidos", json=corpo)

    assert _detalhes(resposta) == [
        {"field": "itens[0].quantidade", "issue": "Deve ser maior que 0"}
    ]


def test_valor_fora_do_enum_lista_as_opcoes_em_portugues(cliente):
    resposta = cliente.post("/teste/pedidos", json=PEDIDO_VALIDO | {"canalPedido": "FAX"})

    [detalhe] = _detalhes(resposta)
    assert detalhe["field"] == "canalPedido"
    assert detalhe["issue"].startswith("Deve ser um destes valores: 'APP'")
    assert detalhe["issue"].endswith("'PICKUP' ou 'WEB'")


def test_query_param_invalido_aponta_o_parametro(cliente):
    resposta = cliente.get("/teste/estoque?limit=abc")

    assert resposta.status_code == 422
    assert _detalhes(resposta) == [{"field": "limit", "issue": "Deve ser um número inteiro"}]


def test_body_ausente_aponta_o_body(cliente):
    resposta = cliente.post("/teste/pedidos")

    assert resposta.status_code == 422
    assert _detalhes(resposta) == [{"field": "body", "issue": "Campo obrigatório"}]


def test_rota_inexistente_devolve_404_no_formato_padrao(cliente):
    resposta = cliente.get("/nao-existe")

    assert resposta.status_code == 404
    assert resposta.json()["error"] == "RECURSO_NAO_ENCONTRADO"
    assert resposta.json()["message"] == "Rota /nao-existe não encontrada"
    assert resposta.json()["path"] == "/nao-existe"


def test_metodo_nao_permitido_devolve_405_no_formato_padrao(cliente):
    resposta = cliente.delete("/teste/pedidos")

    assert resposta.status_code == 405
    assert resposta.json()["error"] == "METODO_NAO_PERMITIDO"
    assert resposta.json()["message"] == "Método DELETE não permitido em /teste/pedidos"


def test_tipo_de_erro_sem_traducao_usa_problema_generico():
    erros = [{"type": "url_parsing", "loc": ("body", "site"), "msg": "Input should be a valid URL"}]

    assert [detalhe.model_dump() for detalhe in detalhes_de_validacao(erros)] == [
        {"field": "site", "issue": "Valor inválido"}
    ]
