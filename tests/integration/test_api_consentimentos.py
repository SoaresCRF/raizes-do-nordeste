import re

from src.infrastructure.database.seeds.dados_iniciais import DOMINIO_EMAIL

URL = "/usuarios/me/consentimentos"
FORMATO_DATA_HORA = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
VERSAO_TERMO = "1.1"


def _consentimento(**alteracoes) -> dict:
    padrao = {"finalidade": "FIDELIDADE", "concedido": False, "versaoTermo": VERSAO_TERMO}
    return padrao | alteracoes


def _vigentes(cliente_http, cabecalho) -> list[tuple[str, bool]]:
    consentimentos = cliente_http.get("/usuarios/me", headers=cabecalho).json()["consentimentos"]
    return [(registro["finalidade"], registro["concedido"]) for registro in consentimentos]


def test_cliente_revoga_consentimento(cliente_http, cliente_novo, entrar):
    cabecalho = entrar(cliente_novo["email"], cliente_novo["senha"])

    resposta = cliente_http.post(URL, json=_consentimento(), headers=cabecalho)
    corpo = resposta.json()

    assert resposta.status_code == 201
    assert set(corpo) == {"finalidade", "concedido", "registradoEm"}
    assert (corpo["finalidade"], corpo["concedido"]) == ("FIDELIDADE", False)
    assert FORMATO_DATA_HORA.match(corpo["registradoEm"])
    assert _vigentes(cliente_http, cabecalho) == [("FIDELIDADE", False)]


def test_vale_a_escolha_mais_recente(cliente_http, cliente_novo, entrar):
    cabecalho = entrar(cliente_novo["email"], cliente_novo["senha"])

    cliente_http.post(URL, json=_consentimento(concedido=False), headers=cabecalho)
    cliente_http.post(URL, json=_consentimento(concedido=True), headers=cabecalho)

    assert _vigentes(cliente_http, cabecalho) == [("FIDELIDADE", True)]


def test_cada_finalidade_tem_o_proprio_registro(cliente_http, cliente_novo, entrar):
    cabecalho = entrar(cliente_novo["email"], cliente_novo["senha"])

    cliente_http.post(
        URL, json=_consentimento(finalidade="MARKETING", concedido=True), headers=cabecalho
    )

    assert _vigentes(cliente_http, cabecalho) == [("FIDELIDADE", True), ("MARKETING", True)]


def test_finalidade_invalida_devolve_422(cliente_http, cliente_novo, entrar):
    cabecalho = entrar(cliente_novo["email"], cliente_novo["senha"])

    resposta = cliente_http.post(URL, json=_consentimento(finalidade="X"), headers=cabecalho)

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [
        {"field": "finalidade", "issue": "Deve ser um destes valores: 'FIDELIDADE' ou 'MARKETING'"}
    ]


def test_sem_versao_do_termo_devolve_422(cliente_http, cliente_novo, entrar):
    cabecalho = entrar(cliente_novo["email"], cliente_novo["senha"])
    dados = _consentimento()
    del dados["versaoTermo"]

    resposta = cliente_http.post(URL, json=dados, headers=cabecalho)

    assert resposta.json()["details"] == [{"field": "versaoTermo", "issue": "Campo obrigatório"}]


def test_funcionario_recebe_403(cliente_http, entrar):
    resposta = cliente_http.post(
        URL, json=_consentimento(), headers=entrar(f"gerente.recife@{DOMINIO_EMAIL}")
    )

    assert resposta.status_code == 403


def test_sem_token_devolve_401(cliente_http):
    assert cliente_http.post(URL, json=_consentimento()).status_code == 401
