from decimal import Decimal

import pytest
from sqlalchemy import select

from src.infrastructure.database.seeds.dados_iniciais import DOMINIO_EMAIL
from src.infrastructure.database.tabelas import log_auditoria, pedido, transacao_fidelidade

URL = "/fidelidade/resgates"
INEXISTENTE = 9999
CAFE_PASSADO = 6
EMAIL_ADMIN = f"admin@{DOMINIO_EMAIL}"
EMAIL_GERENTE_RECIFE = f"gerente.recife@{DOMINIO_EMAIL}"
EMAIL_ATENDENTE_RECIFE = f"atendente.recife@{DOMINIO_EMAIL}"
EMAIL_CLIENTE_SEM_CONSENTIMENTO = f"cliente.sem.consentimento@{DOMINIO_EMAIL}"


def _pedido_de(fazer_pedido, cliente: dict, **alteracoes) -> int:
    return fazer_pedido(cliente["email"], cliente["senha"], **alteracoes)["pedidoId"]


def _resgatar(cliente_http, headers: dict, pedido_id: int, pontos: int = 100):
    return cliente_http.post(URL, json={"pedidoId": pedido_id, "pontos": pontos}, headers=headers)


@pytest.fixture
def cliente_com_149_pontos(cliente_novo, acumular_pontos) -> dict:
    acumular_pontos(cliente_novo, 3)
    return cliente_novo


def test_resgate_aplica_o_desconto_no_pedido(
    cliente_http, entrar_como_cliente, fazer_pedido, cliente_com_149_pontos, banco_semeado
):
    cliente = cliente_com_149_pontos
    pedido_id = _pedido_de(fazer_pedido, cliente)

    resposta = _resgatar(cliente_http, entrar_como_cliente(cliente), pedido_id)

    assert resposta.status_code == 201
    assert resposta.json() == {
        "pedidoId": pedido_id,
        "pontosResgatados": 100,
        "desconto": 5.0,
        "totalAtualizado": 13.9,
        "saldoPontos": 49,
    }
    with banco_semeado.connect() as conexao:
        valores = conexao.execute(
            select(pedido.c.subtotal, pedido.c.desconto, pedido.c.total).where(
                pedido.c.id == pedido_id
            )
        ).one()
        transacoes = conexao.execute(
            select(transacao_fidelidade.c.tipo, transacao_fidelidade.c.pontos).where(
                transacao_fidelidade.c.pedido_id == pedido_id
            )
        ).all()
    assert tuple(valores) == (Decimal("18.90"), Decimal("5.00"), Decimal("13.90"))
    assert [tuple(transacao) for transacao in transacoes] == [("RESGATE", -100)]


def test_pedido_com_desconto_e_pago_pelo_total_atualizado(
    cliente_http,
    entrar_como_cliente,
    fazer_pedido,
    pagar_pedido,
    cliente_com_149_pontos,
    saldo_de_pontos,
):
    cliente = cliente_com_149_pontos
    headers = entrar_como_cliente(cliente)
    pedido_id = _pedido_de(fazer_pedido, cliente)
    _resgatar(cliente_http, headers, pedido_id)

    pago = pagar_pedido(pedido_id, headers)

    assert pago["valor"] == 13.9
    assert saldo_de_pontos(headers) == 49 + 13


def test_resgate_fica_auditado(
    cliente_http, entrar_como_cliente, fazer_pedido, cliente_com_149_pontos, banco_semeado
):
    cliente = cliente_com_149_pontos
    pedido_id = _pedido_de(fazer_pedido, cliente)

    _resgatar(cliente_http, entrar_como_cliente(cliente), pedido_id)

    with banco_semeado.connect() as conexao:
        auditoria = conexao.execute(
            select(log_auditoria).where(
                log_auditoria.c.acao == "PONTOS_RESGATADOS",
                log_auditoria.c.entidade_id == pedido_id,
            )
        ).one()
    assert (auditoria.entidade, auditoria.usuario_id, auditoria.unidade_id) == (
        "Pedido",
        cliente["id"],
        1,
    )
    assert auditoria.dados_antes == {"desconto": "0.00", "total": "18.90"}
    assert auditoria.dados_depois == {"pontos": 100, "desconto": "5.00", "total": "13.90"}


def test_cliente_sem_consentimento_nao_resgata(cliente_http, entrar, fazer_pedido):
    pedido_id = fazer_pedido(EMAIL_CLIENTE_SEM_CONSENTIMENTO)["pedidoId"]

    resposta = _resgatar(cliente_http, entrar(EMAIL_CLIENTE_SEM_CONSENTIMENTO), pedido_id)

    assert resposta.status_code == 409
    assert resposta.json()["error"] == "CONSENTIMENTO_AUSENTE"


