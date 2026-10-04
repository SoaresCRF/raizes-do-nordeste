import uuid
from math import ceil

import pytest
from sqlalchemy import func, select

from src.infrastructure.database.seeds.dados_iniciais import DOMINIO_EMAIL
from src.infrastructure.database.tabelas import log_auditoria, unidade, usuario

URL = "/unidades"
UNIDADE_RECIFE = 1
UNIDADE_CARUARU = 2
UNIDADE_INEXISTENTE = 9999
RECIFE = {
    "id": UNIDADE_RECIFE,
    "nome": "Raízes do Nordeste Recife",
    "cidade": "Recife",
    "uf": "PE",
    "regiao": "Nordeste",
    "tipo": "COZINHA_COMPLETA",
    "ativa": True,
}
EMAIL_ADMIN = f"admin@{DOMINIO_EMAIL}"
EMAIL_GERENTE = f"gerente.recife@{DOMINIO_EMAIL}"
PROBLEMA_UF_INVALIDA = "Deve ser a sigla de uma UF do Brasil"
PROBLEMA_TIPO_INVALIDO = "Deve ser um destes valores: 'COZINHA_COMPLETA' ou 'FORMATO_REDUZIDO'"


def _detalhes(resposta) -> list[dict]:
    return resposta.json()["details"]


def test_lista_unidades_paginadas(cliente_http, banco_semeado):
    with banco_semeado.connect() as conexao:
        total = conexao.execute(select(func.count()).select_from(unidade)).scalar_one()

    resposta = cliente_http.get(f"{URL}?page=1&limit=10")
    corpo = resposta.json()

    assert resposta.status_code == 200
    assert corpo["paginacao"] == {
        "page": 1,
        "limit": 10,
        "total": total,
        "totalPaginas": ceil(total / 10),
    }
    assert corpo["dados"][0] == RECIFE


def test_respeita_page_e_limit(cliente_http):
    corpo = cliente_http.get(f"{URL}?page=2&limit=1").json()

    assert [item["id"] for item in corpo["dados"]] == [UNIDADE_CARUARU]


def test_filtra_por_regiao_sem_diferenciar_maiusculas(cliente_http):
    corpo = cliente_http.get(f"{URL}?regiao=nordeste").json()

    assert {item["regiao"] for item in corpo["dados"]} == {"Nordeste"}
    assert corpo["paginacao"]["total"] >= 2


def test_regiao_sem_unidades_devolve_lista_vazia(cliente_http):
    corpo = cliente_http.get(f"{URL}?regiao=Norte").json()

    assert corpo == {
        "dados": [],
        "paginacao": {"page": 1, "limit": 10, "total": 0, "totalPaginas": 0},
    }


def test_limit_zero_devolve_422(cliente_http):
    resposta = cliente_http.get(f"{URL}?limit=0")

    assert resposta.status_code == 422
    assert _detalhes(resposta) == [{"field": "limit", "issue": "Deve ser maior ou igual a 1"}]


def test_pagina_enorme_devolve_422(cliente_http):
    resposta = cliente_http.get(f"{URL}?page=99999999999999999999")

    assert resposta.status_code == 422
    assert _detalhes(resposta) == [{"field": "page", "issue": "Deve ser menor ou igual a 1000000"}]


def test_regiao_maior_que_a_coluna_devolve_422(cliente_http):
    resposta = cliente_http.get(f"{URL}?regiao={'x' * 41}")

    assert resposta.status_code == 422
    assert _detalhes(resposta) == [{"field": "regiao", "issue": "Deve ter no máximo 40 caracteres"}]


def test_consulta_unidade_por_id(cliente_http):
    resposta = cliente_http.get(f"{URL}/{UNIDADE_RECIFE}")

    assert resposta.status_code == 200
    assert resposta.json() == RECIFE


def test_unidade_inexistente_devolve_404(cliente_http):
    resposta = cliente_http.get(f"{URL}/{UNIDADE_INEXISTENTE}")

    assert resposta.status_code == 404
    assert resposta.json()["error"] == "RECURSO_NAO_ENCONTRADO"
    assert resposta.json()["message"] == f"Unidade {UNIDADE_INEXISTENTE} não encontrada"


