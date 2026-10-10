from src.infrastructure.database.seeds.dados_iniciais import DOMINIO_EMAIL

UNIDADE_RECIFE = 1
EMAIL_ADMIN = f"admin@{DOMINIO_EMAIL}"
EMAIL_GERENTE_RECIFE = f"gerente.recife@{DOMINIO_EMAIL}"


def _ids_no_cardapio(cliente_http) -> set[int]:
    resposta = cliente_http.get(f"/unidades/{UNIDADE_RECIFE}/cardapio?limit=100")
    assert resposta.status_code == 200, resposta.text
    return {item["produtoId"] for item in resposta.json()["dados"]}


def test_produto_novo_entra_no_estoque_e_sai_com_o_pedido(
    cliente_http, entrar, fazer_pedido, saldo_pela_api
):
    produto = cliente_http.post(
        "/produtos",
        json={"nome": "Arrumadinho", "descricao": "Feijão verde com charque", "preco": 22.0},
        headers=entrar(EMAIL_ADMIN),
    )
    assert produto.status_code == 201, produto.text
    produto_id = produto.json()["id"]
    assert produto_id not in _ids_no_cardapio(cliente_http)

    entrada = cliente_http.post(
        "/estoque/movimentacoes",
        json={
            "unidadeId": UNIDADE_RECIFE,
            "produtoId": produto_id,
            "tipo": "ENTRADA",
            "quantidade": 10,
            "motivo": "Primeira remessa",
        },
        headers=entrar(EMAIL_GERENTE_RECIFE),
    )
    assert (entrada.status_code, entrada.json()["saldoAtual"]) == (201, 10)
    assert saldo_pela_api(UNIDADE_RECIFE, produto_id) == 10
    assert produto_id in _ids_no_cardapio(cliente_http)

    criado = fazer_pedido(itens=[{"produtoId": produto_id, "quantidade": 3}])

    assert (criado["status"], criado["total"]) == ("AGUARDANDO_PAGAMENTO", 66.0)
    assert saldo_pela_api(UNIDADE_RECIFE, produto_id) == 7
