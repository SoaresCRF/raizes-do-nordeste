import json
import re

import pytest

from src.infrastructure.database.seeds.dados_iniciais import DOMINIO_EMAIL

URL = "/auditoria"
UNIDADE_RECIFE = 1
UNIDADE_CARUARU = 2
FORMATO_DATA_HORA_UTC = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"
EMAIL_ADMIN = f"admin@{DOMINIO_EMAIL}"
EMAIL_GERENTE_RECIFE = f"gerente.recife@{DOMINIO_EMAIL}"
EMAIL_GERENTE_CARUARU = f"gerente.caruaru@{DOMINIO_EMAIL}"
EMAIL_ATENDENTE_RECIFE = f"atendente.recife@{DOMINIO_EMAIL}"
EMAIL_COZINHA_RECIFE = f"cozinha.recife@{DOMINIO_EMAIL}"
EMAIL_CLIENTE = f"cliente@{DOMINIO_EMAIL}"


def _consultar(cliente_http, headers: dict, consulta: str = ""):
    return cliente_http.get(f"{URL}?limit=100&{consulta}", headers=headers)


def _acoes(resposta) -> list[str]:
    return [item["acao"] for item in resposta.json()["dados"]]


def _pedido_pago_e_pronto(cliente_http, entrar, fazer_pedido, pagar_pedido) -> int:
    criado = fazer_pedido()
    pagar_pedido(criado["pedidoId"], entrar(EMAIL_CLIENTE))
    resposta = cliente_http.patch(
        f"/pedidos/{criado['pedidoId']}/status",
        json={"status": "PRONTO"},
        headers=entrar(EMAIL_COZINHA_RECIFE),
    )
    assert resposta.status_code == 200, resposta.text
    return criado["pedidoId"]


def test_trilha_do_pedido_tem_criacao_e_mudancas_de_status(
    cliente_http, entrar, fazer_pedido, pagar_pedido, id_do_usuario
):
    pedido_id = _pedido_pago_e_pronto(cliente_http, entrar, fazer_pedido, pagar_pedido)

    resposta = _consultar(
        cliente_http, entrar(EMAIL_GERENTE_RECIFE), f"entidade=Pedido&entidadeId={pedido_id}"
    )
    dados = resposta.json()["dados"]

    assert resposta.status_code == 200
    assert _acoes(resposta) == ["STATUS_ALTERADO", "STATUS_ALTERADO", "PEDIDO_CRIADO"]
    assert [item["usuarioId"] for item in dados] == [
        id_do_usuario(EMAIL_COZINHA_RECIFE),
        id_do_usuario(EMAIL_CLIENTE),
        id_do_usuario(EMAIL_CLIENTE),
    ]
    assert set(dados[0]) == {
        "logId",
        "usuarioId",
        "unidadeId",
        "acao",
        "entidade",
        "entidadeId",
        "dadosAntes",
        "dadosDepois",
        "requestId",
        "createdAt",
    }
    assert {(item["entidade"], item["entidadeId"], item["unidadeId"]) for item in dados} == {
        ("Pedido", pedido_id, UNIDADE_RECIFE)
    }
    assert all(re.fullmatch(FORMATO_DATA_HORA_UTC, item["createdAt"]) for item in dados)
    assert all(item["requestId"] for item in dados)


def test_filtra_por_acao(cliente_http, entrar, fazer_pedido, pagar_pedido):
    pedido_id = _pedido_pago_e_pronto(cliente_http, entrar, fazer_pedido, pagar_pedido)

    resposta = _consultar(
        cliente_http,
        entrar(EMAIL_ADMIN),
        f"entidade=Pedido&entidadeId={pedido_id}&acao=PEDIDO_CRIADO",
    )

    assert _acoes(resposta) == ["PEDIDO_CRIADO"]


def test_pagina_a_trilha(cliente_http, entrar, fazer_pedido, pagar_pedido):
    pedido_id = _pedido_pago_e_pronto(cliente_http, entrar, fazer_pedido, pagar_pedido)

    resposta = cliente_http.get(
        f"{URL}?entidade=Pedido&entidadeId={pedido_id}&page=2&limit=1",
        headers=entrar(EMAIL_ADMIN),
    )

    assert resposta.json()["paginacao"] == {"page": 2, "limit": 1, "total": 3, "totalPaginas": 3}
    assert _acoes(resposta) == ["STATUS_ALTERADO"]


