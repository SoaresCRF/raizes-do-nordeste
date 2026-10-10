import json
import re
from http import HTTPStatus

import pytest
from fastapi.routing import APIRoute

from src.api.autenticacao import DESCRICAO_BEARER
from src.api.erros import JSON_INVALIDO, STATUS_POR_ERRO, RespostaErro
from src.api.openapi.exportar import CONTRATO_VERSIONADO
from src.main import ROTEADORES

CAMPOS_SENSIVEIS = {"senha", "senhaHash", "refreshTokenHash"}
CAMPOS_DO_CADASTRO = {"nome", "email", "senha", "consentimentoFidelidade"}
# E09, E13, E14, E19, E21, E23, E30, E32 (item 8.4 do PROJETO.md).
LISTAGENS = [
    "/unidades",
    "/unidades/{id}/cardapio",
    "/produtos",
    "/estoque",
    "/estoque/movimentacoes",
    "/pedidos",
    "/fidelidade/historico",
    "/auditoria",
]
CAMPOS_DO_ERRO_PADRAO = {"error", "message", "details", "timestamp", "path", "requestId"}
STATUS_DO_CODIGO = {erro.codigo: status for erro, status in STATUS_POR_ERRO.items()} | {
    JSON_INVALIDO: HTTPStatus.BAD_REQUEST
}
# E01, E02, E04, E09, E10, E13, E14 e E15: as rotas públicas da seção 8.
OPERACOES_PUBLICAS = {
    ("post", "/auth/login"),
    ("post", "/auth/refresh"),
    ("post", "/usuarios"),
    ("get", "/unidades"),
    ("get", "/unidades/{id}"),
    ("get", "/unidades/{id}/cardapio"),
    ("get", "/produtos"),
    ("get", "/produtos/{id}"),
}
# Status que cada operação devolve de fato (código em src/ e tests/integration/). O 400
# aparece só nas rotas com body, que é onde o JSON malformado pode chegar.
STATUS_POR_OPERACAO = {
    ("post", "/auth/login"): {200, 400, 401, 422},
    ("post", "/auth/refresh"): {200, 400, 401, 422},
    ("post", "/auth/logout"): {204, 401},
    ("post", "/usuarios"): {201, 400, 409, 422},
    ("get", "/usuarios/me"): {200, 401},
    ("delete", "/usuarios/me"): {204, 401, 403},
    ("post", "/usuarios/me/consentimentos"): {201, 400, 401, 403, 422},
    ("post", "/usuarios/funcionarios"): {201, 400, 401, 403, 404, 409, 422},
    ("get", "/unidades"): {200, 422},
    ("get", "/unidades/{id}"): {200, 404, 422},
    ("post", "/unidades"): {201, 400, 401, 403, 422},
    ("put", "/unidades/{id}"): {200, 400, 401, 403, 404, 422},
    ("get", "/unidades/{id}/cardapio"): {200, 404, 422},
    ("get", "/produtos"): {200, 422},
    ("get", "/produtos/{id}"): {200, 404, 422},
    ("post", "/produtos"): {201, 400, 401, 403, 422},
    ("put", "/produtos/{id}"): {200, 400, 401, 403, 404, 422},
    ("delete", "/produtos/{id}"): {204, 401, 403, 404, 422},
    ("get", "/estoque"): {200, 401, 403, 404, 422},
    ("post", "/estoque/movimentacoes"): {201, 400, 401, 403, 404, 409, 422},
    ("get", "/estoque/movimentacoes"): {200, 401, 403, 422},
    ("post", "/pedidos"): {201, 400, 401, 403, 404, 409, 422},
    ("get", "/pedidos"): {200, 401, 403, 422},
    ("get", "/pedidos/{id}"): {200, 401, 403, 404, 422},
    ("patch", "/pedidos/{id}/status"): {200, 400, 401, 403, 404, 409, 422},
    ("post", "/pedidos/{id}/cancelamento"): {200, 400, 401, 403, 404, 409, 422, 503},
    ("post", "/pagamentos"): {201, 400, 401, 403, 404, 409, 422, 503},
    ("get", "/pagamentos/{id}"): {200, 401, 403, 404, 422},
    ("get", "/fidelidade/saldo"): {200, 401, 403},
    ("get", "/fidelidade/historico"): {200, 401, 403, 422},
    ("post", "/fidelidade/resgates"): {201, 400, 401, 403, 404, 409, 422},
    ("get", "/auditoria"): {200, 401, 403, 422},
    ("get", "/relatorios/vendas"): {200, 401, 403, 422},
}
OPERACOES = sorted(STATUS_POR_OPERACAO)
OPERACOES_COM_BODY = [op for op in OPERACOES if HTTPStatus.BAD_REQUEST in STATUS_POR_OPERACAO[op]]
OPERACOES_COM_CORPO_NA_RESPOSTA = [
    op for op in OPERACOES if HTTPStatus.NO_CONTENT not in STATUS_POR_OPERACAO[op]
]