def test_consentimento_revogado_bloqueia_o_resgate_e_mantem_o_saldo(
    cliente_http, entrar_como_cliente, fazer_pedido, cliente_com_149_pontos, saldo_de_pontos
):
    cliente = cliente_com_149_pontos
    headers = entrar_como_cliente(cliente)
    cliente_http.post(
        "/usuarios/me/consentimentos",
        json={"finalidade": "FIDELIDADE", "concedido": False, "versaoTermo": "1.0"},
        headers=headers,
    )
    pedido_id = _pedido_de(fazer_pedido, cliente)

    resposta = _resgatar(cliente_http, headers, pedido_id)

    assert resposta.json()["error"] == "CONSENTIMENTO_AUSENTE"
    assert saldo_de_pontos(headers) == 149


def test_saldo_insuficiente_devolve_409(
    cliente_http, entrar_como_cliente, fazer_pedido, cliente_novo
):
    pedido_id = _pedido_de(fazer_pedido, cliente_novo)

    resposta = _resgatar(cliente_http, entrar_como_cliente(cliente_novo), pedido_id)

    assert resposta.status_code == 409
    assert resposta.json()["error"] == "SALDO_PONTOS_INSUFICIENTE"
    assert resposta.json()["details"] == [{"field": "pontos", "issue": "Saldo disponível: 0"}]


def test_desconto_que_zera_o_pedido_devolve_422(
    cliente_http, entrar_como_cliente, fazer_pedido, cliente_novo, acumular_pontos
):
    acumular_pontos(cliente_novo, 5)
    pedido_id = _pedido_de(
        fazer_pedido, cliente_novo, itens=[{"produtoId": CAFE_PASSADO, "quantidade": 1}]
    )

    resposta = _resgatar(cliente_http, entrar_como_cliente(cliente_novo), pedido_id, 200)

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [
        {
            "field": "pontos",
            "issue": "Desconto de 10.00 precisa ser menor que o total do pedido (6.50)",
        }
    ]


def test_pedido_pago_nao_aceita_resgate(
    cliente_http, entrar_como_cliente, fazer_pedido, pagar_pedido, cliente_com_149_pontos
):
    cliente = cliente_com_149_pontos
    headers = entrar_como_cliente(cliente)
    pedido_id = _pedido_de(fazer_pedido, cliente)
    pagar_pedido(pedido_id, headers)

    resposta = _resgatar(cliente_http, headers, pedido_id)

    assert (resposta.status_code, resposta.json()["error"]) == (409, "PAGAMENTO_NAO_PERMITIDO")


def test_cliente_nao_resgata_em_pedido_de_outro_cliente(
    cliente_http, entrar_como_cliente, fazer_pedido, cliente_com_149_pontos
):
    pedido_id = fazer_pedido()["pedidoId"]

    resposta = _resgatar(cliente_http, entrar_como_cliente(cliente_com_149_pontos), pedido_id)

    assert resposta.status_code == 404
    assert resposta.json()["message"] == f"Pedido {pedido_id} não encontrado"


def test_resgate_em_pedido_inexistente_devolve_404(cliente_http, entrar_como_cliente, cliente_novo):
    resposta = _resgatar(cliente_http, entrar_como_cliente(cliente_novo), INEXISTENTE)

    assert resposta.status_code == 404


@pytest.mark.parametrize(
    ("corpo", "campo", "problema"),
    [
        ({"pedidoId": 1, "pontos": 150}, "pontos", "Deve ser múltiplo de 100"),
        ({"pedidoId": 1, "pontos": 0}, "pontos", "Deve ser maior que 0"),
        ({"pedidoId": 1, "pontos": "100"}, "pontos", "Deve ser um número inteiro"),
        ({"pontos": 100}, "pedidoId", "Campo obrigatório"),
        ({"pedidoId": 1, "pontos": 100, "desconto": 5}, "desconto", "Campo não permitido"),
    ],
)
def test_corpo_invalido_devolve_422(
    cliente_http, entrar_como_cliente, cliente_novo, corpo, campo, problema
):
    resposta = cliente_http.post(URL, json=corpo, headers=entrar_como_cliente(cliente_novo))

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [{"field": campo, "issue": problema}]


@pytest.mark.parametrize("email", [EMAIL_ATENDENTE_RECIFE, EMAIL_GERENTE_RECIFE, EMAIL_ADMIN])
def test_funcionario_nao_resgata_pontos(cliente_http, entrar, email):
    resposta = cliente_http.post(URL, json={"pontos": 150}, headers=entrar(email))

    assert (resposta.status_code, resposta.json()["error"]) == (403, "ACESSO_NEGADO")


def test_resgate_sem_token_devolve_401(cliente_http):
    assert cliente_http.post(URL, json={"pedidoId": 1, "pontos": 100}).status_code == 401
