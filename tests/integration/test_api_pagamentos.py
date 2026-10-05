import re

import pytest
from sqlalchemy import select

from src.infrastructure.database.seeds.dados_iniciais import DOMINIO_EMAIL
from src.infrastructure.database.tabelas import (
    log_auditoria,
    pagamento,
    pedido,
    transacao_fidelidade,
)

URL = "/pagamentos"
UNIDADE_RECIFE = 1
UNIDADE_CARUARU = 2
INEXISTENTE = 9999
SIMULAR = "X-Simular-Resultado"
FORMATO_DATA_HORA_UTC = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"
MOTIVO_RECUSA = "Transação não autorizada pela operadora (simulação)"
EMAIL_ADMIN = f"admin@{DOMINIO_EMAIL}"
EMAIL_GERENTE_RECIFE = f"gerente.recife@{DOMINIO_EMAIL}"
EMAIL_ATENDENTE_RECIFE = f"atendente.recife@{DOMINIO_EMAIL}"
EMAIL_COZINHA_RECIFE = f"cozinha.recife@{DOMINIO_EMAIL}"
EMAIL_CLIENTE = f"cliente@{DOMINIO_EMAIL}"
EMAIL_CLIENTE_SEM_CONSENTIMENTO = f"cliente.sem.consentimento@{DOMINIO_EMAIL}"


def _pagar(cliente_http, headers: dict, pedido_id: int, resultado: str | None = None):
    simulacao = {} if resultado is None else {SIMULAR: resultado}
    return cliente_http.post(URL, json={"pedidoId": pedido_id}, headers=headers | simulacao)


def _status_do_pedido(banco_semeado, pedido_id: int) -> str:
    with banco_semeado.connect() as conexao:
        return conexao.execute(select(pedido.c.status).where(pedido.c.id == pedido_id)).scalar_one()


def _pagamentos_do_pedido(banco_semeado, pedido_id: int) -> list:
    with banco_semeado.connect() as conexao:
        return conexao.execute(
            select(pagamento).where(pagamento.c.pedido_id == pedido_id).order_by(pagamento.c.id)
        ).all()


def _pontos_do_pedido(banco_semeado, pedido_id: int) -> list[tuple[str, int]]:
    with banco_semeado.connect() as conexao:
        transacoes = conexao.execute(
            select(transacao_fidelidade.c.tipo, transacao_fidelidade.c.pontos)
            .where(transacao_fidelidade.c.pedido_id == pedido_id)
            .order_by(transacao_fidelidade.c.id)
        ).all()
    return [tuple(transacao) for transacao in transacoes]


def test_pagamento_aprovado_coloca_o_pedido_em_preparo(
    cliente_http, entrar, fazer_pedido, banco_semeado
):
    criado = fazer_pedido()

    resposta = _pagar(cliente_http, entrar(EMAIL_CLIENTE), criado["pedidoId"], "APROVADO")
    corpo = resposta.json()

    assert resposta.status_code == 201
    assert corpo == {
        "pagamentoId": corpo["pagamentoId"],
        "pedidoId": criado["pedidoId"],
        "status": "APROVADO",
        "valor": criado["total"],
        "transacaoExternaId": corpo["transacaoExternaId"],
        "mensagem": "Pagamento aprovado; o pedido seguiu para o preparo",
        "statusPedido": "EM_PREPARO",
        "payloadGateway": {
            "transacaoId": corpo["transacaoExternaId"],
            "referencia": corpo["pagamentoId"],
            "valor": "18.90",
            "status": "APROVADO",
            "motivo": None,
        },
    }
    assert corpo["transacaoExternaId"].startswith("MOCK-")
    assert _status_do_pedido(banco_semeado, criado["pedidoId"]) == "EM_PREPARO"


def test_sem_o_header_de_simulacao_o_mock_aprova(cliente_http, entrar, fazer_pedido):
    resposta = _pagar(cliente_http, entrar(EMAIL_CLIENTE), fazer_pedido()["pedidoId"])

    assert (resposta.status_code, resposta.json()["status"]) == (201, "APROVADO")


