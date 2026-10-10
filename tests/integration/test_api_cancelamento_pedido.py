import pytest
from sqlalchemy import select

from src.infrastructure.database.seeds.dados_iniciais import DOMINIO_EMAIL
from src.infrastructure.database.tabelas import (
    log_auditoria,
    movimentacao_estoque,
    pagamento,
    pedido,
)

URL = "/pedidos"
UNIDADE_RECIFE = 1
INEXISTENTE = 9999
TAPIOCA = 1
CAFE_PASSADO = 6
CAFE_COMPLETO = 5
MOTIVO = "Cliente desistiu"
EMAIL_ADMIN = f"admin@{DOMINIO_EMAIL}"
EMAIL_GERENTE_RECIFE = f"gerente.recife@{DOMINIO_EMAIL}"
EMAIL_GERENTE_CARUARU = f"gerente.caruaru@{DOMINIO_EMAIL}"
EMAIL_ATENDENTE_RECIFE = f"atendente.recife@{DOMINIO_EMAIL}"
EMAIL_COZINHA_RECIFE = f"cozinha.recife@{DOMINIO_EMAIL}"
EMAIL_CLIENTE = f"cliente@{DOMINIO_EMAIL}"
EMAIL_CLIENTE_SEM_CONSENTIMENTO = f"cliente.sem.consentimento@{DOMINIO_EMAIL}"


def _cancelar(cliente_http, headers: dict, pedido_id: int, motivo: str = MOTIVO):
    return cliente_http.post(
        f"{URL}/{pedido_id}/cancelamento", json={"motivo": motivo}, headers=headers
    )


def _status(banco_semeado, pedido_id: int) -> str:
    with banco_semeado.connect() as conexao:
        return conexao.execute(select(pedido.c.status).where(pedido.c.id == pedido_id)).scalar_one()


def test_cliente_cancela_pedido_aguardando_pagamento(cliente_http, entrar, fazer_pedido):
    pedido_id = fazer_pedido()["pedidoId"]

    resposta = _cancelar(cliente_http, entrar(EMAIL_CLIENTE), pedido_id)

    assert resposta.status_code == 200
    assert resposta.json() == {
        "pedidoId": pedido_id,
        "status": "CANCELADO",
        "motivoCancelamento": MOTIVO,
        "pagamentoEstornado": False,
    }


def test_cancelamento_devolve_o_estoque_com_entradas_vinculadas(
    cliente_http, entrar, fazer_pedido, banco_semeado, saldo_de_estoque
):
    anterior = saldo_de_estoque(UNIDADE_RECIFE, TAPIOCA)
    pedido_id = fazer_pedido(itens=[{"produtoId": TAPIOCA, "quantidade": 3}])["pedidoId"]

    _cancelar(cliente_http, entrar(EMAIL_CLIENTE), pedido_id)

    assert saldo_de_estoque(UNIDADE_RECIFE, TAPIOCA) == anterior
    with banco_semeado.connect() as conexao:
        entradas = conexao.execute(
            select(
                movimentacao_estoque.c.tipo,
                movimentacao_estoque.c.quantidade,
                movimentacao_estoque.c.motivo,
            ).where(
                movimentacao_estoque.c.pedido_id == pedido_id,
                movimentacao_estoque.c.tipo == "ENTRADA",
            )
        ).all()
    assert [tuple(entrada) for entrada in entradas] == [
        ("ENTRADA", 3, f"Cancelamento do pedido {pedido_id}")
    ]


def test_cancelamento_fica_auditado(
    cliente_http, entrar, fazer_pedido, banco_semeado, id_do_usuario
):
    pedido_id = fazer_pedido()["pedidoId"]

    _cancelar(cliente_http, entrar(EMAIL_CLIENTE), pedido_id)

    with banco_semeado.connect() as conexao:
        auditoria = conexao.execute(
            select(log_auditoria).where(
                log_auditoria.c.acao == "PEDIDO_CANCELADO",
                log_auditoria.c.entidade_id == pedido_id,
            )
        ).one()
    assert (auditoria.entidade, auditoria.usuario_id, auditoria.unidade_id) == (
        "Pedido",
        id_do_usuario(EMAIL_CLIENTE),
        UNIDADE_RECIFE,
    )
    assert auditoria.dados_antes == {"status": "AGUARDANDO_PAGAMENTO"}
    assert auditoria.dados_depois == {"status": "CANCELADO", "motivoCancelamento": MOTIVO}