def test_id_zero_devolve_422(cliente_http):
    resposta = cliente_http.get(f"{URL}/0")

    assert resposta.status_code == 422
    assert _detalhes(resposta) == [{"field": "id", "issue": "Deve ser maior que 0"}]


def test_id_acima_do_maximo_devolve_422(cliente_http):
    resposta = cliente_http.get(f"{URL}/2147483648")

    assert resposta.status_code == 422
    assert _detalhes(resposta) == [{"field": "id", "issue": "Deve ser menor ou igual a 2147483647"}]


def test_id_nao_numerico_devolve_422(cliente_http):
    resposta = cliente_http.get(f"{URL}/abc")

    assert resposta.status_code == 422
    assert _detalhes(resposta) == [{"field": "id", "issue": "Deve ser um número inteiro"}]


def test_regiao_com_caractere_nulo_devolve_422(cliente_http):
    resposta = cliente_http.get(f"{URL}?regiao=%00")

    assert resposta.status_code == 422
    assert _detalhes(resposta) == [{"field": "regiao", "issue": "Não pode conter o caractere nulo"}]


def _nova_unidade(**alteracoes) -> dict:
    return {
        "nome": "Raízes do Nordeste Petrolina",
        "cidade": "Petrolina",
        "uf": "PE",
        "regiao": "Nordeste",
        "tipo": "FORMATO_REDUZIDO",
    } | alteracoes


def test_admin_cadastra_unidade(cliente_http, entrar):
    resposta = cliente_http.post(URL, json=_nova_unidade(), headers=entrar(EMAIL_ADMIN))
    corpo = resposta.json()

    assert resposta.status_code == 201
    assert corpo == {"id": corpo["id"], **_nova_unidade(), "ativa": True}
    assert cliente_http.get(f"{URL}/{corpo['id']}").json() == corpo


def test_cadastro_de_unidade_e_auditado(cliente_http, entrar, banco_semeado):
    corpo = cliente_http.post(URL, json=_nova_unidade(), headers=entrar(EMAIL_ADMIN)).json()

    with banco_semeado.connect() as conexao:
        registro = conexao.execute(
            select(log_auditoria).where(
                log_auditoria.c.entidade == "Unidade",
                log_auditoria.c.entidade_id == corpo["id"],
            )
        ).one()
        admin_id = conexao.execute(
            select(usuario.c.id).where(usuario.c.email == EMAIL_ADMIN)
        ).scalar_one()
    assert registro.acao == "UNIDADE_CRIADA"
    assert registro.usuario_id == admin_id
    assert registro.unidade_id == corpo["id"]
    assert registro.dados_antes is None
    assert registro.dados_depois == _nova_unidade()
    assert uuid.UUID(registro.request_id)


def test_normaliza_a_uf_para_maiusculas(cliente_http, entrar):
    resposta = cliente_http.post(URL, json=_nova_unidade(uf="pe"), headers=entrar(EMAIL_ADMIN))

    assert resposta.json()["uf"] == "PE"


def test_gerente_recebe_403(cliente_http, entrar):
    resposta = cliente_http.post(URL, json=_nova_unidade(), headers=entrar(EMAIL_GERENTE))

    assert resposta.status_code == 403
    assert resposta.json()["error"] == "ACESSO_NEGADO"


def test_gerente_recebe_403_mesmo_com_body_invalido(cliente_http, entrar):
    resposta = cliente_http.post(URL, json={}, headers=entrar(EMAIL_GERENTE))

    assert resposta.status_code == 403


def test_cadastro_sem_token_devolve_401(cliente_http):
    assert cliente_http.post(URL, json=_nova_unidade()).status_code == 401


def test_unidade_sem_nome_devolve_422(cliente_http, entrar):
    dados = _nova_unidade()
    del dados["nome"]

    resposta = cliente_http.post(URL, json=dados, headers=entrar(EMAIL_ADMIN))

    assert resposta.status_code == 422
    assert _detalhes(resposta) == [{"field": "nome", "issue": "Campo obrigatório"}]


