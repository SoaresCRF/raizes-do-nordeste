from src.infrastructure.database.seeds.dados_iniciais import DOMINIO_EMAIL
from src.infrastructure.pagamento.gateway_mock import MOTIVO_RECUSA_SIMULADA

UNIDADE_RECIFE = 1
UNIDADE_CARUARU = 2
TAPIOCA = 1
BOLO = 3
# 8 bolos de R$ 12,50 = R$ 100,00, exatamente 100 pontos (RN18).
BOLOS_PARA_100_PONTOS = 8
# Tapioca de R$ 18,90 rende 18 pontos.
PONTOS_DE_UMA_TAPIOCA = 18
# 3 cafés completos de R$ 49,90 = R$ 149,70, que rendem 149 pontos.
PONTOS_DE_TRES_CAFES = 149
# Tapioca de R$ 18,90 com 100 pontos resgatados (R$ 5,00) sai por R$ 13,90 e rende 13 pontos.
TOTAL_COM_DESCONTO = 13.9
PONTOS_DO_TOTAL_COM_DESCONTO = 13
MOTIVO = "Cliente desistiu"
EMAIL_CLIENTE = f"cliente@{DOMINIO_EMAIL}"
EMAIL_GERENTE_RECIFE = f"gerente.recife@{DOMINIO_EMAIL}"


def _consultar(cliente_http, headers: dict, pedido_id: int) -> dict:
    resposta = cliente_http.get(f"/pedidos/{pedido_id}", headers=headers)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _pagar(cliente_http, headers: dict, pedido_id: int, resultado: str):
    return cliente_http.post(
        "/pagamentos",
        json={"pedidoId": pedido_id},
        headers=headers | {"X-Simular-Resultado": resultado},
    )


def _resgatar(cliente_http, headers: dict, pedido_id: int, pontos: int = 100):
    return cliente_http.post(
        "/fidelidade/resgates", json={"pedidoId": pedido_id, "pontos": pontos}, headers=headers
    )


def _cancelar(cliente_http, headers: dict, pedido_id: int):
    return cliente_http.post(
        f"/pedidos/{pedido_id}/cancelamento", json={"motivo": MOTIVO}, headers=headers
    )


def _fazer_pedido_do(fazer_pedido, cliente: dict, **alteracoes) -> int:
    return fazer_pedido(cliente["email"], cliente["senha"], **alteracoes)["pedidoId"]


def test_pagamento_recusado_e_depois_aprovado(
    cliente_http, entrar_como_cliente, cliente_novo, fazer_pedido, saldo_de_pontos
):
    headers = entrar_como_cliente(cliente_novo)
    pedido_id = _fazer_pedido_do(fazer_pedido, cliente_novo)

    recusado = _pagar(cliente_http, headers, pedido_id, "RECUSADO")

    assert recusado.status_code == 201
    assert (recusado.json()["status"], recusado.json()["statusPedido"]) == (
        "RECUSADO",
        "AGUARDANDO_PAGAMENTO",
    )
    assert _consultar(cliente_http, headers, pedido_id)["status"] == "AGUARDANDO_PAGAMENTO"
    assert saldo_de_pontos(headers) == 0

    aprovado = _pagar(cliente_http, headers, pedido_id, "APROVADO")

    assert aprovado.status_code == 201
    assert (aprovado.json()["status"], aprovado.json()["statusPedido"]) == (
        "APROVADO",
        "EM_PREPARO",
    )
    assert _consultar(cliente_http, headers, pedido_id)["status"] == "EM_PREPARO"
    assert saldo_de_pontos(headers) == PONTOS_DE_UMA_TAPIOCA
    primeira_tentativa = cliente_http.get(
        f"/pagamentos/{recusado.json()['pagamentoId']}", headers=headers
    ).json()
    assert (primeira_tentativa["status"], primeira_tentativa["motivoRecusa"]) == (
        "RECUSADO",
        MOTIVO_RECUSA_SIMULADA,
    )


def test_gateway_em_erro_mantem_o_pedido_e_permite_nova_tentativa(
    cliente_http,
    entrar_como_cliente,
    cliente_novo,
    fazer_pedido,
    saldo_pela_api,
    saldo_de_pontos,
):
    headers = entrar_como_cliente(cliente_novo)
    pedido_id = _fazer_pedido_do(fazer_pedido, cliente_novo)
    saldo_depois_do_pedido = saldo_pela_api(UNIDADE_RECIFE, TAPIOCA)

    falha = _pagar(cliente_http, headers, pedido_id, "ERRO")

    assert falha.status_code == 503
    assert falha.json()["error"] == "GATEWAY_PAGAMENTO_INDISPONIVEL"
    intacto = _consultar(cliente_http, headers, pedido_id)
    assert (intacto["status"], intacto["ultimoPagamento"]["status"]) == (
        "AGUARDANDO_PAGAMENTO",
        "ERRO",
    )
    assert saldo_pela_api(UNIDADE_RECIFE, TAPIOCA) == saldo_depois_do_pedido

    nova_tentativa = _pagar(cliente_http, headers, pedido_id, "APROVADO")

    assert nova_tentativa.status_code == 201
    assert nova_tentativa.json()["statusPedido"] == "EM_PREPARO"
    assert _consultar(cliente_http, headers, pedido_id)["status"] == "EM_PREPARO"
    assert saldo_de_pontos(headers) == PONTOS_DE_UMA_TAPIOCA


