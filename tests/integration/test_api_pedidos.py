import re
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, insert, select

from src.infrastructure.database.seeds.dados_iniciais import DOMINIO_EMAIL
from src.infrastructure.database.tabelas import (
    estoque,
    log_auditoria,
    movimentacao_estoque,
    pedido,
)

URL = "/pedidos"
UNIDADE_RECIFE = 1
UNIDADE_CARUARU = 2
INEXISTENTE = 9999
TAPIOCA = 1
CUSCUZ = 2
BOLO = 3
CAFE_DA_MANHA_COMPLETO = 5
ID_MAXIMO = 2_147_483_647
PRECO_MAXIMO = 99999999.99
EMAIL_ADMIN = f"admin@{DOMINIO_EMAIL}"
EMAIL_GERENTE_RECIFE = f"gerente.recife@{DOMINIO_EMAIL}"
EMAIL_ATENDENTE_RECIFE = f"atendente.recife@{DOMINIO_EMAIL}"
EMAIL_COZINHA_RECIFE = f"cozinha.recife@{DOMINIO_EMAIL}"
EMAIL_CLIENTE = f"cliente@{DOMINIO_EMAIL}"
EMAIL_CLIENTE_SEM_CONSENTIMENTO = f"cliente.sem.consentimento@{DOMINIO_EMAIL}"
FORMATO_DATA_HORA_UTC = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"
QUANTIDADE_INTEIRA = "Deve ser um número inteiro"


def _pedido(**alteracoes) -> dict:
    return {
        "canalPedido": "TOTEM",
        "unidadeId": UNIDADE_RECIFE,
        "itens": [
            {"produtoId": TAPIOCA, "quantidade": 2},
            {"produtoId": CUSCUZ, "quantidade": 1},
        ],
        "formaPagamento": "MOCK",
    } | alteracoes


def _balcao(**alteracoes) -> dict:
    return _pedido(canalPedido="BALCAO", **alteracoes)


def _total_de_pedidos(banco_semeado) -> int:
    with banco_semeado.connect() as conexao:
        return conexao.execute(select(func.count()).select_from(pedido)).scalar_one()


def _cadastrar_ofertado(cliente_http, entrar, banco_semeado, **alteracoes) -> int:
    dados = {"nome": "Arrumadinho", "preco": 27.0} | alteracoes
    resposta = cliente_http.post("/produtos", json=dados, headers=entrar(EMAIL_ADMIN))
    assert resposta.status_code == 201, resposta.text
    produto_id = resposta.json()["id"]
    with banco_semeado.begin() as conexao:
        conexao.execute(
            insert(estoque).values(unidade_id=UNIDADE_RECIFE, produto_id=produto_id, quantidade=10)
        )
    return produto_id


def test_cliente_cria_pedido_com_total_calculado_no_servidor(cliente_http, entrar, id_do_usuario):
    resposta = cliente_http.post(URL, json=_pedido(), headers=entrar(EMAIL_CLIENTE))
    corpo = resposta.json()

    assert resposta.status_code == 201
    assert corpo == {
        "pedidoId": corpo["pedidoId"],
        "clienteId": id_do_usuario(EMAIL_CLIENTE),
        "canalPedido": "TOTEM",
        "unidadeId": UNIDADE_RECIFE,
        "status": "AGUARDANDO_PAGAMENTO",
        "subtotal": 62.7,
        "desconto": 0,
        "total": 62.7,
        "itens": [
            {"produtoId": TAPIOCA, "quantidade": 2, "precoUnitario": 18.9},
            {"produtoId": CUSCUZ, "quantidade": 1, "precoUnitario": 24.9},
        ],
        "createdAt": corpo["createdAt"],
    }
    assert re.fullmatch(FORMATO_DATA_HORA_UTC, corpo["createdAt"])


def test_pedido_baixa_o_estoque_com_saidas_vinculadas(
    cliente_http, entrar, banco_semeado, saldo_de_estoque
):
    anterior = saldo_de_estoque(UNIDADE_RECIFE, TAPIOCA)

    corpo = cliente_http.post(URL, json=_pedido(), headers=entrar(EMAIL_CLIENTE)).json()

    assert saldo_de_estoque(UNIDADE_RECIFE, TAPIOCA) == anterior - 2
    with banco_semeado.connect() as conexao:
        saidas = conexao.execute(
            select(
                movimentacao_estoque.c.tipo,
                movimentacao_estoque.c.quantidade,
                movimentacao_estoque.c.motivo,
            )
            .where(movimentacao_estoque.c.pedido_id == corpo["pedidoId"])
            .order_by(movimentacao_estoque.c.id)
        ).all()
    assert [tuple(saida) for saida in saidas] == [
        ("SAIDA", 2, f"Pedido {corpo['pedidoId']}"),
        ("SAIDA", 1, f"Pedido {corpo['pedidoId']}"),
    ]