def test_acesso_a_dados_pessoais_fica_registrado_sem_os_dados(
    cliente_http, entrar, fazer_pedido, cliente_novo, id_do_usuario
):
    criado = fazer_pedido(cliente_novo["email"], cliente_novo["senha"])
    gerente = entrar(EMAIL_GERENTE_RECIFE)
    assert cliente_http.get(f"/pedidos/{criado['pedidoId']}", headers=gerente).status_code == 200

    resposta = _consultar(
        cliente_http,
        gerente,
        f"acao=ACESSO_DADOS_PESSOAIS&entidade=Usuario&entidadeId={cliente_novo['id']}",
    )
    [registro] = resposta.json()["dados"]

    assert registro["usuarioId"] == id_do_usuario(EMAIL_GERENTE_RECIFE)
    assert registro["dadosAntes"] is None
    assert registro["dadosDepois"] == {"pedidoId": criado["pedidoId"]}
    texto = json.dumps(registro, ensure_ascii=False)
    assert cliente_novo["email"] not in texto
    assert cliente_novo["nome"] not in texto


def test_gerente_nao_le_auditoria_de_outra_unidade(cliente_http, entrar):
    resposta = _consultar(
        cliente_http, entrar(EMAIL_GERENTE_RECIFE), f"unidadeId={UNIDADE_CARUARU}"
    )

    assert resposta.status_code == 403
    assert resposta.json()["error"] == "ACESSO_NEGADO"


def test_gerente_sem_filtro_ve_so_a_propria_unidade(cliente_http, entrar, fazer_pedido):
    pedido_de_recife = fazer_pedido()["pedidoId"]

    resposta = _consultar(
        cliente_http,
        entrar(EMAIL_GERENTE_CARUARU),
        f"entidade=Pedido&entidadeId={pedido_de_recife}",
    )

    assert resposta.status_code == 200
    assert resposta.json()["dados"] == []
    assert resposta.json()["paginacao"]["total"] == 0


def test_alteracao_de_produto_so_aparece_para_o_admin(cliente_http, entrar):
    admin = entrar(EMAIL_ADMIN)
    produto = {"nome": "Baião de dois", "descricao": "Arroz, feijão e queijo", "preco": 32.5}
    criado = cliente_http.post("/produtos", json=produto, headers=admin)
    assert criado.status_code == 201, criado.text
    produto_id = criado.json()["id"]
    alterado = cliente_http.put(
        f"/produtos/{produto_id}", json=produto | {"preco": 34.0, "ativo": True}, headers=admin
    )
    assert alterado.status_code == 200, alterado.text
    consulta = f"entidade=Produto&entidadeId={produto_id}"

    do_admin = _consultar(cliente_http, admin, consulta)
    do_gerente = _consultar(cliente_http, entrar(EMAIL_GERENTE_RECIFE), consulta)

    assert _acoes(do_admin) == ["PRODUTO_ALTERADO"]
    assert do_admin.json()["dados"][0]["unidadeId"] is None
    assert do_gerente.json()["dados"] == []


@pytest.mark.parametrize("email", [EMAIL_CLIENTE, EMAIL_ATENDENTE_RECIFE, EMAIL_COZINHA_RECIFE])
def test_perfil_sem_permissao_nao_le_auditoria(cliente_http, entrar, email):
    resposta = _consultar(cliente_http, entrar(email))

    assert resposta.status_code == 403
    assert resposta.json()["error"] == "ACESSO_NEGADO"


def test_cliente_recebe_403_mesmo_com_filtro_invalido(cliente_http, entrar):
    resposta = _consultar(cliente_http, entrar(EMAIL_CLIENTE), "acao=XPTO")

    assert resposta.status_code == 403


@pytest.mark.parametrize(
    ("consulta", "detalhe"),
    [
        ("entidadeId=0", {"field": "entidadeId", "issue": "Deve ser maior que 0"}),
        ("unidadeId=abc", {"field": "unidadeId", "issue": "Deve ser um número inteiro"}),
        ("entidade=", {"field": "entidade", "issue": "Deve ter pelo menos 1 caractere(s)"}),
        (
            f"entidade={'x' * 41}",
            {"field": "entidade", "issue": "Deve ter no máximo 40 caracteres"},
        ),
        ("entidade=Pe%00dido", {"field": "entidade", "issue": "Não pode conter o caractere nulo"}),
    ],
)
def test_filtro_invalido_devolve_422(cliente_http, entrar, consulta, detalhe):
    resposta = _consultar(cliente_http, entrar(EMAIL_ADMIN), consulta)

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [detalhe]


def test_acao_fora_do_catalogo_devolve_422(cliente_http, entrar):
    resposta = _consultar(cliente_http, entrar(EMAIL_ADMIN), "acao=XPTO")
    [detalhe] = resposta.json()["details"]

    assert resposta.status_code == 422
    assert detalhe["field"] == "acao"
    assert detalhe["issue"].startswith("Deve ser um destes valores: 'UNIDADE_CRIADA'")


def test_auditoria_sem_token_devolve_401(cliente_http):
    assert cliente_http.get(URL).status_code == 401