def test_cancelamento_antes_do_pagamento_devolve_o_estoque(
    cliente_http, entrar, fazer_pedido, saldo_pela_api
):
    headers = entrar(EMAIL_CLIENTE)
    saldo_inicial = saldo_pela_api(UNIDADE_RECIFE, TAPIOCA)
    pedido_id = fazer_pedido(itens=[{"produtoId": TAPIOCA, "quantidade": 3}])["pedidoId"]
    assert saldo_pela_api(UNIDADE_RECIFE, TAPIOCA) == saldo_inicial - 3

    cancelado = _cancelar(cliente_http, headers, pedido_id)

    assert cancelado.status_code == 200
    assert (cancelado.json()["status"], cancelado.json()["pagamentoEstornado"]) == (
        "CANCELADO",
        False,
    )
    detalhado = _consultar(cliente_http, headers, pedido_id)
    assert (detalhado["status"], detalhado["motivoCancelamento"]) == ("CANCELADO", MOTIVO)
    assert saldo_pela_api(UNIDADE_RECIFE, TAPIOCA) == saldo_inicial
    pagamento_depois = _pagar(cliente_http, headers, pedido_id, "APROVADO")
    assert pagamento_depois.status_code == 409
    assert pagamento_depois.json()["error"] == "PAGAMENTO_NAO_PERMITIDO"


def test_gerente_cancela_pedido_pago_com_resgate_e_estorna_tudo(
    cliente_http,
    entrar,
    entrar_como_cliente,
    cliente_novo,
    fazer_pedido,
    acumular_pontos,
    saldo_de_pontos,
    saldo_pela_api,
):
    headers = entrar_como_cliente(cliente_novo)
    acumular_pontos(cliente_novo, 3)
    saldo_inicial = saldo_pela_api(UNIDADE_RECIFE, TAPIOCA)
    pedido_id = _fazer_pedido_do(fazer_pedido, cliente_novo)
    resgate = _resgatar(cliente_http, headers, pedido_id)
    assert (resgate.status_code, resgate.json()["totalAtualizado"]) == (201, TOTAL_COM_DESCONTO)
    pago = _pagar(cliente_http, headers, pedido_id, "APROVADO")
    assert (pago.status_code, pago.json()["valor"]) == (201, TOTAL_COM_DESCONTO)
    assert saldo_de_pontos(headers) == PONTOS_DE_TRES_CAFES - 100 + PONTOS_DO_TOTAL_COM_DESCONTO
    gerente = entrar(EMAIL_GERENTE_RECIFE)

    cancelado = _cancelar(cliente_http, gerente, pedido_id)

    assert cancelado.status_code == 200
    assert (cancelado.json()["status"], cancelado.json()["pagamentoEstornado"]) == (
        "CANCELADO",
        True,
    )
    estornado = cliente_http.get(f"/pagamentos/{pago.json()['pagamentoId']}", headers=gerente)
    assert estornado.status_code == 200, estornado.text
    assert estornado.json()["status"] == "ESTORNADO"
    assert saldo_de_pontos(headers) == PONTOS_DE_TRES_CAFES
    assert saldo_pela_api(UNIDADE_RECIFE, TAPIOCA) == saldo_inicial
    assert _consultar(cliente_http, headers, pedido_id)["status"] == "CANCELADO"


def test_resgate_de_todo_o_saldo_antes_do_pagamento(
    cliente_http, entrar_como_cliente, cliente_novo, fazer_pedido, pagar_pedido, saldo_de_pontos
):
    headers = entrar_como_cliente(cliente_novo)
    compra_id = _fazer_pedido_do(
        fazer_pedido,
        cliente_novo,
        unidadeId=UNIDADE_CARUARU,
        itens=[{"produtoId": BOLO, "quantidade": BOLOS_PARA_100_PONTOS}],
    )
    pagar_pedido(compra_id, headers)
    assert saldo_de_pontos(headers) == 100
    pedido_id = _fazer_pedido_do(fazer_pedido, cliente_novo)

    resgate = _resgatar(cliente_http, headers, pedido_id)

    assert resgate.status_code == 201
    assert resgate.json() == {
        "pedidoId": pedido_id,
        "pontosResgatados": 100,
        "desconto": 5.0,
        "totalAtualizado": TOTAL_COM_DESCONTO,
        "saldoPontos": 0,
    }
    detalhado = _consultar(cliente_http, headers, pedido_id)
    assert (detalhado["desconto"], detalhado["total"]) == (5.0, TOTAL_COM_DESCONTO)

    pago = _pagar(cliente_http, headers, pedido_id, "APROVADO")

    assert pago.status_code == 201
    assert (pago.json()["valor"], pago.json()["statusPedido"]) == (TOTAL_COM_DESCONTO, "EM_PREPARO")
    assert saldo_de_pontos(headers) == PONTOS_DO_TOTAL_COM_DESCONTO


def test_cliente_que_revoga_consentimento_nao_acumula_pontos(
    cliente_http, entrar_como_cliente, cliente_novo, fazer_pedido, acumular_pontos, saldo_de_pontos
):
    headers = entrar_como_cliente(cliente_novo)
    acumular_pontos(cliente_novo, 3)
    revogacao = cliente_http.post(
        "/usuarios/me/consentimentos",
        json={"finalidade": "FIDELIDADE", "concedido": False, "versaoTermo": "1.0"},
        headers=headers,
    )
    assert revogacao.status_code == 201, revogacao.text

    pedido_id = _fazer_pedido_do(fazer_pedido, cliente_novo)
    pago = _pagar(cliente_http, headers, pedido_id, "APROVADO")

    assert (pago.status_code, pago.json()["statusPedido"]) == (201, "EM_PREPARO")
    assert saldo_de_pontos(headers) == PONTOS_DE_TRES_CAFES
    outro_id = _fazer_pedido_do(fazer_pedido, cliente_novo)
    resgate = _resgatar(cliente_http, headers, outro_id)
    assert resgate.status_code == 409
    assert resgate.json()["error"] == "CONSENTIMENTO_AUSENTE"