def test_pagamento_recusado_mantem_o_pedido_aguardando(
    cliente_http, entrar, fazer_pedido, banco_semeado
):
    pedido_id = fazer_pedido()["pedidoId"]

    resposta = _pagar(cliente_http, entrar(EMAIL_CLIENTE), pedido_id, "RECUSADO")
    corpo = resposta.json()

    assert resposta.status_code == 201
    assert (corpo["status"], corpo["statusPedido"]) == ("RECUSADO", "AGUARDANDO_PAGAMENTO")
    assert corpo["mensagem"] == (
        f"Pagamento recusado ({MOTIVO_RECUSA}); o pedido continua aguardando pagamento"
    )
    assert corpo["transacaoExternaId"].startswith("MOCK-")
    assert _status_do_pedido(banco_semeado, pedido_id) == "AGUARDANDO_PAGAMENTO"
    [registrado] = _pagamentos_do_pedido(banco_semeado, pedido_id)
    assert registrado.motivo_recusa == MOTIVO_RECUSA


def test_gateway_indisponivel_devolve_503_e_registra_o_erro(
    cliente_http, entrar, fazer_pedido, banco_semeado
):
    pedido_id = fazer_pedido()["pedidoId"]

    resposta = _pagar(cliente_http, entrar(EMAIL_CLIENTE), pedido_id, "ERRO")

    assert resposta.status_code == 503
    [registrado] = _pagamentos_do_pedido(banco_semeado, pedido_id)
    assert resposta.json()["error"] == "GATEWAY_PAGAMENTO_INDISPONIVEL"
    assert resposta.json()["message"] == (
        f"Gateway de pagamento indisponível; pagamento {registrado.id} registrado com erro"
    )
    assert (registrado.status, registrado.transacao_externa_id, registrado.payload_gateway) == (
        "ERRO",
        None,
        None,
    )
    assert _status_do_pedido(banco_semeado, pedido_id) == "AGUARDANDO_PAGAMENTO"
    with banco_semeado.connect() as conexao:
        auditoria = conexao.execute(
            select(log_auditoria.c.dados_depois).where(
                log_auditoria.c.acao == "PAGAMENTO_REGISTRADO",
                log_auditoria.c.entidade_id == registrado.id,
            )
        ).scalar_one()
    assert auditoria["status"] == "ERRO"


def test_nova_tentativa_depois_do_erro_do_gateway_e_aprovada(cliente_http, entrar, fazer_pedido):
    headers = entrar(EMAIL_CLIENTE)
    pedido_id = fazer_pedido()["pedidoId"]
    _pagar(cliente_http, headers, pedido_id, "ERRO")

    resposta = _pagar(cliente_http, headers, pedido_id, "APROVADO")

    assert (resposta.status_code, resposta.json()["statusPedido"]) == (201, "EM_PREPARO")


def test_recusa_nao_pontua_e_permite_nova_tentativa(
    cliente_http, entrar, fazer_pedido, cliente_novo, banco_semeado
):
    headers = entrar(cliente_novo["email"], cliente_novo["senha"])
    pedido_id = fazer_pedido(cliente_novo["email"], cliente_novo["senha"])["pedidoId"]

    _pagar(cliente_http, headers, pedido_id, "RECUSADO")
    pontos_depois_da_recusa = _pontos_do_pedido(banco_semeado, pedido_id)
    segunda = _pagar(cliente_http, headers, pedido_id, "APROVADO")

    assert pontos_depois_da_recusa == []
    assert (segunda.status_code, segunda.json()["statusPedido"]) == (201, "EM_PREPARO")
    assert _pontos_do_pedido(banco_semeado, pedido_id) == [("ACUMULO", 18)]


