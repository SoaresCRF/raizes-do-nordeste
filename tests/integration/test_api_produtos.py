from math import ceil

import pytest
from sqlalchemy import func, insert, select

from src.infrastructure.database.seeds.dados_iniciais import DOMINIO_EMAIL
from src.infrastructure.database.tabelas import estoque, log_auditoria, produto, usuario

URL = "/produtos"
TAPIOCA = 1
CANJICA = 7
PRODUTO_INEXISTENTE = 9999
UNIDADE_RECIFE = 1
DADOS_TAPIOCA = {
    "id": TAPIOCA,
    "nome": "Tapioca",
    "descricao": "Tapioca de queijo coalho",
    "preco": 18.9,
    "ativo": True,
    "disponivelDe": None,
    "disponivelAte": None,
}
EMAIL_ADMIN = f"admin@{DOMINIO_EMAIL}"
EMAIL_COZINHA = f"cozinha.recife@{DOMINIO_EMAIL}"


def _detalhes(resposta) -> list[dict]:
    return resposta.json()["details"]


def test_lista_produtos_paginados(cliente_http, banco_semeado):
    with banco_semeado.connect() as conexao:
        total = conexao.execute(select(func.count()).select_from(produto)).scalar_one()

    resposta = cliente_http.get(f"{URL}?page=1&limit=10")
    corpo = resposta.json()

    assert resposta.status_code == 200
    assert corpo["paginacao"] == {
        "page": 1,
        "limit": 10,
        "total": total,
        "totalPaginas": ceil(total / 10),
    }
    assert corpo["dados"][0] == DADOS_TAPIOCA


def test_filtra_por_nome_sem_diferenciar_maiusculas(cliente_http):
    corpo = cliente_http.get(f"{URL}?nome=CAFÉ").json()

    assert [item["nome"] for item in corpo["dados"]] == ["Café da manhã completo", "Café passado"]


def test_filtro_nome_trata_curinga_como_texto(cliente_http):
    corpo = cliente_http.get(f"{URL}?nome=%25").json()

    assert corpo["paginacao"]["total"] == 0


def test_page_negativa_devolve_422(cliente_http):
    resposta = cliente_http.get(f"{URL}?page=-1")

    assert resposta.status_code == 422
    assert _detalhes(resposta) == [{"field": "page", "issue": "Deve ser maior ou igual a 1"}]


def test_nome_maior_que_a_coluna_devolve_422(cliente_http):
    resposta = cliente_http.get(f"{URL}?nome={'x' * 121}")

    assert resposta.status_code == 422
    assert _detalhes(resposta) == [{"field": "nome", "issue": "Deve ter no máximo 120 caracteres"}]


def test_consulta_produto_por_id(cliente_http):
    resposta = cliente_http.get(f"{URL}/{TAPIOCA}")

    assert resposta.status_code == 200
    assert resposta.json() == DADOS_TAPIOCA


def test_produto_sazonal_traz_o_periodo(cliente_http):
    corpo = cliente_http.get(f"{URL}/{CANJICA}").json()

    assert corpo["disponivelDe"] == "2026-06-01"
    assert corpo["disponivelAte"] == "2026-07-31"


def test_produto_inexistente_devolve_404(cliente_http):
    resposta = cliente_http.get(f"{URL}/{PRODUTO_INEXISTENTE}")

    assert resposta.status_code == 404
    assert resposta.json()["message"] == f"Produto {PRODUTO_INEXISTENTE} não encontrado"


def test_id_zero_devolve_422(cliente_http):
    resposta = cliente_http.get(f"{URL}/0")

    assert resposta.status_code == 422
    assert _detalhes(resposta) == [{"field": "id", "issue": "Deve ser maior que 0"}]


def _novo_produto(**alteracoes) -> dict:
    return {
        "nome": "Baião de dois",
        "descricao": "Arroz, feijão verde e queijo coalho",
        "preco": 32.5,
    } | alteracoes


def test_admin_cadastra_produto(cliente_http, entrar):
    resposta = cliente_http.post(URL, json=_novo_produto(), headers=entrar(EMAIL_ADMIN))
    corpo = resposta.json()

    assert resposta.status_code == 201
    assert corpo == {
        "id": corpo["id"],
        **_novo_produto(),
        "ativo": True,
        "disponivelDe": None,
        "disponivelAte": None,
    }
    assert cliente_http.get(f"{URL}/{corpo['id']}").json() == corpo


def test_cadastra_produto_sazonal_sem_descricao(cliente_http, entrar):
    dados = _novo_produto(disponivelDe="2026-06-01", disponivelAte="2026-07-31")
    del dados["descricao"]

    corpo = cliente_http.post(URL, json=dados, headers=entrar(EMAIL_ADMIN)).json()

    assert corpo["descricao"] is None
    assert (corpo["disponivelDe"], corpo["disponivelAte"]) == ("2026-06-01", "2026-07-31")


