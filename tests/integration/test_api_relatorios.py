from datetime import date, timedelta

import pytest

from src.infrastructure.database.seeds.dados_iniciais import DOMINIO_EMAIL

URL = "/relatorios/vendas"
UNIDADE_RECIFE = 1
UNIDADE_CARUARU = 2
TAPIOCA = 1
CAFE_COMPLETO = 5
EMAIL_ADMIN = f"admin@{DOMINIO_EMAIL}"
EMAIL_GERENTE_RECIFE = f"gerente.recife@{DOMINIO_EMAIL}"
EMAIL_GERENTE_CARUARU = f"gerente.caruaru@{DOMINIO_EMAIL}"
EMAIL_ATENDENTE_RECIFE = f"atendente.recife@{DOMINIO_EMAIL}"
EMAIL_COZINHA_RECIFE = f"cozinha.recife@{DOMINIO_EMAIL}"
EMAIL_CLIENTE = f"cliente@{DOMINIO_EMAIL}"
LINHA_VAZIA = {"pedidos": 0, "quantidade": 0, "total": 0}


def _relatorio(cliente_http, headers: dict, consulta: str):
    resposta = cliente_http.get(f"{URL}?{consulta}", headers=headers)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _linha(relatorio: dict, grupo: str) -> dict:
    return next((linha for linha in relatorio["dados"] if linha["grupo"] == grupo), LINHA_VAZIA)


def _diferenca(antes: dict, depois: dict) -> dict:
    return {campo: depois[campo] - antes[campo] for campo in LINHA_VAZIA}


def _venda(fazer_pedido, pagar_pedido, entrar, **alteracoes) -> dict:
    criado = fazer_pedido(**alteracoes)
    pagar_pedido(criado["pedidoId"], entrar(EMAIL_CLIENTE))
    return criado


def test_admin_ve_vendas_por_canal(cliente_http, entrar, fazer_pedido, pagar_pedido):
    admin = entrar(EMAIL_ADMIN)
    antes = _relatorio(cliente_http, admin, "agrupamento=canal")

    _venda(fazer_pedido, pagar_pedido, entrar, canalPedido="TOTEM")
    depois = _relatorio(cliente_http, admin, "agrupamento=canal")

    linha = _linha(depois, "TOTEM")
    assert linha["grupoId"] is None
    assert _diferenca(_linha(antes, "TOTEM"), linha) == {
        "pedidos": 1,
        "quantidade": 1,
        "total": pytest.approx(18.9),
    }


def test_pedido_com_varios_itens_conta_uma_vez(cliente_http, entrar, fazer_pedido, pagar_pedido):
    admin = entrar(EMAIL_ADMIN)
    antes = _relatorio(cliente_http, admin, "agrupamento=canal")

    _venda(
        fazer_pedido,
        pagar_pedido,
        entrar,
        canalPedido="WEB",
        itens=[
            {"produtoId": TAPIOCA, "quantidade": 2},
            {"produtoId": CAFE_COMPLETO, "quantidade": 1},
        ],
    )
    depois = _relatorio(cliente_http, admin, "agrupamento=canal")

    assert _diferenca(_linha(antes, "WEB"), _linha(depois, "WEB")) == {
        "pedidos": 1,
        "quantidade": 3,
        "total": pytest.approx(87.7),
    }


def test_agrupa_por_produto_com_o_valor_dos_itens(cliente_http, entrar, fazer_pedido, pagar_pedido):
    admin = entrar(EMAIL_ADMIN)
    antes = _relatorio(cliente_http, admin, "agrupamento=produto")

    _venda(fazer_pedido, pagar_pedido, entrar, itens=[{"produtoId": TAPIOCA, "quantidade": 2}])
    depois = _relatorio(cliente_http, admin, "agrupamento=produto")

    linha = _linha(depois, "Tapioca")
    assert linha["grupoId"] == TAPIOCA
    assert _diferenca(_linha(antes, "Tapioca"), linha) == {
        "pedidos": 1,
        "quantidade": 2,
        "total": pytest.approx(37.8),
    }


@pytest.mark.parametrize(
    ("agrupamento", "grupo", "grupo_id"),
    [
        ("unidade", "Raízes do Nordeste Recife", UNIDADE_RECIFE),
        ("regiao", "Nordeste", None),
    ],
)
def test_agrupa_por_unidade_e_por_regiao(
    cliente_http, entrar, fazer_pedido, pagar_pedido, agrupamento, grupo, grupo_id
):
    admin = entrar(EMAIL_ADMIN)
    antes = _relatorio(cliente_http, admin, f"agrupamento={agrupamento}")

    _venda(fazer_pedido, pagar_pedido, entrar)
    depois = _relatorio(cliente_http, admin, f"agrupamento={agrupamento}")

    assert _linha(depois, grupo)["grupoId"] == grupo_id
    assert _diferenca(_linha(antes, grupo), _linha(depois, grupo))["pedidos"] == 1


