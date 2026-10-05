import re

import pytest
from sqlalchemy import select

from src.infrastructure.database.seeds.dados_iniciais import DOMINIO_EMAIL
from src.infrastructure.database.tabelas import log_auditoria, pedido

URL = "/pedidos"
UNIDADE_RECIFE = 1
INEXISTENTE = 9999
EMAIL_ADMIN = f"admin@{DOMINIO_EMAIL}"
EMAIL_GERENTE_RECIFE = f"gerente.recife@{DOMINIO_EMAIL}"
EMAIL_GERENTE_CARUARU = f"gerente.caruaru@{DOMINIO_EMAIL}"
EMAIL_ATENDENTE_RECIFE = f"atendente.recife@{DOMINIO_EMAIL}"
EMAIL_COZINHA_RECIFE = f"cozinha.recife@{DOMINIO_EMAIL}"
EMAIL_CLIENTE = f"cliente@{DOMINIO_EMAIL}"
FORMATO_DATA_HORA_UTC = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"


def _alterar(cliente_http, headers: dict, pedido_id: int, status: str):
    return cliente_http.patch(f"{URL}/{pedido_id}/status", json={"status": status}, headers=headers)


def _status(banco_semeado, pedido_id: int) -> str:
    with banco_semeado.connect() as conexao:
        return conexao.execute(select(pedido.c.status).where(pedido.c.id == pedido_id)).scalar_one()


def _pedido_em(fazer_pedido, definir_status_do_pedido, status: str) -> int:
    pedido_id = fazer_pedido()["pedidoId"]
    definir_status_do_pedido(pedido_id, status)
    return pedido_id


def test_cozinha_marca_pedido_em_preparo_como_pronto(
    cliente_http, entrar, fazer_pedido, definir_status_do_pedido
):
    pedido_id = _pedido_em(fazer_pedido, definir_status_do_pedido, "EM_PREPARO")

    resposta = _alterar(cliente_http, entrar(EMAIL_COZINHA_RECIFE), pedido_id, "PRONTO")
    corpo = resposta.json()

    assert resposta.status_code == 200
    assert corpo == {
        "pedidoId": pedido_id,
        "statusAnterior": "EM_PREPARO",
        "status": "PRONTO",
        "updatedAt": corpo["updatedAt"],
    }
    assert re.fullmatch(FORMATO_DATA_HORA_UTC, corpo["updatedAt"])


def test_atendente_entrega_pedido_pronto(
    cliente_http, entrar, fazer_pedido, definir_status_do_pedido
):
    pedido_id = _pedido_em(fazer_pedido, definir_status_do_pedido, "PRONTO")

    resposta = _alterar(cliente_http, entrar(EMAIL_ATENDENTE_RECIFE), pedido_id, "ENTREGUE")

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "ENTREGUE"


@pytest.mark.parametrize("email", [EMAIL_GERENTE_RECIFE, EMAIL_ADMIN])
def test_gerencia_marca_pronto_e_entregue(
    cliente_http, entrar, fazer_pedido, definir_status_do_pedido, email
):
    pedido_id = _pedido_em(fazer_pedido, definir_status_do_pedido, "EM_PREPARO")
    gestor = entrar(email)

    pronto = _alterar(cliente_http, gestor, pedido_id, "PRONTO")
    entregue = _alterar(cliente_http, gestor, pedido_id, "ENTREGUE")

    assert (pronto.status_code, entregue.status_code) == (200, 200)


def test_mudanca_de_status_fica_auditada(
    cliente_http, entrar, fazer_pedido, definir_status_do_pedido, banco_semeado, id_do_usuario
):
    pedido_id = _pedido_em(fazer_pedido, definir_status_do_pedido, "EM_PREPARO")

    _alterar(cliente_http, entrar(EMAIL_COZINHA_RECIFE), pedido_id, "PRONTO")

    with banco_semeado.connect() as conexao:
        auditoria = conexao.execute(
            select(log_auditoria).where(
                log_auditoria.c.acao == "STATUS_ALTERADO",
                log_auditoria.c.entidade_id == pedido_id,
            )
        ).one()
    assert (auditoria.entidade, auditoria.usuario_id, auditoria.unidade_id) == (
        "Pedido",
        id_do_usuario(EMAIL_COZINHA_RECIFE),
        UNIDADE_RECIFE,
    )
    assert auditoria.dados_antes == {"status": "EM_PREPARO"}
    assert auditoria.dados_depois == {"status": "PRONTO"}


