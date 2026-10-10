import json
import re
from pathlib import Path

import pytest

PASTA_POSTMAN = Path("postman")
COLECAO = PASTA_POSTMAN / "raizes-do-nordeste.postman_collection.json"
AMBIENTE = PASTA_POSTMAN / "raizes-do-nordeste.postman_environment.json"
ESQUEMA_V21 = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
TOTAL_DE_CENARIOS = 95
PASTAS = [
    "Auth",
    "Usuarios",
    "Unidades",
    "Produtos",
    "Estoque",
    "Pedidos",
    "Pagamento",
    "Fidelidade",
    "Auditoria",
    "Erros",
]
# Cenários negativos da tabela da seção 11 do PROJETO.md (coluna Tipo = −).
# fmt: off
NEGATIVOS = {
    2, 3, 5, 7, 9, 10, 11, 13, 15, 17, 19, 21, 23, 25, 26, 28, 30, 32, 34, 36,
    37, 39, 41, 43, 45, 46, 47, 49, 51, 52, 53, 54, 55, 56, 57, 59, 61, 62, 64, 65,
    67, 69, 70, 71, 72, 74, 76, 78, 80, 81, 83, 86, 88, 89, 91, 93,
}
# fmt: on
NOME_DA_REQUISICAO = re.compile(r"^(?:T(?P<id>\d{2})|Prep) – \S")
VARIAVEIS_DA_SECAO_11 = {
    "baseUrl",
    "tokenCliente",
    "tokenAtendente",
    "tokenCozinha",
    "tokenGerente",
    "tokenAdmin",
    "pedidoId",
}
VARIAVEIS_COM_VALOR = {"baseUrl", "senhaSeed"}
REFERENCIA_A_VARIAVEL = re.compile(r"\{\{(\w+)\}\}")


def _carregar(caminho: Path) -> dict:
    return json.loads(caminho.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def colecao() -> dict:
    return _carregar(COLECAO)


@pytest.fixture(scope="module")
def ambiente() -> dict:
    return _carregar(AMBIENTE)


def _pastas(colecao: dict) -> list[dict]:
    return [item for item in colecao["item"] if "item" in item]


def _requisicoes(colecao: dict) -> list[tuple[str | None, dict]]:
    soltas = [(None, item) for item in colecao["item"] if "request" in item]
    return soltas + [(pasta["name"], item) for pasta in _pastas(colecao) for item in pasta["item"]]


def _id_do_cenario(requisicao: dict) -> int | None:
    encontrado = NOME_DA_REQUISICAO.match(requisicao["name"])
    assert encontrado, f"Nome fora do padrão: {requisicao['name']!r}"
    return int(encontrado["id"]) if encontrado["id"] else None


def _script(requisicao: dict, evento: str) -> str:
    return "\n".join(
        linha
        for registro in requisicao.get("event", [])
        if registro["listen"] == evento
        for linha in registro["script"]["exec"]
    )


def test_colecao_usa_o_formato_postman_v21(colecao):
    assert colecao["info"]["schema"] == ESQUEMA_V21


def test_pastas_seguem_a_ordem_da_secao_11(colecao):
    assert [pasta["name"] for pasta in _pastas(colecao)] == PASTAS


def test_toda_requisicao_segue_o_padrao_de_nome(colecao):
    for _, requisicao in _requisicoes(colecao):
        _id_do_cenario(requisicao)


def test_cada_cenario_aparece_uma_vez(colecao):
    ids = [_id_do_cenario(requisicao) for _, requisicao in _requisicoes(colecao)]
    cenarios = [cenario for cenario in ids if cenario is not None]
    assert len(cenarios) == len(set(cenarios))


def test_negativos_ficam_na_pasta_erros(colecao):
    for pasta, requisicao in _requisicoes(colecao):
        cenario = _id_do_cenario(requisicao)
        if cenario is None:
            continue
        assert (pasta == "Erros") == (cenario in NEGATIVOS), requisicao["name"]


def test_toda_requisicao_tem_script_de_teste(colecao):
    for _, requisicao in _requisicoes(colecao):
        assert "pm.test(" in _script(requisicao, "test"), requisicao["name"]


def test_toda_url_parte_da_base(colecao):
    for _, requisicao in _requisicoes(colecao):
        assert requisicao["request"]["url"].startswith("{{baseUrl}}/"), requisicao["name"]


def test_ambiente_tem_as_variaveis_da_secao_11(ambiente):
    assert VARIAVEIS_DA_SECAO_11 <= {variavel["key"] for variavel in ambiente["values"]}


def test_ambiente_versionado_nao_guarda_tokens(ambiente):
    preenchidas = {variavel["key"] for variavel in ambiente["values"] if variavel["value"]}
    assert preenchidas == VARIAVEIS_COM_VALOR


def test_toda_variavel_usada_existe_no_ambiente(ambiente):
    declaradas = {variavel["key"] for variavel in ambiente["values"]}
    texto = COLECAO.read_text(encoding="utf-8")
    assert set(REFERENCIA_A_VARIAVEL.findall(texto)) <= declaradas


def test_colecao_tem_os_95_cenarios_da_secao_11(colecao):
    ids = {_id_do_cenario(requisicao) for _, requisicao in _requisicoes(colecao)} - {None}
    assert ids == set(range(1, TOTAL_DE_CENARIOS + 1))