def test_cliente_sem_consentimento_nao_acumula_pontos(
    cliente_http, entrar, fazer_pedido, banco_semeado
):
    pedido_id = fazer_pedido(EMAIL_CLIENTE_SEM_CONSENTIMENTO)["pedidoId"]

    _pagar(cliente_http, entrar(EMAIL_CLIENTE_SEM_CONSENTIMENTO), pedido_id)

    assert _pontos_do_pedido(banco_semeado, pedido_id) == []


def test_consentimento_revogado_nao_acumula_pontos(
    cliente_http, entrar, fazer_pedido, cliente_novo, banco_semeado
):
    headers = entrar(cliente_novo["email"], cliente_novo["senha"])
    revogacao = cliente_http.post(
        "/usuarios/me/consentimentos",
        json={"finalidade": "FIDELIDADE", "concedido": False, "versaoTermo": "1.0"},
        headers=headers,
    )
    assert revogacao.status_code == 201
    pedido_id = fazer_pedido(cliente_novo["email"], cliente_novo["senha"])["pedidoId"]

    _pagar(cliente_http, headers, pedido_id)

    assert _pontos_do_pedido(banco_semeado, pedido_id) == []


def test_atendente_paga_pedido_do_balcao_sem_gerar_pontos(
    cliente_http, entrar, fazer_pedido, banco_semeado
):
    pedido_id = fazer_pedido(EMAIL_ATENDENTE_RECIFE, canalPedido="BALCAO")["pedidoId"]

    resposta = _pagar(cliente_http, entrar(EMAIL_ATENDENTE_RECIFE), pedido_id)

    assert (resposta.status_code, resposta.json()["statusPedido"]) == (201, "EM_PREPARO")
    assert _pontos_do_pedido(banco_semeado, pedido_id) == []


def test_pagamento_aprovado_fica_auditado(
    cliente_http, entrar, fazer_pedido, banco_semeado, id_do_usuario
):
    criado = fazer_pedido()

    corpo = _pagar(cliente_http, entrar(EMAIL_CLIENTE), criado["pedidoId"]).json()

    with banco_semeado.connect() as conexao:
        do_pagamento = conexao.execute(
            select(log_auditoria).where(
                log_auditoria.c.acao == "PAGAMENTO_REGISTRADO",
                log_auditoria.c.entidade == "Pagamento",
                log_auditoria.c.entidade_id == corpo["pagamentoId"],
            )
        ).one()
        do_status = conexao.execute(
            select(log_auditoria).where(
                log_auditoria.c.acao == "STATUS_ALTERADO",
                log_auditoria.c.entidade == "Pedido",
                log_auditoria.c.entidade_id == criado["pedidoId"],
            )
        ).one()
    cliente_id = id_do_usuario(EMAIL_CLIENTE)
    assert (do_pagamento.usuario_id, do_pagamento.unidade_id) == (cliente_id, UNIDADE_RECIFE)
    assert do_pagamento.dados_antes is None
    assert do_pagamento.dados_depois == {
        "pedidoId": criado["pedidoId"],
        "status": "APROVADO",
        "valor": "18.90",
    }
    assert do_status.usuario_id == cliente_id
    assert (do_status.dados_antes, do_status.dados_depois) == (
        {"status": "AGUARDANDO_PAGAMENTO"},
        {"status": "EM_PREPARO"},
    )


def test_pedido_ja_pago_nao_aceita_novo_pagamento(
    cliente_http, entrar, fazer_pedido, banco_semeado
):
    headers = entrar(EMAIL_CLIENTE)
    pedido_id = fazer_pedido()["pedidoId"]
    _pagar(cliente_http, headers, pedido_id)

    resposta = _pagar(cliente_http, headers, pedido_id)

    assert resposta.status_code == 409
    assert resposta.json()["error"] == "PAGAMENTO_NAO_PERMITIDO"
    assert resposta.json()["message"] == (
        f"Pedido {pedido_id} está EM_PREPARO e não aceita pagamento nem resgate"
    )
    assert len(_pagamentos_do_pedido(banco_semeado, pedido_id)) == 1