def test_pedido_criado_fica_auditado(cliente_http, entrar, banco_semeado, id_do_usuario):
    cliente_id = id_do_usuario(EMAIL_CLIENTE)

    corpo = cliente_http.post(URL, json=_pedido(), headers=entrar(EMAIL_CLIENTE)).json()

    with banco_semeado.connect() as conexao:
        auditoria = conexao.execute(
            select(log_auditoria).where(
                log_auditoria.c.acao == "PEDIDO_CRIADO",
                log_auditoria.c.entidade_id == corpo["pedidoId"],
            )
        ).one()
    assert (auditoria.entidade, auditoria.usuario_id, auditoria.unidade_id) == (
        "Pedido",
        cliente_id,
        UNIDADE_RECIFE,
    )
    assert auditoria.dados_antes is None
    assert auditoria.dados_depois == {
        "status": "AGUARDANDO_PAGAMENTO",
        "canalPedido": "TOTEM",
        "clienteId": cliente_id,
        "total": "62.70",
        "itens": [
            {"produtoId": TAPIOCA, "quantidade": 2, "precoUnitario": "18.90"},
            {"produtoId": CUSCUZ, "quantidade": 1, "precoUnitario": "24.90"},
        ],
    }
    assert auditoria.request_id is not None


def test_atendente_cria_pedido_no_balcao_sem_cliente(cliente_http, entrar):
    resposta = cliente_http.post(URL, json=_balcao(), headers=entrar(EMAIL_ATENDENTE_RECIFE))

    assert resposta.status_code == 201
    assert (resposta.json()["canalPedido"], resposta.json()["clienteId"]) == ("BALCAO", None)


def test_atendente_informa_o_cliente_do_pedido(cliente_http, entrar, id_do_usuario):
    cliente_id = id_do_usuario(EMAIL_CLIENTE)

    resposta = cliente_http.post(
        URL, json=_balcao(clienteId=cliente_id), headers=entrar(EMAIL_ATENDENTE_RECIFE)
    )

    assert resposta.status_code == 201
    assert resposta.json()["clienteId"] == cliente_id


@pytest.mark.parametrize("canal", ["APP", "TOTEM", "PICKUP", "WEB"])
def test_cliente_pede_por_qualquer_canal_de_autoatendimento(cliente_http, entrar, canal):
    resposta = cliente_http.post(
        URL, json=_pedido(canalPedido=canal), headers=entrar(EMAIL_CLIENTE)
    )

    assert resposta.status_code == 201
    assert resposta.json()["canalPedido"] == canal


@pytest.mark.parametrize(
    ("email", "canal", "problema"),
    [
        (EMAIL_CLIENTE, "BALCAO", "Canal BALCAO não permitido para o perfil CLIENTE"),
        (EMAIL_ATENDENTE_RECIFE, "APP", "Canal APP não permitido para o perfil ATENDENTE"),
    ],
)
def test_canal_incoerente_com_o_perfil_devolve_422(cliente_http, entrar, email, canal, problema):
    resposta = cliente_http.post(URL, json=_pedido(canalPedido=canal), headers=entrar(email))

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [{"field": "canalPedido", "issue": problema}]


def test_cliente_nao_informa_cliente_id(cliente_http, entrar, id_do_usuario):
    outro_cliente = id_do_usuario(EMAIL_CLIENTE_SEM_CONSENTIMENTO)

    resposta = cliente_http.post(
        URL, json=_pedido(clienteId=outro_cliente), headers=entrar(EMAIL_CLIENTE)
    )

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [
        {"field": "clienteId", "issue": "Não se aplica ao perfil CLIENTE"}
    ]