def test_atendente_cancela_pedido_aguardando_pagamento(cliente_http, entrar, fazer_pedido):
    pedido_id = fazer_pedido()["pedidoId"]

    resposta = _cancelar(cliente_http, entrar(EMAIL_ATENDENTE_RECIFE), pedido_id)

    assert resposta.status_code == 200


@pytest.mark.parametrize("email", [EMAIL_GERENTE_RECIFE, EMAIL_ADMIN])
def test_gerencia_cancela_pedido_em_preparo(
    cliente_http, entrar, fazer_pedido, definir_status_do_pedido, saldo_de_estoque, email
):
    anterior = saldo_de_estoque(UNIDADE_RECIFE, TAPIOCA)
    pedido_id = fazer_pedido()["pedidoId"]
    definir_status_do_pedido(pedido_id, "EM_PREPARO")

    resposta = _cancelar(cliente_http, entrar(email), pedido_id)

    assert resposta.status_code == 200
    assert saldo_de_estoque(UNIDADE_RECIFE, TAPIOCA) == anterior


@pytest.mark.parametrize("email", [EMAIL_CLIENTE, EMAIL_ATENDENTE_RECIFE])
def test_cliente_e_atendente_nao_cancelam_pedido_em_preparo(
    cliente_http, entrar, fazer_pedido, definir_status_do_pedido, banco_semeado, email
):
    pedido_id = fazer_pedido()["pedidoId"]
    definir_status_do_pedido(pedido_id, "EM_PREPARO")

    resposta = _cancelar(cliente_http, entrar(email), pedido_id)

    assert resposta.status_code == 403
    assert _status(banco_semeado, pedido_id) == "EM_PREPARO"


def test_pedido_entregue_nao_e_cancelado(
    cliente_http, entrar, fazer_pedido, definir_status_do_pedido, saldo_de_estoque
):
    pedido_id = fazer_pedido()["pedidoId"]
    definir_status_do_pedido(pedido_id, "EM_PREPARO")
    pronto = cliente_http.patch(
        f"{URL}/{pedido_id}/status", json={"status": "PRONTO"}, headers=entrar(EMAIL_COZINHA_RECIFE)
    )
    entregue = cliente_http.patch(
        f"{URL}/{pedido_id}/status",
        json={"status": "ENTREGUE"},
        headers=entrar(EMAIL_ATENDENTE_RECIFE),
    )
    assert pronto.status_code == 200
    assert entregue.status_code == 200
    saldo = saldo_de_estoque(UNIDADE_RECIFE, TAPIOCA)

    resposta = _cancelar(cliente_http, entrar(EMAIL_GERENTE_RECIFE), pedido_id)

    assert resposta.status_code == 409
    assert resposta.json()["error"] == "TRANSICAO_STATUS_INVALIDA"
    assert saldo_de_estoque(UNIDADE_RECIFE, TAPIOCA) == saldo


@pytest.mark.parametrize("status", ["PRONTO", "CANCELADO"])
def test_pedido_pronto_ou_cancelado_nao_e_cancelado(
    cliente_http, entrar, fazer_pedido, definir_status_do_pedido, status
):
    pedido_id = fazer_pedido()["pedidoId"]
    definir_status_do_pedido(pedido_id, status)

    resposta = _cancelar(cliente_http, entrar(EMAIL_ADMIN), pedido_id)

    assert resposta.status_code == 409


def test_cliente_nao_cancela_pedido_de_outro_cliente(
    cliente_http, entrar, fazer_pedido, banco_semeado
):
    pedido_id = fazer_pedido(EMAIL_CLIENTE_SEM_CONSENTIMENTO)["pedidoId"]

    resposta = _cancelar(cliente_http, entrar(EMAIL_CLIENTE), pedido_id)

    assert resposta.status_code == 404
    assert _status(banco_semeado, pedido_id) == "AGUARDANDO_PAGAMENTO"


def test_funcionario_de_outra_unidade_recebe_403(cliente_http, entrar, fazer_pedido):
    pedido_id = fazer_pedido()["pedidoId"]

    resposta = _cancelar(cliente_http, entrar(EMAIL_GERENTE_CARUARU), pedido_id)

    assert resposta.status_code == 403


