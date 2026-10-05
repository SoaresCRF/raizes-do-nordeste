import pytest
from sqlalchemy import func, select, update

from src.infrastructure.database.seeds.dados_iniciais import DOMINIO_EMAIL, SALDO_INICIAL_RECIFE
from src.infrastructure.database.tabelas import estoque, produto

URL = "/estoque"
UNIDADE_RECIFE = 1
UNIDADE_CARUARU = 2
UNIDADE_INEXISTENTE = 9999
CAFE_DA_MANHA_COMPLETO = 5
CAFE_PASSADO = 6
EMAIL_ADMIN = f"admin@{DOMINIO_EMAIL}"
EMAIL_GERENTE_RECIFE = f"gerente.recife@{DOMINIO_EMAIL}"
EMAIL_ATENDENTE_RECIFE = f"atendente.recife@{DOMINIO_EMAIL}"
EMAIL_COZINHA_RECIFE = f"cozinha.recife@{DOMINIO_EMAIL}"
EMAIL_CLIENTE = f"cliente@{DOMINIO_EMAIL}"


def _url(unidade_id: int) -> str:
    return f"{URL}?unidadeId={unidade_id}&limit=100"


def _produto_ids(resposta) -> list[int]:
    return [item["produtoId"] for item in resposta.json()["dados"]]


def test_gerente_consulta_saldo_da_propria_unidade(cliente_http, entrar, banco_semeado):
    with banco_semeado.connect() as conexao:
        total = conexao.execute(
            select(func.count()).select_from(estoque).where(estoque.c.unidade_id == UNIDADE_RECIFE)
        ).scalar_one()

    resposta = cliente_http.get(_url(UNIDADE_RECIFE), headers=entrar(EMAIL_GERENTE_RECIFE))
    corpo = resposta.json()

    assert resposta.status_code == 200
    assert corpo["paginacao"]["total"] == total
    assert corpo["dados"][0] == {
        "produtoId": 1,
        "nome": "Tapioca",
        "quantidade": SALDO_INICIAL_RECIFE,
    }
    assert _produto_ids(resposta) == sorted(_produto_ids(resposta))


def test_saldo_inclui_produto_inativo(cliente_http, entrar, banco_semeado):
    with banco_semeado.begin() as conexao:
        conexao.execute(update(produto).where(produto.c.id == CAFE_PASSADO).values(ativo=False))

    resposta = cliente_http.get(_url(UNIDADE_RECIFE), headers=entrar(EMAIL_GERENTE_RECIFE))

    assert CAFE_PASSADO in _produto_ids(resposta)


@pytest.mark.parametrize("email", [EMAIL_ATENDENTE_RECIFE, EMAIL_COZINHA_RECIFE])
def test_atendente_e_cozinha_consultam_a_propria_unidade(cliente_http, entrar, email):
    resposta = cliente_http.get(_url(UNIDADE_RECIFE), headers=entrar(email))

    assert resposta.status_code == 200


def test_admin_consulta_qualquer_unidade(cliente_http, entrar):
    resposta = cliente_http.get(_url(UNIDADE_CARUARU), headers=entrar(EMAIL_ADMIN))

    assert resposta.status_code == 200
    assert CAFE_DA_MANHA_COMPLETO not in _produto_ids(resposta)


def test_sem_unidade_id_devolve_422(cliente_http, entrar):
    resposta = cliente_http.get(URL, headers=entrar(EMAIL_GERENTE_RECIFE))

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [{"field": "unidadeId", "issue": "Campo obrigatório"}]


@pytest.mark.parametrize(
    ("valor", "problema"),
    [("0", "Deve ser maior que 0"), ("abc", "Deve ser um número inteiro")],
)
def test_unidade_id_invalido_devolve_422(cliente_http, entrar, valor, problema):
    resposta = cliente_http.get(f"{URL}?unidadeId={valor}", headers=entrar(EMAIL_ADMIN))

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [{"field": "unidadeId", "issue": problema}]


def test_gerente_nao_consulta_outra_unidade(cliente_http, entrar):
    resposta = cliente_http.get(_url(UNIDADE_CARUARU), headers=entrar(EMAIL_GERENTE_RECIFE))

    assert resposta.status_code == 403
    assert resposta.json()["error"] == "ACESSO_NEGADO"


def test_gerente_recebe_403_para_unidade_inexistente(cliente_http, entrar):
    resposta = cliente_http.get(_url(UNIDADE_INEXISTENTE), headers=entrar(EMAIL_GERENTE_RECIFE))

    assert resposta.status_code == 403


def test_admin_recebe_404_para_unidade_inexistente(cliente_http, entrar):
    resposta = cliente_http.get(_url(UNIDADE_INEXISTENTE), headers=entrar(EMAIL_ADMIN))

    assert resposta.status_code == 404
    assert resposta.json()["error"] == "RECURSO_NAO_ENCONTRADO"


def test_cliente_recebe_403_mesmo_sem_unidade_id(cliente_http, entrar):
    resposta = cliente_http.get(URL, headers=entrar(EMAIL_CLIENTE))

    assert resposta.status_code == 403


def test_consulta_sem_token_devolve_401(cliente_http):
    assert cliente_http.get(_url(UNIDADE_RECIFE)).status_code == 401
