import pytest
from sqlalchemy import insert, select

from src.infrastructure.database.seeds.dados_iniciais import DOMINIO_EMAIL
from src.infrastructure.database.tabelas import log_auditoria, pagamento

URL = "/pedidos"
UNIDADE_RECIFE = 1
UNIDADE_CARUARU = 2
INEXISTENTE = 9999
EMAIL_ADMIN = f"admin@{DOMINIO_EMAIL}"
EMAIL_GERENTE_RECIFE = f"gerente.recife@{DOMINIO_EMAIL}"
EMAIL_GERENTE_CARUARU = f"gerente.caruaru@{DOMINIO_EMAIL}"
EMAIL_ATENDENTE_RECIFE = f"atendente.recife@{DOMINIO_EMAIL}"
EMAIL_COZINHA_RECIFE = f"cozinha.recife@{DOMINIO_EMAIL}"
EMAIL_CLIENTE = f"cliente@{DOMINIO_EMAIL}"
EMAIL_CLIENTE_SEM_CONSENTIMENTO = f"cliente.sem.consentimento@{DOMINIO_EMAIL}"
FUNCIONARIOS_DE_RECIFE = [EMAIL_ATENDENTE_RECIFE, EMAIL_COZINHA_RECIFE, EMAIL_GERENTE_RECIFE]


def _listar(cliente_http, headers: dict, consulta: str = ""):
    return cliente_http.get(f"{URL}?limit=100&{consulta}", headers=headers)


def _ids(resposta) -> list[int]:
    return [item["pedidoId"] for item in resposta.json()["dados"]]


def _consultar(cliente_http, headers: dict, pedido_id: int):
    return cliente_http.get(f"{URL}/{pedido_id}", headers=headers)


def _logs_de_acesso(banco_semeado, pedido_id: int) -> list:
    with banco_semeado.connect() as conexao:
        return conexao.execute(
            select(log_auditoria).where(
                log_auditoria.c.acao == "ACESSO_DADOS_PESSOAIS",
                log_auditoria.c.dados_depois["pedidoId"].as_integer() == pedido_id,
            )
        ).all()


def test_cliente_lista_so_os_proprios_pedidos(cliente_http, entrar, fazer_pedido, id_do_usuario):
    proprio = fazer_pedido()
    alheio = fazer_pedido(EMAIL_CLIENTE_SEM_CONSENTIMENTO)

    resposta = _listar(cliente_http, entrar(EMAIL_CLIENTE))

    assert resposta.status_code == 200
    assert proprio["pedidoId"] in _ids(resposta)
    assert alheio["pedidoId"] not in _ids(resposta)
    assert {item["clienteId"] for item in resposta.json()["dados"]} == {
        id_do_usuario(EMAIL_CLIENTE)
    }


def test_listagem_traz_o_resumo_do_pedido(cliente_http, entrar, fazer_pedido):
    criado = fazer_pedido()

    resposta = _listar(cliente_http, entrar(EMAIL_CLIENTE))

    [item] = [i for i in resposta.json()["dados"] if i["pedidoId"] == criado["pedidoId"]]
    assert item == {campo: valor for campo, valor in criado.items() if campo != "itens"}


@pytest.mark.parametrize("email", FUNCIONARIOS_DE_RECIFE)
def test_funcionario_lista_os_pedidos_da_propria_unidade(cliente_http, entrar, fazer_pedido, email):
    de_recife = fazer_pedido()
    de_caruaru = fazer_pedido(unidadeId=UNIDADE_CARUARU)

    resposta = _listar(cliente_http, entrar(email))

    assert de_recife["pedidoId"] in _ids(resposta)
    assert de_caruaru["pedidoId"] not in _ids(resposta)


def test_funcionario_nao_lista_outra_unidade(cliente_http, entrar):
    resposta = _listar(cliente_http, entrar(EMAIL_GERENTE_RECIFE), f"unidadeId={UNIDADE_CARUARU}")

    assert resposta.status_code == 403
    assert resposta.json()["error"] == "ACESSO_NEGADO"