def test_cozinha_recebe_403_mesmo_com_motivo_invalido(cliente_http, entrar, fazer_pedido):
    pedido_id = fazer_pedido()["pedidoId"]

    resposta = _cancelar(cliente_http, entrar(EMAIL_COZINHA_RECIFE), pedido_id, motivo="")

    assert resposta.status_code == 403


@pytest.mark.parametrize(
    ("motivo", "problema"),
    [
        ("   ", "Deve ter pelo menos 1 caractere(s)"),
        ("x" * 201, "Deve ter no máximo 200 caracteres"),
    ],
)
def test_motivo_invalido_devolve_422(cliente_http, entrar, fazer_pedido, motivo, problema):
    pedido_id = fazer_pedido()["pedidoId"]

    resposta = _cancelar(cliente_http, entrar(EMAIL_CLIENTE), pedido_id, motivo=motivo)

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [{"field": "motivo", "issue": problema}]


def test_cancelamento_sem_motivo_devolve_422(cliente_http, entrar, fazer_pedido):
    pedido_id = fazer_pedido()["pedidoId"]

    resposta = cliente_http.post(
        f"{URL}/{pedido_id}/cancelamento", json={}, headers=entrar(EMAIL_CLIENTE)
    )

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [{"field": "motivo", "issue": "Campo obrigatório"}]


def test_produto_desativado_depois_do_pedido_volta_ao_estoque(
    cliente_http, entrar, fazer_pedido, saldo_de_estoque
):
    anterior = saldo_de_estoque(UNIDADE_RECIFE, CAFE_PASSADO)
    pedido_id = fazer_pedido(itens=[{"produtoId": CAFE_PASSADO, "quantidade": 2}])["pedidoId"]
    cliente_http.delete(f"/produtos/{CAFE_PASSADO}", headers=entrar(EMAIL_ADMIN))

    resposta = _cancelar(cliente_http, entrar(EMAIL_CLIENTE), pedido_id)

    assert resposta.status_code == 200
    assert saldo_de_estoque(UNIDADE_RECIFE, CAFE_PASSADO) == anterior


def test_pedido_inexistente_devolve_404(cliente_http, entrar):
    resposta = _cancelar(cliente_http, entrar(EMAIL_ADMIN), INEXISTENTE)

    assert resposta.status_code == 404


def test_cancelamento_sem_token_devolve_401(cliente_http):
    resposta = cliente_http.post(f"{URL}/1/cancelamento", json={"motivo": MOTIVO})

    assert resposta.status_code == 401


def _status_do_pagamento(banco_semeado, pedido_id: int) -> str:
    with banco_semeado.connect() as conexao:
        return conexao.execute(
            select(pagamento.c.status).where(pagamento.c.pedido_id == pedido_id)
        ).scalar_one()


def test_gerente_cancela_pedido_pago_com_estorno(
    cliente_http,
    entrar,
    entrar_como_cliente,
    cliente_novo,
    acumular_pontos,
    saldo_de_pontos,
    saldo_de_estoque,
    banco_semeado,
):
    estoque_antes = saldo_de_estoque(UNIDADE_RECIFE, CAFE_COMPLETO)
    pedido_id = acumular_pontos(cliente_novo, 3)

    resposta = _cancelar(cliente_http, entrar(EMAIL_GERENTE_RECIFE), pedido_id)

    assert resposta.status_code == 200
    assert resposta.json() == {
        "pedidoId": pedido_id,
        "status": "CANCELADO",
        "motivoCancelamento": MOTIVO,
        "pagamentoEstornado": True,
    }
    assert _status_do_pagamento(banco_semeado, pedido_id) == "ESTORNADO"
    assert saldo_de_pontos(entrar_como_cliente(cliente_novo)) == 0
    assert saldo_de_estoque(UNIDADE_RECIFE, CAFE_COMPLETO) == estoque_antes


def test_estorno_do_pagamento_fica_auditado(
    cliente_http, entrar, cliente_novo, acumular_pontos, banco_semeado, id_do_usuario
):
    pedido_id = acumular_pontos(cliente_novo, 1)

    _cancelar(cliente_http, entrar(EMAIL_GERENTE_RECIFE), pedido_id)

    with banco_semeado.connect() as conexao:
        pagamento_id = conexao.execute(
            select(pagamento.c.id).where(pagamento.c.pedido_id == pedido_id)
        ).scalar_one()
        auditoria = conexao.execute(
            select(log_auditoria).where(
                log_auditoria.c.acao == "PAGAMENTO_ESTORNADO",
                log_auditoria.c.entidade_id == pagamento_id,
            )
        ).one()
    assert (auditoria.entidade, auditoria.usuario_id, auditoria.unidade_id) == (
        "Pagamento",
        id_do_usuario(EMAIL_GERENTE_RECIFE),
        UNIDADE_RECIFE,
    )
    assert (auditoria.dados_antes, auditoria.dados_depois) == (
        {"status": "APROVADO"},
        {"status": "ESTORNADO"},
    )