def test_cozinha_recebe_403(cliente_http, entrar):
    resposta = cliente_http.post(URL, json=_novo_produto(), headers=entrar(EMAIL_COZINHA))

    assert resposta.status_code == 403
    assert resposta.json()["error"] == "ACESSO_NEGADO"


def test_cozinha_recebe_403_mesmo_com_body_invalido(cliente_http, entrar):
    resposta = cliente_http.post(URL, json={}, headers=entrar(EMAIL_COZINHA))

    assert resposta.status_code == 403


def test_cadastro_sem_token_devolve_401(cliente_http):
    assert cliente_http.post(URL, json=_novo_produto()).status_code == 401


@pytest.mark.parametrize(
    ("campo", "valor", "problema"),
    [
        ("preco", -1, "Deve ser maior que 0"),
        ("preco", 0, "Deve ser maior que 0"),
        ("preco", 18.999, "Deve ter no máximo 2 casas decimais"),
        ("preco", 123456789.99, "Deve ter no máximo 10 dígitos"),
        ("preco", "NaN", "Deve ser um número finito"),
        ("nome", "x" * 121, "Deve ter no máximo 120 caracteres"),
        ("disponivelDe", "2026-13-01", "Deve ser uma data no formato AAAA-MM-DD"),
        ("disponivelDe", "2026-01-01T03:00:00", "Deve ser uma data no formato AAAA-MM-DD"),
        ("ativo", False, "Campo não permitido"),
    ],
)
def test_rejeita_campo_invalido(cliente_http, entrar, campo, valor, problema):
    resposta = cliente_http.post(
        URL, json=_novo_produto(**{campo: valor}), headers=entrar(EMAIL_ADMIN)
    )

    assert resposta.status_code == 422
    assert _detalhes(resposta) == [{"field": campo, "issue": problema}]


def test_produto_sem_preco_devolve_422(cliente_http, entrar):
    dados = _novo_produto()
    del dados["preco"]

    resposta = cliente_http.post(URL, json=dados, headers=entrar(EMAIL_ADMIN))

    assert _detalhes(resposta) == [{"field": "preco", "issue": "Campo obrigatório"}]


def test_periodo_invertido_devolve_422(cliente_http, entrar):
    resposta = cliente_http.post(
        URL,
        json=_novo_produto(disponivelDe="2026-07-31", disponivelAte="2026-06-01"),
        headers=entrar(EMAIL_ADMIN),
    )

    assert resposta.status_code == 422
    assert _detalhes(resposta) == [
        {"field": "disponivelAte", "issue": "Deve ser igual ou posterior a disponivelDe"}
    ]


def _cadastrar(cliente_http, entrar, **alteracoes) -> int:
    resposta = cliente_http.post(URL, json=_novo_produto(**alteracoes), headers=entrar(EMAIL_ADMIN))
    assert resposta.status_code == 201, resposta.text
    return resposta.json()["id"]


def _auditorias(banco_semeado, produto_id: int) -> list:
    with banco_semeado.connect() as conexao:
        return conexao.execute(
            select(log_auditoria)
            .where(
                log_auditoria.c.entidade == "Produto",
                log_auditoria.c.entidade_id == produto_id,
            )
            .order_by(log_auditoria.c.id)
        ).all()


def test_admin_atualiza_produto(cliente_http, entrar):
    produto_id = _cadastrar(cliente_http, entrar)
    alteracao = _novo_produto(nome="Baião de dois completo", preco=35.0) | {"ativo": True}

    resposta = cliente_http.put(f"{URL}/{produto_id}", json=alteracao, headers=entrar(EMAIL_ADMIN))

    assert resposta.status_code == 200
    assert resposta.json() == {
        "id": produto_id,
        **alteracao,
        "disponivelDe": None,
        "disponivelAte": None,
    }
    assert cliente_http.get(f"{URL}/{produto_id}").json()["preco"] == 35.0


def test_alteracao_de_preco_e_auditada(cliente_http, entrar, banco_semeado):
    produto_id = _cadastrar(cliente_http, entrar, preco=21.5)

    cliente_http.put(
        f"{URL}/{produto_id}",
        json=_novo_produto(preco=22.0, ativo=True),
        headers=entrar(EMAIL_ADMIN),
    )

    [registro] = _auditorias(banco_semeado, produto_id)
    with banco_semeado.connect() as conexao:
        admin_id = conexao.execute(
            select(usuario.c.id).where(usuario.c.email == EMAIL_ADMIN)
        ).scalar_one()
    assert registro.acao == "PRODUTO_ALTERADO"
    assert registro.usuario_id == admin_id
    assert registro.unidade_id is None
    assert registro.dados_antes["preco"] == "21.50"
    assert registro.dados_depois == {
        "nome": "Baião de dois",
        "descricao": "Arroz, feijão verde e queijo coalho",
        "preco": "22.00",
        "ativo": True,
        "disponivelDe": None,
        "disponivelAte": None,
    }
    assert registro.request_id is not None