def test_pedido_nao_pago_e_pedido_cancelado_nao_contam(
    cliente_http, entrar, fazer_pedido, pagar_pedido
):
    admin = entrar(EMAIL_ADMIN)
    antes = _relatorio(cliente_http, admin, "agrupamento=canal")

    fazer_pedido(canalPedido="PICKUP")
    cancelado = _venda(fazer_pedido, pagar_pedido, entrar, canalPedido="PICKUP")
    resposta = cliente_http.post(
        f"/pedidos/{cancelado['pedidoId']}/cancelamento",
        json={"motivo": "Cliente desistiu"},
        headers=entrar(EMAIL_GERENTE_RECIFE),
    )
    assert resposta.status_code == 200, resposta.text
    depois = _relatorio(cliente_http, admin, "agrupamento=canal")

    assert _linha(depois, "PICKUP") == _linha(antes, "PICKUP")


def test_gerente_ve_so_a_propria_unidade(cliente_http, entrar, fazer_pedido, pagar_pedido):
    _venda(fazer_pedido, pagar_pedido, entrar)

    de_caruaru = _relatorio(cliente_http, entrar(EMAIL_GERENTE_CARUARU), "agrupamento=unidade")
    de_recife = _relatorio(cliente_http, entrar(EMAIL_GERENTE_RECIFE), "agrupamento=unidade")

    assert {linha["grupoId"] for linha in de_caruaru["dados"]} <= {UNIDADE_CARUARU}
    assert [linha["grupoId"] for linha in de_recife["dados"]] == [UNIDADE_RECIFE]


def test_periodo_filtra_pelo_dia_do_pedido(cliente_http, entrar, fazer_pedido, pagar_pedido):
    admin = entrar(EMAIL_ADMIN)
    dia = date.fromisoformat(_venda(fazer_pedido, pagar_pedido, entrar)["createdAt"][:10])
    seguinte = dia + timedelta(days=1)

    no_dia = _relatorio(cliente_http, admin, f"agrupamento=unidade&de={dia}&ate={dia}")
    depois = _relatorio(cliente_http, admin, f"agrupamento=unidade&de={seguinte}")

    assert _linha(no_dia, "Raízes do Nordeste Recife")["pedidos"] >= 1
    assert depois == {
        "agrupamento": "unidade",
        "de": seguinte.isoformat(),
        "ate": None,
        "dados": [],
    }


def test_periodo_extremo_nao_quebra(cliente_http, entrar):
    relatorio = _relatorio(
        cliente_http, entrar(EMAIL_ADMIN), "agrupamento=canal&de=0001-01-01&ate=9999-12-31"
    )

    assert relatorio["de"] == "0001-01-01"
    assert relatorio["ate"] == "9999-12-31"


def test_ate_antes_de_de_devolve_422(cliente_http, entrar):
    resposta = cliente_http.get(
        f"{URL}?agrupamento=canal&de=2026-10-05&ate=2026-10-01", headers=entrar(EMAIL_ADMIN)
    )

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [
        {"field": "ate", "issue": "Deve ser igual ou posterior a de"}
    ]


@pytest.mark.parametrize(
    ("consulta", "detalhe"),
    [
        ("", {"field": "agrupamento", "issue": "Campo obrigatório"}),
        (
            "agrupamento=mes",
            {
                "field": "agrupamento",
                "issue": "Deve ser um destes valores: 'unidade', 'regiao', 'canal' ou 'produto'",
            },
        ),
        (
            "agrupamento=canal&de=2026-13-01",
            {"field": "de", "issue": "Deve ser uma data no formato AAAA-MM-DD"},
        ),
    ],
)
def test_parametro_invalido_devolve_422(cliente_http, entrar, consulta, detalhe):
    resposta = cliente_http.get(f"{URL}?{consulta}", headers=entrar(EMAIL_ADMIN))

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [detalhe]


@pytest.mark.parametrize("email", [EMAIL_CLIENTE, EMAIL_ATENDENTE_RECIFE, EMAIL_COZINHA_RECIFE])
def test_perfil_sem_permissao_nao_ve_relatorio(cliente_http, entrar, email):
    resposta = cliente_http.get(f"{URL}?agrupamento=canal", headers=entrar(email))

    assert resposta.status_code == 403
    assert resposta.json()["error"] == "ACESSO_NEGADO"


def test_cliente_recebe_403_mesmo_com_parametro_invalido(cliente_http, entrar):
    resposta = cliente_http.get(f"{URL}?agrupamento=mes", headers=entrar(EMAIL_CLIENTE))

    assert resposta.status_code == 403


def test_relatorio_sem_token_devolve_401(cliente_http):
    assert cliente_http.get(f"{URL}?agrupamento=canal").status_code == 401
