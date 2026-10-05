import re

import pytest

from src.infrastructure.database.seeds.dados_iniciais import DOMINIO_EMAIL

URL_SALDO = "/fidelidade/saldo"
URL_HISTORICO = "/fidelidade/historico"
FORMATO_DATA_HORA_UTC = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"
EMAIL_ADMIN = f"admin@{DOMINIO_EMAIL}"
EMAIL_GERENTE_RECIFE = f"gerente.recife@{DOMINIO_EMAIL}"
EMAIL_ATENDENTE_RECIFE = f"atendente.recife@{DOMINIO_EMAIL}"


def test_cliente_novo_comeca_sem_pontos(cliente_http, entrar_como_cliente, cliente_novo):
    resposta = cliente_http.get(URL_SALDO, headers=entrar_como_cliente(cliente_novo))

    assert resposta.status_code == 200
    assert resposta.json() == {"saldoPontos": 0, "valorEquivalente": 0}


def test_saldo_aumenta_com_o_pagamento_aprovado(
    cliente_http, entrar_como_cliente, cliente_novo, acumular_pontos
):
    acumular_pontos(cliente_novo, 3)

    resposta = cliente_http.get(URL_SALDO, headers=entrar_como_cliente(cliente_novo))

    assert resposta.json() == {"saldoPontos": 149, "valorEquivalente": 5.0}


def test_pagamento_recusado_nao_altera_o_saldo(
    entrar_como_cliente, cliente_novo, fazer_pedido, pagar_pedido, saldo_de_pontos
):
    headers = entrar_como_cliente(cliente_novo)
    pedido_id = fazer_pedido(cliente_novo["email"], cliente_novo["senha"])["pedidoId"]

    pagar_pedido(pedido_id, headers, "RECUSADO")

    assert saldo_de_pontos(headers) == 0


@pytest.mark.parametrize("email", [EMAIL_ATENDENTE_RECIFE, EMAIL_GERENTE_RECIFE, EMAIL_ADMIN])
def test_funcionario_nao_consulta_saldo_de_pontos(cliente_http, entrar, email):
    resposta = cliente_http.get(URL_SALDO, headers=entrar(email))

    assert (resposta.status_code, resposta.json()["error"]) == (403, "ACESSO_NEGADO")


def test_saldo_sem_token_devolve_401(cliente_http):
    assert cliente_http.get(URL_SALDO).status_code == 401


def test_historico_lista_as_transacoes_mais_recentes_primeiro(
    cliente_http, entrar_como_cliente, cliente_novo, acumular_pontos
):
    primeiro = acumular_pontos(cliente_novo, 1)
    segundo = acumular_pontos(cliente_novo, 2)

    resposta = cliente_http.get(URL_HISTORICO, headers=entrar_como_cliente(cliente_novo))
    corpo = resposta.json()

    assert resposta.status_code == 200
    assert [(t["tipo"], t["pontos"], t["pedidoId"]) for t in corpo["dados"]] == [
        ("ACUMULO", 99, segundo),
        ("ACUMULO", 49, primeiro),
    ]
    assert set(corpo["dados"][0]) == {"transacaoId", "tipo", "pontos", "pedidoId", "createdAt"}
    assert re.fullmatch(FORMATO_DATA_HORA_UTC, corpo["dados"][0]["createdAt"])
    assert corpo["paginacao"] == {"page": 1, "limit": 10, "total": 2, "totalPaginas": 1}


def test_historico_paginado(cliente_http, entrar_como_cliente, cliente_novo, acumular_pontos):
    acumular_pontos(cliente_novo, 1)
    acumular_pontos(cliente_novo, 1)

    resposta = cliente_http.get(
        f"{URL_HISTORICO}?page=2&limit=1", headers=entrar_como_cliente(cliente_novo)
    )

    assert len(resposta.json()["dados"]) == 1
    assert resposta.json()["paginacao"] == {"page": 2, "limit": 1, "total": 2, "totalPaginas": 2}


def test_historico_mostra_so_as_transacoes_do_cliente(
    cliente_http, entrar, entrar_como_cliente, cliente_novo, fazer_pedido, pagar_pedido
):
    pagar_pedido(fazer_pedido()["pedidoId"], entrar(f"cliente@{DOMINIO_EMAIL}"))

    resposta = cliente_http.get(URL_HISTORICO, headers=entrar_como_cliente(cliente_novo))

    assert resposta.json()["dados"] == []
    assert resposta.json()["paginacao"]["total"] == 0


def test_historico_com_limit_invalido_devolve_422(cliente_http, entrar_como_cliente, cliente_novo):
    resposta = cliente_http.get(
        f"{URL_HISTORICO}?limit=0", headers=entrar_como_cliente(cliente_novo)
    )

    assert resposta.status_code == 422


def test_atendente_nao_consulta_historico(cliente_http, entrar):
    assert (
        cliente_http.get(URL_HISTORICO, headers=entrar(EMAIL_ATENDENTE_RECIFE)).status_code == 403
    )


def test_historico_sem_token_devolve_401(cliente_http):
    assert cliente_http.get(URL_HISTORICO).status_code == 401