def test_atualizar_produto_inexistente_devolve_404(cliente_http, entrar):
    resposta = cliente_http.put(
        f"{URL}/{PRODUTO_INEXISTENTE}",
        json=_novo_produto(ativo=True),
        headers=entrar(EMAIL_ADMIN),
    )

    assert resposta.status_code == 404
    assert resposta.json()["message"] == f"Produto {PRODUTO_INEXISTENTE} não encontrado"


def test_cozinha_nao_atualiza_produto(cliente_http, entrar):
    resposta = cliente_http.put(f"{URL}/{TAPIOCA}", json={}, headers=entrar(EMAIL_COZINHA))

    assert resposta.status_code == 403


def test_atualizacao_sem_token_devolve_401(cliente_http):
    resposta = cliente_http.put(f"{URL}/{TAPIOCA}", json=_novo_produto(ativo=True))

    assert resposta.status_code == 401


def test_atualizacao_sem_ativo_devolve_422(cliente_http, entrar):
    resposta = cliente_http.put(
        f"{URL}/{TAPIOCA}", json=_novo_produto(), headers=entrar(EMAIL_ADMIN)
    )

    assert resposta.status_code == 422
    assert _detalhes(resposta) == [{"field": "ativo", "issue": "Campo obrigatório"}]


def test_atualizacao_com_periodo_invertido_devolve_422(cliente_http, entrar, banco_semeado):
    produto_id = _cadastrar(cliente_http, entrar)

    resposta = cliente_http.put(
        f"{URL}/{produto_id}",
        json=_novo_produto(disponivelDe="2026-07-31", disponivelAte="2026-06-01", ativo=True),
        headers=entrar(EMAIL_ADMIN),
    )

    assert resposta.status_code == 422
    assert _auditorias(banco_semeado, produto_id) == []


def test_admin_desativa_produto(cliente_http, entrar, banco_semeado):
    produto_id = _cadastrar(cliente_http, entrar)

    resposta = cliente_http.delete(f"{URL}/{produto_id}", headers=entrar(EMAIL_ADMIN))

    assert resposta.status_code == 204
    assert cliente_http.get(f"{URL}/{produto_id}").json()["ativo"] is False
    [registro] = _auditorias(banco_semeado, produto_id)
    assert registro.acao == "PRODUTO_DESATIVADO"
    assert (registro.dados_antes["ativo"], registro.dados_depois["ativo"]) == (True, False)


def test_desativar_de_novo_nao_gera_outra_auditoria(cliente_http, entrar, banco_semeado):
    produto_id = _cadastrar(cliente_http, entrar)
    cliente_http.delete(f"{URL}/{produto_id}", headers=entrar(EMAIL_ADMIN))

    resposta = cliente_http.delete(f"{URL}/{produto_id}", headers=entrar(EMAIL_ADMIN))

    assert resposta.status_code == 204
    assert len(_auditorias(banco_semeado, produto_id)) == 1


def test_produto_desativado_some_do_cardapio(cliente_http, entrar, banco_semeado):
    produto_id = _cadastrar(cliente_http, entrar)
    with banco_semeado.begin() as conexao:
        conexao.execute(
            insert(estoque).values(unidade_id=UNIDADE_RECIFE, produto_id=produto_id, quantidade=5)
        )
    cardapio = f"/unidades/{UNIDADE_RECIFE}/cardapio?limit=100"
    assert produto_id in [i["produtoId"] for i in cliente_http.get(cardapio).json()["dados"]]

    cliente_http.delete(f"{URL}/{produto_id}", headers=entrar(EMAIL_ADMIN))

    assert produto_id not in [i["produtoId"] for i in cliente_http.get(cardapio).json()["dados"]]


def test_desativar_produto_inexistente_devolve_404(cliente_http, entrar):
    resposta = cliente_http.delete(f"{URL}/{PRODUTO_INEXISTENTE}", headers=entrar(EMAIL_ADMIN))

    assert resposta.status_code == 404


def test_cozinha_nao_desativa_produto(cliente_http, entrar):
    resposta = cliente_http.delete(f"{URL}/{TAPIOCA}", headers=entrar(EMAIL_COZINHA))

    assert resposta.status_code == 403


def test_desativacao_sem_token_devolve_401(cliente_http):
    assert cliente_http.delete(f"{URL}/{TAPIOCA}").status_code == 401