def test_falha_do_gateway_no_estorno_nao_cancela_nada(
    cliente_http,
    entrar,
    entrar_como_cliente,
    cliente_novo,
    acumular_pontos,
    saldo_de_pontos,
    saldo_de_estoque,
    banco_semeado,
):
    pedido_id = acumular_pontos(cliente_novo, 1)
    estoque_antes = saldo_de_estoque(UNIDADE_RECIFE, CAFE_COMPLETO)

    resposta = cliente_http.post(
        f"{URL}/{pedido_id}/cancelamento",
        json={"motivo": MOTIVO},
        headers=entrar(EMAIL_GERENTE_RECIFE) | {"X-Simular-Resultado": "ERRO"},
    )

    assert resposta.status_code == 503
    assert resposta.json()["error"] == "GATEWAY_PAGAMENTO_INDISPONIVEL"
    assert resposta.json()["message"] == (
        f"Gateway de pagamento indisponível; pedido {pedido_id} não foi cancelado"
    )
    assert _status(banco_semeado, pedido_id) == "EM_PREPARO"
    assert _status_do_pagamento(banco_semeado, pedido_id) == "APROVADO"
    assert saldo_de_pontos(entrar_como_cliente(cliente_novo)) == 49
    assert saldo_de_estoque(UNIDADE_RECIFE, CAFE_COMPLETO) == estoque_antes


def test_timeout_no_estorno_nao_cancela_nada(
    cliente_http, entrar, cliente_novo, acumular_pontos, banco_semeado
):
    pedido_id = acumular_pontos(cliente_novo, 1)

    resposta = cliente_http.post(
        f"{URL}/{pedido_id}/cancelamento",
        json={"motivo": MOTIVO},
        headers=entrar(EMAIL_GERENTE_RECIFE) | {"X-Simular-Resultado": "TIMEOUT"},
    )

    assert resposta.status_code == 503
    assert resposta.json()["error"] == "GATEWAY_PAGAMENTO_INDISPONIVEL"
    assert _status(banco_semeado, pedido_id) == "EM_PREPARO"
    assert _status_do_pagamento(banco_semeado, pedido_id) == "APROVADO"


def test_cancelamento_devolve_os_pontos_resgatados(
    cliente_http, entrar_como_cliente, cliente_novo, acumular_pontos, fazer_pedido, saldo_de_pontos
):
    headers = entrar_como_cliente(cliente_novo)
    acumular_pontos(cliente_novo, 3)
    pedido_id = fazer_pedido(cliente_novo["email"], cliente_novo["senha"])["pedidoId"]
    resgate = cliente_http.post(
        "/fidelidade/resgates", json={"pedidoId": pedido_id, "pontos": 100}, headers=headers
    )
    assert resgate.status_code == 201

    resposta = _cancelar(cliente_http, headers, pedido_id)

    assert (resposta.status_code, resposta.json()["pagamentoEstornado"]) == (200, False)
    assert saldo_de_pontos(headers) == 149


def test_estorno_retira_pontos_ja_usados_e_o_saldo_fica_negativo(
    cliente_http,
    entrar,
    entrar_como_cliente,
    cliente_novo,
    acumular_pontos,
    fazer_pedido,
    pagar_pedido,
    saldo_de_pontos,
):
    headers = entrar_como_cliente(cliente_novo)
    pago_id = acumular_pontos(cliente_novo, 3)
    outro_id = fazer_pedido(cliente_novo["email"], cliente_novo["senha"])["pedidoId"]
    cliente_http.post(
        "/fidelidade/resgates", json={"pedidoId": outro_id, "pontos": 100}, headers=headers
    )
    pagar_pedido(outro_id, headers)

    _cancelar(cliente_http, entrar(EMAIL_GERENTE_RECIFE), pago_id)

    assert saldo_de_pontos(headers) == 149 - 100 + 13 - 149
    assert cliente_http.get("/fidelidade/saldo", headers=headers).json()["valorEquivalente"] == 0