def test_pedido_cancelado_nao_aceita_pagamento(cliente_http, entrar, fazer_pedido):
    headers = entrar(EMAIL_CLIENTE)
    pedido_id = fazer_pedido()["pedidoId"]
    cliente_http.post(
        f"/pedidos/{pedido_id}/cancelamento", json={"motivo": "Desistiu"}, headers=headers
    )

    resposta = _pagar(cliente_http, headers, pedido_id)

    assert (resposta.status_code, resposta.json()["error"]) == (409, "PAGAMENTO_NAO_PERMITIDO")


def test_pedido_inexistente_devolve_404(cliente_http, entrar):
    resposta = _pagar(cliente_http, entrar(EMAIL_CLIENTE), INEXISTENTE)

    assert resposta.status_code == 404
    assert resposta.json()["message"] == f"Pedido {INEXISTENTE} não encontrado"


def test_cliente_nao_paga_pedido_de_outro_cliente(
    cliente_http, entrar, fazer_pedido, banco_semeado
):
    pedido_id = fazer_pedido()["pedidoId"]

    resposta = _pagar(cliente_http, entrar(EMAIL_CLIENTE_SEM_CONSENTIMENTO), pedido_id)

    assert resposta.status_code == 404
    assert resposta.json()["message"] == f"Pedido {pedido_id} não encontrado"
    assert _pagamentos_do_pedido(banco_semeado, pedido_id) == []


def test_atendente_nao_paga_pedido_de_outra_unidade(cliente_http, entrar, fazer_pedido):
    pedido_id = fazer_pedido(unidadeId=UNIDADE_CARUARU)["pedidoId"]

    resposta = _pagar(cliente_http, entrar(EMAIL_ATENDENTE_RECIFE), pedido_id)

    assert resposta.status_code == 403


@pytest.mark.parametrize("email", [EMAIL_COZINHA_RECIFE, EMAIL_GERENTE_RECIFE, EMAIL_ADMIN])
def test_perfil_sem_permissao_recebe_403(cliente_http, entrar, fazer_pedido, email):
    pedido_id = fazer_pedido()["pedidoId"]

    resposta = _pagar(cliente_http, entrar(email), pedido_id)

    assert (resposta.status_code, resposta.json()["error"]) == (403, "ACESSO_NEGADO")


def test_perfil_sem_permissao_recebe_403_mesmo_com_entrada_invalida(cliente_http, entrar):
    resposta = cliente_http.post(
        URL, json={}, headers=entrar(EMAIL_COZINHA_RECIFE) | {SIMULAR: "TALVEZ"}
    )

    assert resposta.status_code == 403


@pytest.mark.parametrize(
    ("corpo", "campo", "problema"),
    [
        ({}, "pedidoId", "Campo obrigatório"),
        ({"pedidoId": "abc"}, "pedidoId", "Deve ser um número inteiro"),
        ({"pedidoId": 1, "valor": 1}, "valor", "Campo não permitido"),
    ],
)
def test_corpo_invalido_devolve_422(cliente_http, entrar, corpo, campo, problema):
    resposta = cliente_http.post(URL, json=corpo, headers=entrar(EMAIL_CLIENTE))

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [{"field": campo, "issue": problema}]


def test_header_de_simulacao_invalido_devolve_422(cliente_http, entrar, fazer_pedido):
    resposta = _pagar(cliente_http, entrar(EMAIL_CLIENTE), fazer_pedido()["pedidoId"], "TALVEZ")

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [
        {
            "field": SIMULAR,
            "issue": "Deve ser um destes valores: 'APROVADO', 'RECUSADO' ou 'ERRO'",
        }
    ]


def test_pagamento_sem_token_devolve_401(cliente_http):
    assert cliente_http.post(URL, json={"pedidoId": 1}).status_code == 401