def test_admin_lista_todas_as_unidades(cliente_http, entrar, fazer_pedido):
    de_recife = fazer_pedido()
    de_caruaru = fazer_pedido(unidadeId=UNIDADE_CARUARU)
    admin = entrar(EMAIL_ADMIN)

    todos = _listar(cliente_http, admin)
    so_caruaru = _listar(cliente_http, admin, f"unidadeId={UNIDADE_CARUARU}")

    assert {de_recife["pedidoId"], de_caruaru["pedidoId"]} <= set(_ids(todos))
    assert de_caruaru["pedidoId"] in _ids(so_caruaru)
    assert de_recife["pedidoId"] not in _ids(so_caruaru)


def test_filtra_por_canal(cliente_http, entrar, fazer_pedido):
    totem = fazer_pedido(canalPedido="TOTEM")
    web = fazer_pedido(canalPedido="WEB")

    resposta = _listar(cliente_http, entrar(EMAIL_GERENTE_RECIFE), "canalPedido=TOTEM")

    assert totem["pedidoId"] in _ids(resposta)
    assert web["pedidoId"] not in _ids(resposta)
    assert {item["canalPedido"] for item in resposta.json()["dados"]} == {"TOTEM"}


def test_filtra_por_status(cliente_http, entrar, fazer_pedido, definir_status_do_pedido):
    em_preparo = fazer_pedido()
    aguardando = fazer_pedido()
    definir_status_do_pedido(em_preparo["pedidoId"], "EM_PREPARO")

    resposta = _listar(cliente_http, entrar(EMAIL_GERENTE_RECIFE), "status=EM_PREPARO")

    assert em_preparo["pedidoId"] in _ids(resposta)
    assert aguardando["pedidoId"] not in _ids(resposta)
    assert {item["status"] for item in resposta.json()["dados"]} == {"EM_PREPARO"}


def test_lista_do_mais_recente_para_o_mais_antigo(cliente_http, entrar, fazer_pedido):
    primeiro = fazer_pedido()
    segundo = fazer_pedido()

    ids = _ids(_listar(cliente_http, entrar(EMAIL_CLIENTE)))

    assert ids.index(segundo["pedidoId"]) < ids.index(primeiro["pedidoId"])
    assert ids == sorted(ids, reverse=True)


@pytest.mark.parametrize(
    ("consulta", "detalhe"),
    [
        (
            "canalPedido=XPTO",
            {
                "field": "canalPedido",
                "issue": "Deve ser um destes valores: 'APP', 'TOTEM', 'BALCAO', 'PICKUP' ou 'WEB'",
            },
        ),
        (
            "status=PAGO",
            {
                "field": "status",
                "issue": "Deve ser um destes valores: 'AGUARDANDO_PAGAMENTO', 'EM_PREPARO', "
                "'PRONTO', 'ENTREGUE' ou 'CANCELADO'",
            },
        ),
        ("unidadeId=0", {"field": "unidadeId", "issue": "Deve ser maior que 0"}),
    ],
)
def test_filtro_invalido_devolve_422(cliente_http, entrar, consulta, detalhe):
    resposta = _listar(cliente_http, entrar(EMAIL_GERENTE_RECIFE), consulta)

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [detalhe]


def test_listagem_sem_token_devolve_401(cliente_http):
    resposta = cliente_http.get(URL)

    assert resposta.status_code == 401
    assert resposta.json()["error"] == "NAO_AUTENTICADO"


def test_cliente_consulta_o_proprio_pedido(cliente_http, entrar, fazer_pedido, id_do_usuario):
    criado = fazer_pedido()

    resposta = _consultar(cliente_http, entrar(EMAIL_CLIENTE), criado["pedidoId"])
    corpo = resposta.json()

    assert resposta.status_code == 200
    assert corpo == criado | {
        "motivoCancelamento": None,
        "cliente": {"id": id_do_usuario(EMAIL_CLIENTE), "nome": "Maria Cliente"},
        "ultimoPagamento": None,
        "updatedAt": corpo["updatedAt"],
    }


def test_cliente_nao_ve_pedido_de_outro_cliente(cliente_http, entrar, fazer_pedido):
    alheio = fazer_pedido(EMAIL_CLIENTE_SEM_CONSENTIMENTO)

    resposta = _consultar(cliente_http, entrar(EMAIL_CLIENTE), alheio["pedidoId"])

    assert resposta.status_code == 404
    assert resposta.json()["message"] == f"Pedido {alheio['pedidoId']} não encontrado"


