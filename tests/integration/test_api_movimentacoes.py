import re

import pytest
from sqlalchemy import func, select

from src.domain.estoque.estoque import SALDO_MAXIMO
from src.infrastructure.database.seeds.dados_iniciais import DOMINIO_EMAIL
from src.infrastructure.database.tabelas import (
    estoque,
    log_auditoria,
    movimentacao_estoque,
    usuario,
)

URL = "/estoque/movimentacoes"
UNIDADE_RECIFE = 1
UNIDADE_CARUARU = 2
UNIDADE_INEXISTENTE = 9999
PRODUTO_INEXISTENTE = 9999
TAPIOCA = 1
BOLO = 3
SUCO = 4
CAFE_PASSADO = 6
ID_MAXIMO = 2_147_483_647
EMAIL_ADMIN = f"admin@{DOMINIO_EMAIL}"
EMAIL_GERENTE_RECIFE = f"gerente.recife@{DOMINIO_EMAIL}"
EMAIL_ATENDENTE_RECIFE = f"atendente.recife@{DOMINIO_EMAIL}"
EMAIL_COZINHA_RECIFE = f"cozinha.recife@{DOMINIO_EMAIL}"
EMAIL_CLIENTE = f"cliente@{DOMINIO_EMAIL}"
FORMATO_DATA_HORA_UTC = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"


def _movimentacao(**alteracoes) -> dict:
    return {
        "unidadeId": UNIDADE_RECIFE,
        "produtoId": TAPIOCA,
        "tipo": "ENTRADA",
        "quantidade": 10,
        "motivo": "Reposição semanal",
    } | alteracoes


def _saldo(banco_semeado, unidade_id: int, produto_id: int) -> int | None:
    with banco_semeado.connect() as conexao:
        return conexao.execute(
            select(estoque.c.quantidade).where(
                estoque.c.unidade_id == unidade_id, estoque.c.produto_id == produto_id
            )
        ).scalar_one_or_none()


def _total_de_auditorias(banco_semeado) -> int:
    with banco_semeado.connect() as conexao:
        return conexao.execute(
            select(func.count())
            .select_from(log_auditoria)
            .where(log_auditoria.c.acao == "ESTOQUE_MOVIMENTADO")
        ).scalar_one()


def _id_do_usuario(banco_semeado, email: str) -> int:
    with banco_semeado.connect() as conexao:
        return conexao.execute(select(usuario.c.id).where(usuario.c.email == email)).scalar_one()