def _consultar(cliente_http, headers: dict, pagamento_id: int):
    return cliente_http.get(f"{URL}/{pagamento_id}", headers=headers)


def test_cliente_consulta_o_proprio_pagamento(cliente_http, entrar, fazer_pedido, pagar_pedido):
    headers = entrar(EMAIL_CLIENTE)
    criado = fazer_pedido()
    pago = pagar_pedido(criado["pedidoId"], headers, "RECUSADO")

    resposta = _consultar(cliente_http, headers, pago["pagamentoId"])
    corpo = resposta.json()

    assert resposta.status_code == 200
    assert corpo == {
        "pagamentoId": pago["pagamentoId"],
        "pedidoId": criado["pedidoId"],
        "status": "RECUSADO",
        "valor": criado["total"],
        "formaPagamento": "MOCK",
        "transacaoExternaId": pago["transacaoExternaId"],
        "motivoRecusa": MOTIVO_RECUSA,
        "payloadGateway": pago["payloadGateway"],
        "createdAt": corpo["createdAt"],
        "updatedAt": corpo["updatedAt"],
    }
    assert re.fullmatch(FORMATO_DATA_HORA_UTC, corpo["createdAt"])


@pytest.mark.parametrize("email", [EMAIL_ATENDENTE_RECIFE, EMAIL_GERENTE_RECIFE, EMAIL_ADMIN])
def test_funcionario_da_unidade_consulta_pagamento(
    cliente_http, entrar, fazer_pedido, pagar_pedido, email
):
    pago = pagar_pedido(fazer_pedido()["pedidoId"], entrar(EMAIL_CLIENTE))

    resposta = _consultar(cliente_http, entrar(email), pago["pagamentoId"])

    assert (resposta.status_code, resposta.json()["status"]) == (200, "APROVADO")


def test_pagamento_inexistente_devolve_404(cliente_http, entrar):
    resposta = _consultar(cliente_http, entrar(EMAIL_CLIENTE), INEXISTENTE)

    assert resposta.status_code == 404
    assert resposta.json()["message"] == f"Pagamento {INEXISTENTE} não encontrado"


def test_cliente_nao_ve_pagamento_de_outro_cliente(
    cliente_http, entrar, fazer_pedido, pagar_pedido
):
    pago = pagar_pedido(fazer_pedido()["pedidoId"], entrar(EMAIL_CLIENTE))

    resposta = _consultar(
        cliente_http, entrar(EMAIL_CLIENTE_SEM_CONSENTIMENTO), pago["pagamentoId"]
    )

    assert resposta.status_code == 404
    assert resposta.json()["message"] == f"Pagamento {pago['pagamentoId']} não encontrado"


def test_gerente_de_outra_unidade_recebe_403(cliente_http, entrar, fazer_pedido, pagar_pedido):
    pedido_id = fazer_pedido(unidadeId=UNIDADE_CARUARU)["pedidoId"]
    pago = pagar_pedido(pedido_id, entrar(EMAIL_CLIENTE))

    resposta = _consultar(cliente_http, entrar(EMAIL_GERENTE_RECIFE), pago["pagamentoId"])

    assert resposta.status_code == 403


def test_cozinha_nao_consulta_pagamento(cliente_http, entrar, fazer_pedido, pagar_pedido):
    pago = pagar_pedido(fazer_pedido()["pedidoId"], entrar(EMAIL_CLIENTE))

    resposta = _consultar(cliente_http, entrar(EMAIL_COZINHA_RECIFE), pago["pagamentoId"])

    assert resposta.status_code == 403


def test_id_de_pagamento_invalido_devolve_422(cliente_http, entrar):
    resposta = _consultar(cliente_http, entrar(EMAIL_CLIENTE), 0)

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [{"field": "id", "issue": "Deve ser maior que 0"}]


def test_consulta_de_pagamento_sem_token_devolve_401(cliente_http):
    assert cliente_http.get(f"{URL}/1").status_code == 401