def test_pedido_inexistente_devolve_404(cliente_http, entrar):
    resposta = _consultar(cliente_http, entrar(EMAIL_CLIENTE), INEXISTENTE)

    assert resposta.status_code == 404
    assert resposta.json()["error"] == "RECURSO_NAO_ENCONTRADO"


@pytest.mark.parametrize("email", [*FUNCIONARIOS_DE_RECIFE, EMAIL_ADMIN])
def test_funcionario_da_unidade_e_admin_consultam_o_pedido(
    cliente_http, entrar, fazer_pedido, email
):
    criado = fazer_pedido()

    resposta = _consultar(cliente_http, entrar(email), criado["pedidoId"])

    assert resposta.status_code == 200


def test_funcionario_de_outra_unidade_recebe_403(cliente_http, entrar, fazer_pedido):
    criado = fazer_pedido()

    resposta = _consultar(cliente_http, entrar(EMAIL_GERENTE_CARUARU), criado["pedidoId"])

    assert resposta.status_code == 403


def test_funcionario_que_ve_dados_do_cliente_gera_log_sem_os_dados(
    cliente_http, entrar, fazer_pedido, banco_semeado, id_do_usuario
):
    criado = fazer_pedido()

    _consultar(cliente_http, entrar(EMAIL_GERENTE_RECIFE), criado["pedidoId"])

    [registro] = _logs_de_acesso(banco_semeado, criado["pedidoId"])
    assert (
        registro.entidade,
        registro.entidade_id,
        registro.usuario_id,
        registro.unidade_id,
    ) == (
        "Usuario",
        id_do_usuario(EMAIL_CLIENTE),
        id_do_usuario(EMAIL_GERENTE_RECIFE),
        UNIDADE_RECIFE,
    )
    assert registro.dados_antes is None
    assert registro.dados_depois == {"pedidoId": criado["pedidoId"]}


def test_cliente_que_ve_o_proprio_pedido_nao_gera_log(
    cliente_http, entrar, fazer_pedido, banco_semeado
):
    criado = fazer_pedido()

    _consultar(cliente_http, entrar(EMAIL_CLIENTE), criado["pedidoId"])

    assert _logs_de_acesso(banco_semeado, criado["pedidoId"]) == []


def test_pedido_de_balcao_sem_cliente_nao_gera_log(
    cliente_http, entrar, fazer_pedido, banco_semeado
):
    criado = fazer_pedido(EMAIL_ATENDENTE_RECIFE, canalPedido="BALCAO")

    resposta = _consultar(cliente_http, entrar(EMAIL_GERENTE_RECIFE), criado["pedidoId"])

    assert resposta.json()["cliente"] is None
    assert _logs_de_acesso(banco_semeado, criado["pedidoId"]) == []


def test_consulta_traz_o_ultimo_pagamento(cliente_http, entrar, fazer_pedido, banco_semeado):
    criado = fazer_pedido()
    tentativa = {
        "pedido_id": criado["pedidoId"],
        "valor": criado["total"],
        "forma_pagamento": "MOCK",
    }
    # Gravados direto: o teste só depende da ordem das tentativas, não do gateway.
    with banco_semeado.begin() as conexao:
        pagamento_ids = (
            conexao.execute(
                insert(pagamento).returning(pagamento.c.id, sort_by_parameter_order=True),
                [tentativa | {"status": "RECUSADO"}, tentativa | {"status": "APROVADO"}],
            )
            .scalars()
            .all()
        )

    corpo = _consultar(cliente_http, entrar(EMAIL_CLIENTE), criado["pedidoId"]).json()

    assert corpo["ultimoPagamento"] == {
        "pagamentoId": pagamento_ids[1],
        "status": "APROVADO",
        "valor": criado["total"],
        "createdAt": corpo["ultimoPagamento"]["createdAt"],
    }


def test_id_invalido_devolve_422(cliente_http, entrar):
    resposta = _consultar(cliente_http, entrar(EMAIL_CLIENTE), 0)

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [{"field": "id", "issue": "Deve ser maior que 0"}]


def test_consulta_sem_token_devolve_401(cliente_http):
    assert cliente_http.get(f"{URL}/1").status_code == 401