@pytest.fixture
def contrato(app) -> dict:
    return app.openapi()


def _nome_do_esquema(referencia: str) -> str:
    return referencia.rsplit("/", 1)[-1]


def _esquemas_de_resposta(contrato: dict) -> set[str]:
    componentes = contrato["components"]["schemas"]
    pendentes = [
        operacao.get("responses", {})
        for caminho in contrato["paths"].values()
        for operacao in caminho.values()
    ]
    vistos: set[str] = set()
    while pendentes:
        no = pendentes.pop()
        if isinstance(no, list):
            pendentes.extend(no)
            continue
        if not isinstance(no, dict):
            continue
        referencia = no.get("$ref")
        if referencia and _nome_do_esquema(referencia) not in vistos:
            vistos.add(_nome_do_esquema(referencia))
            pendentes.append(componentes[_nome_do_esquema(referencia)])
        pendentes.extend(no.values())
    return vistos


def _operacao(contrato: dict, metodo: str, caminho: str) -> dict:
    return contrato["paths"][caminho][metodo]


def _rota(metodo: str, caminho: str) -> APIRoute:
    [rota] = [
        rota
        for roteador in ROTEADORES
        for rota in roteador.routes
        if rota.path == caminho and metodo.upper() in rota.methods
    ]
    return rota


def _exemplos(no: dict) -> dict:
    return no["content"]["application/json"]["examples"]


def _padrao_do_caminho(caminho: str) -> re.Pattern[str]:
    return re.compile("^" + re.sub(r"\{[^}]+\}", "[^/]+", caminho) + "$")


def test_respostas_nao_expoem_campos_sensiveis(contrato):
    componentes = contrato["components"]["schemas"]
    esquemas = _esquemas_de_resposta(contrato)

    expostos = {
        (esquema, campo)
        for esquema in esquemas
        for campo in componentes[esquema].get("properties", {})
        if campo in CAMPOS_SENSIVEIS
    }

    assert "MinhaConta" in esquemas
    assert expostos == set()


def test_cadastro_de_cliente_recebe_so_os_dados_necessarios(contrato):
    corpo = contrato["paths"]["/usuarios"]["post"]["requestBody"]["content"]["application/json"]
    esquema = contrato["components"]["schemas"][_nome_do_esquema(corpo["schema"]["$ref"])]

    assert set(esquema["properties"]) == CAMPOS_DO_CADASTRO
    assert esquema["additionalProperties"] is False


@pytest.mark.parametrize("caminho", LISTAGENS)
def test_listagem_e_paginada(contrato, caminho):
    operacao = contrato["paths"][caminho]["get"]
    resposta = operacao["responses"]["200"]["content"]["application/json"]
    esquema = contrato["components"]["schemas"][_nome_do_esquema(resposta["schema"]["$ref"])]

    parametros = {
        parametro["name"] for parametro in operacao["parameters"] if parametro["in"] == "query"
    }
    assert {"page", "limit"} <= parametros
    assert {"dados", "paginacao"} <= set(esquema["properties"])


def test_erro_padrao_e_componente_com_os_campos_do_rnf10(contrato):
    esquema = contrato["components"]["schemas"]["RespostaErro"]

    assert set(esquema["properties"]) == CAMPOS_DO_ERRO_PADRAO
    assert set(esquema["required"]) == CAMPOS_DO_ERRO_PADRAO


def test_esquema_bearer_aceita_o_access_token_jwt(contrato):
    esquema = contrato["components"]["securitySchemes"]["HTTPBearer"]

    assert esquema == {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": DESCRICAO_BEARER,
    }


def test_so_as_rotas_publicas_dispensam_o_bearer(contrato):
    sem_bearer = {
        (metodo, caminho)
        for caminho, operacoes in contrato["paths"].items()
        for metodo, operacao in operacoes.items()
        if "security" not in operacao
    }

    assert sem_bearer == OPERACOES_PUBLICAS