@pytest.mark.parametrize(
    ("atual", "novo"),
    [
        ("AGUARDANDO_PAGAMENTO", "ENTREGUE"),
        ("AGUARDANDO_PAGAMENTO", "PRONTO"),
        ("EM_PREPARO", "ENTREGUE"),
        ("ENTREGUE", "PRONTO"),
        ("CANCELADO", "PRONTO"),
    ],
)
def test_transicao_invalida_devolve_409(
    cliente_http, entrar, fazer_pedido, definir_status_do_pedido, banco_semeado, atual, novo
):
    pedido_id = _pedido_em(fazer_pedido, definir_status_do_pedido, atual)

    resposta = _alterar(cliente_http, entrar(EMAIL_GERENTE_RECIFE), pedido_id, novo)

    assert resposta.status_code == 409
    assert resposta.json()["error"] == "TRANSICAO_STATUS_INVALIDA"
    assert _status(banco_semeado, pedido_id) == atual


@pytest.mark.parametrize(
    ("email", "atual", "novo"),
    [
        (EMAIL_COZINHA_RECIFE, "PRONTO", "ENTREGUE"),
        (EMAIL_ATENDENTE_RECIFE, "EM_PREPARO", "PRONTO"),
    ],
)
def test_perfil_sem_permissao_para_o_status_recebe_403(
    cliente_http, entrar, fazer_pedido, definir_status_do_pedido, email, atual, novo
):
    pedido_id = _pedido_em(fazer_pedido, definir_status_do_pedido, atual)

    resposta = _alterar(cliente_http, entrar(email), pedido_id, novo)

    assert resposta.status_code == 403
    assert resposta.json()["error"] == "ACESSO_NEGADO"


@pytest.mark.parametrize("status", ["PRONTO", "PAGO"])
def test_cliente_nao_muda_status(cliente_http, entrar, fazer_pedido, status):
    pedido_id = fazer_pedido()["pedidoId"]

    resposta = _alterar(cliente_http, entrar(EMAIL_CLIENTE), pedido_id, status)

    assert resposta.status_code == 403


@pytest.mark.parametrize("novo", ["AGUARDANDO_PAGAMENTO", "EM_PREPARO", "CANCELADO"])
def test_status_de_outro_fluxo_devolve_422(cliente_http, entrar, fazer_pedido, novo):
    pedido_id = fazer_pedido()["pedidoId"]

    resposta = _alterar(cliente_http, entrar(EMAIL_GERENTE_RECIFE), pedido_id, novo)

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [
        {"field": "status", "issue": "Deve ser um destes valores: 'PRONTO' ou 'ENTREGUE'"}
    ]


def test_status_fora_do_enum_devolve_422(cliente_http, entrar, fazer_pedido):
    pedido_id = fazer_pedido()["pedidoId"]

    resposta = _alterar(cliente_http, entrar(EMAIL_GERENTE_RECIFE), pedido_id, "PAGO")

    assert resposta.status_code == 422
    assert resposta.json()["details"][0]["field"] == "status"


def test_funcionario_de_outra_unidade_recebe_403(
    cliente_http, entrar, fazer_pedido, definir_status_do_pedido
):
    pedido_id = _pedido_em(fazer_pedido, definir_status_do_pedido, "EM_PREPARO")

    resposta = _alterar(cliente_http, entrar(EMAIL_GERENTE_CARUARU), pedido_id, "PRONTO")

    assert resposta.status_code == 403


def test_pedido_inexistente_devolve_404(cliente_http, entrar):
    resposta = _alterar(cliente_http, entrar(EMAIL_GERENTE_RECIFE), INEXISTENTE, "PRONTO")

    assert resposta.status_code == 404


def test_mudanca_sem_token_devolve_401(cliente_http):
    assert cliente_http.patch(f"{URL}/1/status", json={"status": "PRONTO"}).status_code == 401
