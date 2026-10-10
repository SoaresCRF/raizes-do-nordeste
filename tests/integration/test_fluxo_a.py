from decimal import Decimal

import pytest
from sqlalchemy import select

from src.infrastructure.database.seeds.dados_iniciais import DOMINIO_EMAIL
from src.infrastructure.database.tabelas import (
    item_pedido,
    movimentacao_estoque,
    pagamento,
    pedido,
)

UNIDADE_RECIFE = 1
TAPIOCA = 1
QUANTIDADE = 2
# 2 tapiocas de R$ 18,90 = R$ 37,80, que rendem 37 pontos (RN18).
PONTOS_DO_PEDIDO = 37
CANAIS_DO_CLIENTE = ["APP", "TOTEM", "PICKUP", "WEB"]
EMAIL_GERENTE_RECIFE = f"gerente.recife@{DOMINIO_EMAIL}"
EMAIL_ATENDENTE_RECIFE = f"atendente.recife@{DOMINIO_EMAIL}"
EMAIL_COZINHA_RECIFE = f"cozinha.recife@{DOMINIO_EMAIL}"
EMAIL_CLIENTE = f"cliente@{DOMINIO_EMAIL}"


def _consultar(cliente_http, headers: dict, pedido_id: int) -> dict:
    resposta = cliente_http.get(f"/pedidos/{pedido_id}", headers=headers)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _preco_no_cardapio(cliente_http, produto_id: int) -> float:
    resposta = cliente_http.get(f"/unidades/{UNIDADE_RECIFE}/cardapio?limit=100")
    assert resposta.status_code == 200, resposta.text
    item = next(item for item in resposta.json()["dados"] if item["produtoId"] == produto_id)
    assert item["disponivel"] is True
    return item["preco"]


def _mudar_status(cliente_http, headers: dict, pedido_id: int, status: str) -> dict:
    resposta = cliente_http.patch(
        f"/pedidos/{pedido_id}/status", json={"status": status}, headers=headers
    )
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _conferir_passo(
    cliente_http, saldo_pela_api, headers: dict, pedido_id: int, status: str, saldo: int
) -> None:
    assert _consultar(cliente_http, headers, pedido_id)["status"] == status
    assert saldo_pela_api(UNIDADE_RECIFE, TAPIOCA) == saldo


def _percorrer_fluxo_a(
    cliente_http, entrar, saldo_pela_api, pagar_pedido, headers: dict, canal: str
) -> int:
    saldo_depois_do_pedido = saldo_pela_api(UNIDADE_RECIFE, TAPIOCA) - QUANTIDADE
    preco = _preco_no_cardapio(cliente_http, TAPIOCA)

    resposta = cliente_http.post(
        "/pedidos",
        json={
            "canalPedido": canal,
            "unidadeId": UNIDADE_RECIFE,
            "itens": [{"produtoId": TAPIOCA, "quantidade": QUANTIDADE}],
            "formaPagamento": "MOCK",
        },
        headers=headers,
    )
    assert resposta.status_code == 201, resposta.text
    criado = resposta.json()
    pedido_id = criado["pedidoId"]
    assert (criado["status"], criado["canalPedido"]) == ("AGUARDANDO_PAGAMENTO", canal)
    assert criado["total"] == round(preco * QUANTIDADE, 2)
    _conferir_passo(
        cliente_http,
        saldo_pela_api,
        headers,
        pedido_id,
        "AGUARDANDO_PAGAMENTO",
        saldo_depois_do_pedido,
    )

    pago = pagar_pedido(pedido_id, headers)
    assert (pago["status"], pago["statusPedido"]) == ("APROVADO", "EM_PREPARO")
    _conferir_passo(
        cliente_http, saldo_pela_api, headers, pedido_id, "EM_PREPARO", saldo_depois_do_pedido
    )

    pronto = _mudar_status(cliente_http, entrar(EMAIL_COZINHA_RECIFE), pedido_id, "PRONTO")
    assert pronto["statusAnterior"] == "EM_PREPARO"
    _conferir_passo(
        cliente_http, saldo_pela_api, headers, pedido_id, "PRONTO", saldo_depois_do_pedido
    )

    entregue = _mudar_status(cliente_http, entrar(EMAIL_ATENDENTE_RECIFE), pedido_id, "ENTREGUE")
    assert entregue["statusAnterior"] == "PRONTO"
    _conferir_passo(
        cliente_http, saldo_pela_api, headers, pedido_id, "ENTREGUE", saldo_depois_do_pedido
    )

    assert _consultar(cliente_http, headers, pedido_id)["ultimoPagamento"]["status"] == "APROVADO"
    return pedido_id


def _listar_por_canal(cliente_http, entrar, canal: str) -> list[dict]:
    resposta = cliente_http.get(
        f"/pedidos?canalPedido={canal}&limit=100", headers=entrar(EMAIL_GERENTE_RECIFE)
    )
    assert resposta.status_code == 200, resposta.text
    return resposta.json()["dados"]