def test_toda_tag_usada_tem_descricao(contrato):
    usadas = {
        tag
        for operacoes in contrato["paths"].values()
        for operacao in operacoes.values()
        for tag in operacao["tags"]
    }
    descritas = {tag["name"] for tag in contrato["tags"] if tag["description"]}

    assert usadas == descritas


def test_exemplos_mantem_os_campos_nulos(contrato):
    resposta = _operacao(contrato, "get", "/usuarios/me")["responses"]["200"]

    assert _exemplos(resposta)["cliente"]["value"]["unidadeId"] is None


@pytest.mark.parametrize(("metodo", "caminho"), OPERACOES)
def test_operacao_tem_resumo_e_perfil_na_descricao(contrato, metodo, caminho):
    operacao = _operacao(contrato, metodo, caminho)
    descricoes = {resposta["description"] for resposta in operacao["responses"].values()}

    assert operacao["summary"]
    assert operacao["description"].startswith("**Perfil:** ")
    assert "Successful Response" not in descricoes


@pytest.mark.parametrize(("metodo", "caminho"), OPERACOES)
def test_operacao_documenta_os_status_reais(contrato, metodo, caminho):
    operacao = _operacao(contrato, metodo, caminho)
    esperados = STATUS_POR_OPERACAO[(metodo, caminho)]

    assert {int(status) for status in operacao["responses"]} == esperados
    assert ("requestBody" in operacao) == (HTTPStatus.BAD_REQUEST in esperados)


@pytest.mark.parametrize(("metodo", "caminho"), OPERACOES)
def test_respostas_de_erro_seguem_o_erro_padrao(contrato, metodo, caminho):
    respostas = _operacao(contrato, metodo, caminho)["responses"]
    padrao = _padrao_do_caminho(caminho)

    for status, resposta in respostas.items():
        if int(status) < HTTPStatus.BAD_REQUEST:
            continue
        corpo = resposta["content"]["application/json"]
        assert corpo["schema"] == {"$ref": "#/components/schemas/RespostaErro"}
        assert corpo["examples"]
        for exemplo in corpo["examples"].values():
            erro = RespostaErro.model_validate(exemplo["value"])
            assert STATUS_DO_CODIGO[erro.error] == int(status)
            assert padrao.match(erro.path)


@pytest.mark.parametrize(("metodo", "caminho"), OPERACOES_COM_CORPO_NA_RESPOSTA)
def test_exemplos_de_sucesso_seguem_o_schema_da_resposta(contrato, metodo, caminho):
    rota = _rota(metodo, caminho)
    status = str(int(rota.status_code or HTTPStatus.OK))
    exemplos = _exemplos(_operacao(contrato, metodo, caminho)["responses"][status])

    assert exemplos
    for exemplo in exemplos.values():
        resposta = rota.response_model.model_validate(exemplo["value"])
        assert resposta.model_dump(mode="json", by_alias=True) == exemplo["value"]


@pytest.mark.parametrize(("metodo", "caminho"), OPERACOES_COM_BODY)
def test_exemplos_de_request_sao_aceitos_pela_validacao(contrato, metodo, caminho):
    esquema_do_body = _rota(metodo, caminho).body_field.field_info.annotation
    exemplos = _exemplos(_operacao(contrato, metodo, caminho)["requestBody"])

    assert exemplos
    for exemplo in exemplos.values():
        esquema_do_body.model_validate(exemplo["value"])


@pytest.mark.parametrize("caminho", ["/pedidos/{id}/cancelamento", "/pagamentos"])
def test_header_de_simulacao_do_gateway_tem_descricao(contrato, caminho):
    [header] = [
        parametro
        for parametro in contrato["paths"][caminho]["post"]["parameters"]
        if parametro["in"] == "header"
    ]

    assert header["name"] == "X-Simular-Resultado"
    assert header["description"]


def test_todas_as_operacoes_implementadas_estao_documentadas(contrato):
    operacoes = {
        (metodo, caminho)
        for caminho, operacoes_do_caminho in contrato["paths"].items()
        for metodo in operacoes_do_caminho
    }

    assert operacoes == set(STATUS_POR_OPERACAO)


def test_contrato_nao_usa_o_erro_de_validacao_do_fastapi(contrato):
    assert {"HTTPValidationError", "ValidationError"}.isdisjoint(contrato["components"]["schemas"])


def test_contrato_versionado_esta_igual_ao_da_api(contrato):
    versionado = json.loads(CONTRATO_VERSIONADO.read_text(encoding="utf-8"))

    assert versionado == contrato, "Rode: uv run python -m src.api.openapi.exportar"