@pytest.mark.parametrize(
    ("alteracao", "detalhe"),
    [
        (
            {"canalPedido": "FAX"},
            {
                "field": "canalPedido",
                "issue": "Deve ser um destes valores: 'APP', 'TOTEM', 'BALCAO', 'PICKUP' ou 'WEB'",
            },
        ),
        ({"itens": []}, {"field": "itens", "issue": "Deve ter pelo menos 1 item(ns)"}),
        (
            {"itens": [{"produtoId": TAPIOCA, "quantidade": -2}]},
            {"field": "itens[0].quantidade", "issue": "Deve ser maior que 0"},
        ),
        (
            {"itens": [{"produtoId": TAPIOCA, "quantidade": True}]},
            {"field": "itens[0].quantidade", "issue": QUANTIDADE_INTEIRA},
        ),
        (
            {"itens": [{"produtoId": TAPIOCA, "quantidade": "2"}]},
            {"field": "itens[0].quantidade", "issue": QUANTIDADE_INTEIRA},
        ),
        (
            {"itens": [{"produtoId": TAPIOCA, "quantidade": 2.5}]},
            {"field": "itens[0].quantidade", "issue": QUANTIDADE_INTEIRA},
        ),
        (
            {"formaPagamento": "PIX"},
            {"field": "formaPagamento", "issue": "Deve ser um destes valores: 'MOCK'"},
        ),
        (
            {"unidadeId": ID_MAXIMO + 1},
            {"field": "unidadeId", "issue": f"Deve ser menor ou igual a {ID_MAXIMO}"},
        ),
        (
            {
                "itens": [
                    {"produtoId": TAPIOCA, "quantidade": 1},
                    {"produtoId": TAPIOCA, "quantidade": 2},
                ]
            },
            {"field": "itens[1].produtoId", "issue": "Produto repetido no pedido"},
        ),
    ],
)
def test_rejeita_pedido_invalido(cliente_http, entrar, alteracao, detalhe):
    resposta = cliente_http.post(URL, json=_pedido(**alteracao), headers=entrar(EMAIL_CLIENTE))

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [detalhe]


def test_pedido_sem_canal_devolve_422(cliente_http, entrar):
    corpo = _pedido()
    del corpo["canalPedido"]

    resposta = cliente_http.post(URL, json=corpo, headers=entrar(EMAIL_CLIENTE))

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [{"field": "canalPedido", "issue": "Campo obrigatório"}]


def test_cliente_nao_define_total_nem_status(cliente_http, entrar):
    resposta = cliente_http.post(
        URL, json=_pedido(total=1, status="ENTREGUE"), headers=entrar(EMAIL_CLIENTE)
    )

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [
        {"field": "total", "issue": "Campo não permitido"},
        {"field": "status", "issue": "Campo não permitido"},
    ]


@pytest.mark.parametrize(
    "alteracao",
    [{"unidadeId": INEXISTENTE}, {"itens": [{"produtoId": INEXISTENTE, "quantidade": 1}]}],
)
def test_unidade_ou_produto_inexistente_devolve_404(cliente_http, entrar, alteracao):
    resposta = cliente_http.post(URL, json=_pedido(**alteracao), headers=entrar(EMAIL_CLIENTE))

    assert resposta.status_code == 404
    assert resposta.json()["error"] == "RECURSO_NAO_ENCONTRADO"


def test_produto_nao_ofertado_na_unidade_devolve_409(cliente_http, entrar):
    corpo = _pedido(
        unidadeId=UNIDADE_CARUARU,
        itens=[{"produtoId": CAFE_DA_MANHA_COMPLETO, "quantidade": 1}],
    )

    resposta = cliente_http.post(URL, json=corpo, headers=entrar(EMAIL_CLIENTE))

    assert resposta.status_code == 409
    assert resposta.json()["error"] == "PRODUTO_INDISPONIVEL_NA_UNIDADE"
    assert resposta.json()["details"] == [
        {"field": "itens[0].produtoId", "issue": f"Indisponível na unidade {UNIDADE_CARUARU}"}
    ]


def test_produto_inativo_devolve_409(cliente_http, entrar, banco_semeado):
    produto_id = _cadastrar_ofertado(cliente_http, entrar, banco_semeado)
    cliente_http.delete(f"/produtos/{produto_id}", headers=entrar(EMAIL_ADMIN))

    resposta = cliente_http.post(
        URL,
        json=_pedido(itens=[{"produtoId": produto_id, "quantidade": 1}]),
        headers=entrar(EMAIL_CLIENTE),
    )

    assert resposta.status_code == 409
    assert resposta.json()["error"] == "PRODUTO_INDISPONIVEL_NA_UNIDADE"