def _cadastrar_produto(cliente_http, entrar) -> int:
    resposta = cliente_http.post(
        "/produtos", json={"nome": "Arrumadinho", "preco": 27.0}, headers=entrar(EMAIL_ADMIN)
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()["id"]


def test_gerente_registra_entrada_na_propria_unidade(cliente_http, entrar, banco_semeado):
    anterior = _saldo(banco_semeado, UNIDADE_RECIFE, TAPIOCA)

    resposta = cliente_http.post(URL, json=_movimentacao(), headers=entrar(EMAIL_GERENTE_RECIFE))
    corpo = resposta.json()

    assert resposta.status_code == 201
    assert corpo == {
        "movimentacaoId": corpo["movimentacaoId"],
        "tipo": "ENTRADA",
        "quantidade": 10,
        "saldoAtual": anterior + 10,
    }
    assert _saldo(banco_semeado, UNIDADE_RECIFE, TAPIOCA) == anterior + 10


def test_movimentacao_fica_registrada_e_auditada(cliente_http, entrar, banco_semeado):
    gerente_id = _id_do_usuario(banco_semeado, EMAIL_GERENTE_RECIFE)
    anterior = _saldo(banco_semeado, UNIDADE_RECIFE, SUCO)

    corpo = cliente_http.post(
        URL,
        json=_movimentacao(produtoId=SUCO, tipo="SAIDA", quantidade=3, motivo="Avaria"),
        headers=entrar(EMAIL_GERENTE_RECIFE),
    ).json()

    with banco_semeado.connect() as conexao:
        movimentacao = conexao.execute(
            select(movimentacao_estoque).where(movimentacao_estoque.c.id == corpo["movimentacaoId"])
        ).one()
        auditoria = conexao.execute(
            select(log_auditoria).where(
                log_auditoria.c.acao == "ESTOQUE_MOVIMENTADO",
                log_auditoria.c.dados_depois["movimentacaoId"].as_integer()
                == corpo["movimentacaoId"],
            )
        ).one()
    assert (
        movimentacao.tipo,
        movimentacao.quantidade,
        movimentacao.motivo,
        movimentacao.usuario_id,
        movimentacao.pedido_id,
    ) == ("SAIDA", 3, "Avaria", gerente_id, None)
    assert (auditoria.usuario_id, auditoria.unidade_id) == (gerente_id, UNIDADE_RECIFE)
    assert (auditoria.entidade, auditoria.entidade_id) == ("Estoque", movimentacao.estoque_id)
    assert auditoria.dados_antes == {"produtoId": SUCO, "quantidade": anterior}
    assert auditoria.dados_depois == {
        "produtoId": SUCO,
        "quantidade": anterior - 3,
        "movimentacaoId": corpo["movimentacaoId"],
        "tipo": "SAIDA",
        "motivo": "Avaria",
    }
    assert auditoria.request_id is not None


def test_saida_maior_que_o_saldo_devolve_409(cliente_http, entrar, banco_semeado):
    anterior = _saldo(banco_semeado, UNIDADE_RECIFE, BOLO)
    auditorias = _total_de_auditorias(banco_semeado)

    resposta = cliente_http.post(
        URL,
        json=_movimentacao(produtoId=BOLO, tipo="SAIDA", quantidade=anterior + 1),
        headers=entrar(EMAIL_GERENTE_RECIFE),
    )

    assert resposta.status_code == 409
    assert resposta.json()["error"] == "ESTOQUE_INSUFICIENTE"
    assert resposta.json()["details"] == [
        {"field": "quantidade", "issue": f"Disponível: {anterior}"}
    ]
    assert _saldo(banco_semeado, UNIDADE_RECIFE, BOLO) == anterior
    assert _total_de_auditorias(banco_semeado) == auditorias


def test_saida_de_produto_nao_ofertado_nao_cria_estoque(cliente_http, entrar, banco_semeado):
    produto_id = _cadastrar_produto(cliente_http, entrar)

    resposta = cliente_http.post(
        URL,
        json=_movimentacao(produtoId=produto_id, tipo="SAIDA", quantidade=1),
        headers=entrar(EMAIL_ADMIN),
    )

    assert resposta.status_code == 409
    assert resposta.json()["details"] == [{"field": "quantidade", "issue": "Disponível: 0"}]
    assert _saldo(banco_semeado, UNIDADE_RECIFE, produto_id) is None


def test_primeira_entrada_passa_a_ofertar_o_produto(cliente_http, entrar, banco_semeado):
    produto_id = _cadastrar_produto(cliente_http, entrar)

    resposta = cliente_http.post(
        URL, json=_movimentacao(produtoId=produto_id, quantidade=5), headers=entrar(EMAIL_ADMIN)
    )

    assert resposta.status_code == 201
    assert resposta.json()["saldoAtual"] == 5
    cardapio = cliente_http.get(f"/unidades/{UNIDADE_RECIFE}/cardapio?limit=100").json()
    assert produto_id in [item["produtoId"] for item in cardapio["dados"]]


def test_entrada_que_estoura_o_saldo_devolve_422(cliente_http, entrar, banco_semeado):
    anterior = _saldo(banco_semeado, UNIDADE_RECIFE, TAPIOCA)

    resposta = cliente_http.post(
        URL, json=_movimentacao(quantidade=SALDO_MAXIMO), headers=entrar(EMAIL_ADMIN)
    )

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [
        {"field": "quantidade", "issue": f"Saldo resultante passa de {SALDO_MAXIMO}"}
    ]
    assert _saldo(banco_semeado, UNIDADE_RECIFE, TAPIOCA) == anterior


@pytest.mark.parametrize(
    ("alteracao", "detalhe"),
    [
        ({"quantidade": -5}, {"field": "quantidade", "issue": "Deve ser maior que 0"}),
        ({"quantidade": 0}, {"field": "quantidade", "issue": "Deve ser maior que 0"}),
        ({"quantidade": 2.5}, {"field": "quantidade", "issue": "Deve ser um número inteiro"}),
        ({"quantidade": True}, {"field": "quantidade", "issue": "Deve ser um número inteiro"}),
        ({"quantidade": "10"}, {"field": "quantidade", "issue": "Deve ser um número inteiro"}),
        (
            {"quantidade": SALDO_MAXIMO + 1},
            {"field": "quantidade", "issue": f"Deve ser menor ou igual a {SALDO_MAXIMO}"},
        ),
        (
            {"tipo": "AJUSTE"},
            {"field": "tipo", "issue": "Deve ser um destes valores: 'ENTRADA' ou 'SAIDA'"},
        ),
        ({"motivo": "   "}, {"field": "motivo", "issue": "Deve ter pelo menos 1 caractere(s)"}),
        (
            {"motivo": "x" * 201},
            {"field": "motivo", "issue": "Deve ter no máximo 200 caracteres"},
        ),
        (
            {"unidadeId": ID_MAXIMO + 1},
            {"field": "unidadeId", "issue": f"Deve ser menor ou igual a {ID_MAXIMO}"},
        ),
    ],
)
def test_rejeita_movimentacao_invalida(cliente_http, entrar, alteracao, detalhe):
    resposta = cliente_http.post(
        URL, json=_movimentacao(**alteracao), headers=entrar(EMAIL_GERENTE_RECIFE)
    )

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [detalhe]


def test_movimentacao_sem_motivo_devolve_422(cliente_http, entrar):
    corpo = _movimentacao()
    del corpo["motivo"]

    resposta = cliente_http.post(URL, json=corpo, headers=entrar(EMAIL_GERENTE_RECIFE))

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [{"field": "motivo", "issue": "Campo obrigatório"}]


def test_gerente_nao_movimenta_outra_unidade(cliente_http, entrar, banco_semeado):
    anterior = _saldo(banco_semeado, UNIDADE_CARUARU, TAPIOCA)

    resposta = cliente_http.post(
        URL, json=_movimentacao(unidadeId=UNIDADE_CARUARU), headers=entrar(EMAIL_GERENTE_RECIFE)
    )

    assert resposta.status_code == 403
    assert resposta.json()["error"] == "ACESSO_NEGADO"
    assert _saldo(banco_semeado, UNIDADE_CARUARU, TAPIOCA) == anterior


def test_admin_movimenta_qualquer_unidade(cliente_http, entrar):
    resposta = cliente_http.post(
        URL, json=_movimentacao(unidadeId=UNIDADE_CARUARU), headers=entrar(EMAIL_ADMIN)
    )

    assert resposta.status_code == 201


@pytest.mark.parametrize("email", [EMAIL_ATENDENTE_RECIFE, EMAIL_COZINHA_RECIFE, EMAIL_CLIENTE])
def test_perfil_sem_permissao_recebe_403_mesmo_com_body_invalido(cliente_http, entrar, email):
    resposta = cliente_http.post(URL, json=_movimentacao(quantidade=-5), headers=entrar(email))

    assert resposta.status_code == 403


@pytest.mark.parametrize(
    "alteracao", [{"unidadeId": UNIDADE_INEXISTENTE}, {"produtoId": PRODUTO_INEXISTENTE}]
)
def test_unidade_ou_produto_inexistente_devolve_404(cliente_http, entrar, alteracao):
    resposta = cliente_http.post(URL, json=_movimentacao(**alteracao), headers=entrar(EMAIL_ADMIN))

    assert resposta.status_code == 404
    assert resposta.json()["error"] == "RECURSO_NAO_ENCONTRADO"


def test_movimentacao_sem_token_devolve_401(cliente_http):
    assert cliente_http.post(URL, json=_movimentacao()).status_code == 401


def _historico(cliente_http, headers: dict, consulta: str):
    return cliente_http.get(f"{URL}?{consulta}", headers=headers)


def test_gerente_consulta_historico_da_propria_unidade(cliente_http, entrar, banco_semeado):
    gerente = entrar(EMAIL_GERENTE_RECIFE)
    gerente_id = _id_do_usuario(banco_semeado, EMAIL_GERENTE_RECIFE)
    criada = cliente_http.post(
        URL,
        json=_movimentacao(produtoId=CAFE_PASSADO, quantidade=4, motivo="Compra do fornecedor"),
        headers=gerente,
    ).json()
    with banco_semeado.connect() as conexao:
        total = conexao.execute(
            select(func.count())
            .select_from(
                movimentacao_estoque.join(
                    estoque, estoque.c.id == movimentacao_estoque.c.estoque_id
                )
            )
            .where(estoque.c.unidade_id == UNIDADE_RECIFE)
        ).scalar_one()

    resposta = _historico(cliente_http, gerente, f"unidadeId={UNIDADE_RECIFE}")
    corpo = resposta.json()

    assert resposta.status_code == 200
    assert corpo["paginacao"]["total"] == total
    mais_recente = corpo["dados"][0]
    assert mais_recente == {
        "movimentacaoId": criada["movimentacaoId"],
        "produtoId": CAFE_PASSADO,
        "tipo": "ENTRADA",
        "quantidade": 4,
        "motivo": "Compra do fornecedor",
        "pedidoId": None,
        "usuarioId": gerente_id,
        "createdAt": mais_recente["createdAt"],
    }
    assert re.fullmatch(FORMATO_DATA_HORA_UTC, mais_recente["createdAt"])


def test_historico_filtra_por_produto(cliente_http, entrar):
    gerente = entrar(EMAIL_GERENTE_RECIFE)
    cliente_http.post(URL, json=_movimentacao(produtoId=SUCO), headers=gerente)
    cliente_http.post(URL, json=_movimentacao(produtoId=TAPIOCA), headers=gerente)

    resposta = _historico(
        cliente_http, gerente, f"unidadeId={UNIDADE_RECIFE}&produtoId={SUCO}&limit=100"
    )

    produto_ids = {item["produtoId"] for item in resposta.json()["dados"]}
    assert produto_ids == {SUCO}


def test_historico_vem_do_mais_recente_para_o_mais_antigo(cliente_http, entrar):
    gerente = entrar(EMAIL_GERENTE_RECIFE)
    primeira = cliente_http.post(URL, json=_movimentacao(), headers=gerente).json()
    segunda = cliente_http.post(URL, json=_movimentacao(), headers=gerente).json()

    resposta = _historico(cliente_http, gerente, f"unidadeId={UNIDADE_RECIFE}&limit=100")

    ids = [item["movimentacaoId"] for item in resposta.json()["dados"]]
    assert segunda["movimentacaoId"] > primeira["movimentacaoId"]
    assert ids == sorted(ids, reverse=True)
    assert len(set(ids)) == len(ids)
    assert ids.index(segunda["movimentacaoId"]) < ids.index(primeira["movimentacaoId"])


def test_historico_nao_mistura_unidades(cliente_http, entrar):
    admin = entrar(EMAIL_ADMIN)
    criada = cliente_http.post(
        URL, json=_movimentacao(unidadeId=UNIDADE_CARUARU), headers=admin
    ).json()

    recife = _historico(cliente_http, admin, f"unidadeId={UNIDADE_RECIFE}&limit=100").json()
    caruaru = _historico(cliente_http, admin, f"unidadeId={UNIDADE_CARUARU}&limit=100").json()

    assert criada["movimentacaoId"] not in [i["movimentacaoId"] for i in recife["dados"]]
    assert criada["movimentacaoId"] in [i["movimentacaoId"] for i in caruaru["dados"]]


def test_gerente_nao_consulta_historico_de_outra_unidade(cliente_http, entrar):
    resposta = _historico(
        cliente_http, entrar(EMAIL_GERENTE_RECIFE), f"unidadeId={UNIDADE_CARUARU}"
    )

    assert resposta.status_code == 403


@pytest.mark.parametrize("email", [EMAIL_ATENDENTE_RECIFE, EMAIL_COZINHA_RECIFE])
def test_atendente_e_cozinha_nao_consultam_historico(cliente_http, entrar, email):
    resposta = _historico(cliente_http, entrar(email), f"unidadeId={UNIDADE_RECIFE}")

    assert resposta.status_code == 403


@pytest.mark.parametrize(
    ("consulta", "detalhe"),
    [
        ("", {"field": "unidadeId", "issue": "Campo obrigatório"}),
        (
            f"unidadeId={UNIDADE_RECIFE}&produtoId=0",
            {"field": "produtoId", "issue": "Deve ser maior que 0"},
        ),
    ],
)
def test_historico_com_filtro_invalido_devolve_422(cliente_http, entrar, consulta, detalhe):
    resposta = _historico(cliente_http, entrar(EMAIL_GERENTE_RECIFE), consulta)

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [detalhe]


def test_historico_sem_token_devolve_401(cliente_http):
    assert cliente_http.get(URL).status_code == 401
