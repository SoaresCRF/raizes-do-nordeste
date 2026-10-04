from datetime import UTC, datetime, timedelta

from sqlalchemy import insert, update

from src.infrastructure.database.seeds.dados_iniciais import DOMINIO_EMAIL
from src.infrastructure.database.tabelas import estoque, produto

UNIDADE_RECIFE = 1
UNIDADE_CARUARU = 2
UNIDADE_INEXISTENTE = 9999
BOLO = 3
CAFE_DA_MANHA_COMPLETO = 5
CANJICA = 7
EMAIL_ADMIN = f"admin@{DOMINIO_EMAIL}"
PRODUTOS_DO_SEED_NO_PERIODO = [1, 2, 3, 4, 5, 6]


def _url(unidade_id: int) -> str:
    return f"/unidades/{unidade_id}/cardapio"


def _ids(corpo: dict) -> list[int]:
    return [item["produtoId"] for item in corpo["dados"]]


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


def test_cardapio_traz_so_produtos_ativos_ofertados_e_no_periodo(cliente_http):
    resposta = cliente_http.get(f"{_url(UNIDADE_RECIFE)}?limit=100")
    corpo = resposta.json()

    assert resposta.status_code == 200
    assert _ids(corpo)[:6] == PRODUTOS_DO_SEED_NO_PERIODO
    assert CANJICA not in _ids(corpo)
    assert corpo["dados"][0] == {
        "produtoId": 1,
        "nome": "Tapioca",
        "descricao": "Tapioca de queijo coalho",
        "preco": 18.9,
        "disponivel": True,
    }


def test_cardapio_de_caruaru_nao_traz_produto_nao_ofertado(cliente_http):
    corpo = cliente_http.get(f"{_url(UNIDADE_CARUARU)}?limit=100").json()

    assert CAFE_DA_MANHA_COMPLETO not in _ids(corpo)


def test_produto_sem_saldo_aparece_indisponivel(cliente_http, banco_semeado):
    with banco_semeado.begin() as conexao:
        conexao.execute(
            update(estoque)
            .where(estoque.c.unidade_id == UNIDADE_CARUARU, estoque.c.produto_id == BOLO)
            .values(quantidade=0)
        )

    corpo = cliente_http.get(f"{_url(UNIDADE_CARUARU)}?limit=100").json()

    bolo = next(item for item in corpo["dados"] if item["produtoId"] == BOLO)
    assert bolo["disponivel"] is False


def test_produto_sazonal_no_periodo_aparece(cliente_http, entrar, banco_semeado):
    hoje = datetime.now(UTC).date()
    produto_id = _cadastrar_ofertado(
        cliente_http,
        entrar,
        banco_semeado,
        disponivelDe=(hoje - timedelta(days=1)).isoformat(),
        disponivelAte=(hoje + timedelta(days=1)).isoformat(),
    )

    corpo = cliente_http.get(f"{_url(UNIDADE_RECIFE)}?limit=100").json()

    assert produto_id in _ids(corpo)


def test_produto_sazonal_futuro_nao_aparece(cliente_http, entrar, banco_semeado):
    depois_de_amanha = datetime.now(UTC).date() + timedelta(days=2)
    produto_id = _cadastrar_ofertado(
        cliente_http, entrar, banco_semeado, disponivelDe=depois_de_amanha.isoformat()
    )

    corpo = cliente_http.get(f"{_url(UNIDADE_RECIFE)}?limit=100").json()

    assert produto_id not in _ids(corpo)


def test_produto_inativo_nao_aparece_no_cardapio(cliente_http, entrar, banco_semeado):
    produto_id = _cadastrar_ofertado(cliente_http, entrar, banco_semeado)
    with banco_semeado.begin() as conexao:
        conexao.execute(update(produto).where(produto.c.id == produto_id).values(ativo=False))

    corpo = cliente_http.get(f"{_url(UNIDADE_RECIFE)}?limit=100").json()

    assert produto_id not in _ids(corpo)


def test_cardapio_paginado(cliente_http):
    corpo = cliente_http.get(f"{_url(UNIDADE_RECIFE)}?page=2&limit=2").json()

    assert _ids(corpo) == [3, 4]
    assert corpo["paginacao"]["page"] == 2


def test_cardapio_de_unidade_inexistente_devolve_404(cliente_http):
    resposta = cliente_http.get(_url(UNIDADE_INEXISTENTE))

    assert resposta.status_code == 404
    assert resposta.json()["message"] == f"Unidade {UNIDADE_INEXISTENTE} não encontrada"


def test_cardapio_com_id_zero_devolve_422(cliente_http):
    resposta = cliente_http.get(_url(0))

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [{"field": "id", "issue": "Deve ser maior que 0"}]