@pytest.mark.parametrize(
    ("campo", "valor", "problema"),
    [
        ("uf", "P", PROBLEMA_UF_INVALIDA),
        ("uf", "P1", PROBLEMA_UF_INVALIDA),
        ("uf", "PEE", PROBLEMA_UF_INVALIDA),
        ("uf", "XX", PROBLEMA_UF_INVALIDA),
        ("tipo", "QUIOSQUE", PROBLEMA_TIPO_INVALIDO),
        ("nome", "   ", "Deve ter pelo menos 1 caractere(s)"),
        ("nome", "x" * 121, "Deve ter no máximo 120 caracteres"),
        ("cidade", "x" * 81, "Deve ter no máximo 80 caracteres"),
        ("regiao", "x" * 41, "Deve ter no máximo 40 caracteres"),
        ("ativa", False, "Campo não permitido"),
    ],
)
def test_rejeita_campo_invalido(cliente_http, entrar, campo, valor, problema):
    resposta = cliente_http.post(
        URL, json=_nova_unidade(**{campo: valor}), headers=entrar(EMAIL_ADMIN)
    )

    assert resposta.status_code == 422
    assert _detalhes(resposta) == [{"field": campo, "issue": problema}]


def _cadastrar(cliente_http, entrar) -> int:
    resposta = cliente_http.post(URL, json=_nova_unidade(), headers=entrar(EMAIL_ADMIN))
    assert resposta.status_code == 201, resposta.text
    return resposta.json()["id"]


def test_admin_atualiza_unidade(cliente_http, entrar):
    unidade_id = _cadastrar(cliente_http, entrar)
    alteracao = _nova_unidade(nome="Raízes do Nordeste Juazeiro", cidade="Juazeiro", uf="ba")

    resposta = cliente_http.put(
        f"{URL}/{unidade_id}", json=alteracao | {"ativa": True}, headers=entrar(EMAIL_ADMIN)
    )

    assert resposta.status_code == 200
    assert resposta.json() == {"id": unidade_id, **alteracao, "uf": "BA", "ativa": True}
    assert cliente_http.get(f"{URL}/{unidade_id}").json()["cidade"] == "Juazeiro"


def test_admin_desativa_unidade(cliente_http, entrar):
    unidade_id = _cadastrar(cliente_http, entrar)

    cliente_http.put(
        f"{URL}/{unidade_id}", json=_nova_unidade(ativa=False), headers=entrar(EMAIL_ADMIN)
    )

    assert cliente_http.get(f"{URL}/{unidade_id}").json()["ativa"] is False


def test_atualizar_unidade_inexistente_devolve_404(cliente_http, entrar):
    resposta = cliente_http.put(
        f"{URL}/{UNIDADE_INEXISTENTE}",
        json=_nova_unidade(ativa=True),
        headers=entrar(EMAIL_ADMIN),
    )

    assert resposta.status_code == 404
    assert resposta.json()["message"] == f"Unidade {UNIDADE_INEXISTENTE} não encontrada"


def test_gerente_nao_atualiza_unidade(cliente_http, entrar):
    resposta = cliente_http.put(f"{URL}/{UNIDADE_RECIFE}", json={}, headers=entrar(EMAIL_GERENTE))

    assert resposta.status_code == 403


def test_atualizacao_sem_token_devolve_401(cliente_http):
    resposta = cliente_http.put(f"{URL}/{UNIDADE_RECIFE}", json=_nova_unidade(ativa=True))

    assert resposta.status_code == 401


def test_atualizacao_sem_ativa_devolve_422(cliente_http, entrar):
    resposta = cliente_http.put(
        f"{URL}/{UNIDADE_RECIFE}", json=_nova_unidade(), headers=entrar(EMAIL_ADMIN)
    )

    assert resposta.status_code == 422
    assert _detalhes(resposta) == [{"field": "ativa", "issue": "Campo obrigatório"}]