@pytest.mark.parametrize("canal", CANAIS_DO_CLIENTE)
def test_fluxo_a_do_cliente_em_cada_canal(
    cliente_http,
    entrar,
    entrar_como_cliente,
    cliente_novo,
    saldo_pela_api,
    pagar_pedido,
    saldo_de_pontos,
    canal,
):
    headers = entrar_como_cliente(cliente_novo)

    pedido_id = _percorrer_fluxo_a(
        cliente_http, entrar, saldo_pela_api, pagar_pedido, headers, canal
    )

    assert saldo_de_pontos(headers) == PONTOS_DO_PEDIDO
    listados = _listar_por_canal(cliente_http, entrar, canal)
    assert pedido_id in [listado["pedidoId"] for listado in listados]
    assert {listado["canalPedido"] for listado in listados} == {canal}


def test_fluxo_a_no_balcao(cliente_http, entrar, saldo_pela_api, pagar_pedido):
    headers = entrar(EMAIL_ATENDENTE_RECIFE)

    pedido_id = _percorrer_fluxo_a(
        cliente_http, entrar, saldo_pela_api, pagar_pedido, headers, "BALCAO"
    )

    detalhado = _consultar(cliente_http, headers, pedido_id)
    assert (detalhado["clienteId"], detalhado["cliente"]) == (None, None)
    listados = _listar_por_canal(cliente_http, entrar, "BALCAO")
    assert pedido_id in [listado["pedidoId"] for listado in listados]
    assert {listado["canalPedido"] for listado in listados} == {"BALCAO"}


def test_fluxo_a_fica_persistido_no_banco(
    cliente_http, entrar, saldo_pela_api, pagar_pedido, banco_semeado, id_do_usuario
):
    pedido_id = _percorrer_fluxo_a(
        cliente_http, entrar, saldo_pela_api, pagar_pedido, entrar(EMAIL_CLIENTE), "APP"
    )

    with banco_semeado.connect() as conexao:
        registro = conexao.execute(
            select(
                pedido.c.status, pedido.c.canal_pedido, pedido.c.cliente_id, pedido.c.total
            ).where(pedido.c.id == pedido_id)
        ).one()
        itens = conexao.execute(
            select(
                item_pedido.c.produto_id, item_pedido.c.quantidade, item_pedido.c.preco_unitario
            ).where(item_pedido.c.pedido_id == pedido_id)
        ).all()
        pagamentos = conexao.execute(
            select(pagamento.c.status, pagamento.c.valor, pagamento.c.transacao_externa_id).where(
                pagamento.c.pedido_id == pedido_id
            )
        ).all()
        movimentacoes = conexao.execute(
            select(
                movimentacao_estoque.c.tipo,
                movimentacao_estoque.c.quantidade,
                movimentacao_estoque.c.motivo,
            ).where(movimentacao_estoque.c.pedido_id == pedido_id)
        ).all()
    assert tuple(registro) == ("ENTREGUE", "APP", id_do_usuario(EMAIL_CLIENTE), Decimal("37.80"))
    assert [tuple(item) for item in itens] == [(TAPIOCA, QUANTIDADE, Decimal("18.90"))]
    assert [(p.status, p.valor) for p in pagamentos] == [("APROVADO", Decimal("37.80"))]
    assert pagamentos[0].transacao_externa_id.startswith("MOCK-")
    assert [tuple(m) for m in movimentacoes] == [("SAIDA", QUANTIDADE, f"Pedido {pedido_id}")]


def _auditoria(cliente_http, headers: dict, entidade: str, entidade_id: int) -> list[dict]:
    resposta = cliente_http.get(
        f"/auditoria?entidade={entidade}&entidadeId={entidade_id}&unidadeId={UNIDADE_RECIFE}",
        headers=headers,
    )
    assert resposta.status_code == 200, resposta.text
    return resposta.json()["dados"]


def test_fluxo_a_deixa_a_trilha_completa_na_auditoria(
    cliente_http, entrar, saldo_pela_api, pagar_pedido, id_do_usuario
):
    headers_cliente = entrar(EMAIL_CLIENTE)
    pedido_id = _percorrer_fluxo_a(
        cliente_http, entrar, saldo_pela_api, pagar_pedido, headers_cliente, "APP"
    )
    pagamento_id = _consultar(cliente_http, headers_cliente, pedido_id)["ultimoPagamento"][
        "pagamentoId"
    ]
    gerente = entrar(EMAIL_GERENTE_RECIFE)

    trilha_do_pedido = _auditoria(cliente_http, gerente, "Pedido", pedido_id)
    trilha_do_pagamento = _auditoria(cliente_http, gerente, "Pagamento", pagamento_id)

    assert [
        (registro["acao"], registro["usuarioId"], registro["dadosDepois"]["status"])
        for registro in trilha_do_pedido
    ] == [
        ("STATUS_ALTERADO", id_do_usuario(EMAIL_ATENDENTE_RECIFE), "ENTREGUE"),
        ("STATUS_ALTERADO", id_do_usuario(EMAIL_COZINHA_RECIFE), "PRONTO"),
        ("STATUS_ALTERADO", id_do_usuario(EMAIL_CLIENTE), "EM_PREPARO"),
        ("PEDIDO_CRIADO", id_do_usuario(EMAIL_CLIENTE), "AGUARDANDO_PAGAMENTO"),
    ]
    assert [(registro["acao"], registro["dadosDepois"]) for registro in trilha_do_pagamento] == [
        ("PAGAMENTO_REGISTRADO", {"pedidoId": pedido_id, "status": "APROVADO", "valor": "37.80"})
    ]
    assert all(registro["requestId"] for registro in trilha_do_pedido + trilha_do_pagamento)