def test_produto_sazonal_fora_do_periodo_devolve_409(cliente_http, entrar, banco_semeado):
    hoje = datetime.now(UTC).date()
    produto_id = _cadastrar_ofertado(
        cliente_http,
        entrar,
        banco_semeado,
        disponivelDe=(hoje - timedelta(days=30)).isoformat(),
        disponivelAte=(hoje - timedelta(days=1)).isoformat(),
    )

    resposta = cliente_http.post(
        URL,
        json=_pedido(itens=[{"produtoId": produto_id, "quantidade": 1}]),
        headers=entrar(EMAIL_CLIENTE),
    )

    assert resposta.status_code == 409
    assert resposta.json()["error"] == "PRODUTO_INDISPONIVEL_NA_UNIDADE"


def test_estoque_insuficiente_devolve_409_sem_gravar_nada(
    cliente_http, entrar, banco_semeado, saldo_de_estoque
):
    saldo_do_bolo = saldo_de_estoque(UNIDADE_RECIFE, BOLO)
    saldo_da_tapioca = saldo_de_estoque(UNIDADE_RECIFE, TAPIOCA)
    pedidos = _total_de_pedidos(banco_semeado)
    corpo = _pedido(
        itens=[
            {"produtoId": TAPIOCA, "quantidade": 1},
            {"produtoId": BOLO, "quantidade": saldo_do_bolo + 1},
        ]
    )

    resposta = cliente_http.post(URL, json=corpo, headers=entrar(EMAIL_CLIENTE))

    assert resposta.status_code == 409
    assert resposta.json()["error"] == "ESTOQUE_INSUFICIENTE"
    assert resposta.json()["details"] == [
        {"field": "itens[1].quantidade", "issue": f"Disponível: {saldo_do_bolo}"}
    ]
    assert saldo_de_estoque(UNIDADE_RECIFE, TAPIOCA) == saldo_da_tapioca
    assert _total_de_pedidos(banco_semeado) == pedidos


def test_total_acima_do_teto_devolve_422(cliente_http, entrar, banco_semeado):
    produto_id = _cadastrar_ofertado(cliente_http, entrar, banco_semeado, preco=PRECO_MAXIMO)

    resposta = cliente_http.post(
        URL,
        json=_pedido(itens=[{"produtoId": produto_id, "quantidade": 2}]),
        headers=entrar(EMAIL_CLIENTE),
    )

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [{"field": "itens", "issue": "Total passa de 99999999.99"}]


@pytest.mark.parametrize("unidade_id", [UNIDADE_CARUARU, INEXISTENTE])
def test_atendente_nao_cria_pedido_fora_da_propria_unidade(cliente_http, entrar, unidade_id):
    resposta = cliente_http.post(
        URL, json=_balcao(unidadeId=unidade_id), headers=entrar(EMAIL_ATENDENTE_RECIFE)
    )

    assert resposta.status_code == 403
    assert resposta.json()["error"] == "ACESSO_NEGADO"


def test_atendente_com_cliente_inexistente_devolve_404(cliente_http, entrar):
    resposta = cliente_http.post(
        URL, json=_balcao(clienteId=INEXISTENTE), headers=entrar(EMAIL_ATENDENTE_RECIFE)
    )

    assert resposta.status_code == 404
    assert resposta.json()["message"] == f"Cliente {INEXISTENTE} não encontrado"


def test_funcionario_nao_e_cliente_do_pedido(cliente_http, entrar, id_do_usuario):
    admin_id = id_do_usuario(EMAIL_ADMIN)

    resposta = cliente_http.post(
        URL, json=_balcao(clienteId=admin_id), headers=entrar(EMAIL_ATENDENTE_RECIFE)
    )

    assert resposta.status_code == 404


@pytest.mark.parametrize("email", [EMAIL_GERENTE_RECIFE, EMAIL_COZINHA_RECIFE, EMAIL_ADMIN])
def test_perfil_sem_permissao_recebe_403_mesmo_com_body_invalido(cliente_http, entrar, email):
    resposta = cliente_http.post(URL, json=_pedido(canalPedido="FAX"), headers=entrar(email))

    assert resposta.status_code == 403


def test_pedido_sem_token_devolve_401(cliente_http):
    assert cliente_http.post(URL, json=_pedido()).status_code == 401
