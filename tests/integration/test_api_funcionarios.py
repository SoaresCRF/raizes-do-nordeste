import uuid

from src.infrastructure.database.seeds.dados_iniciais import DOMINIO_EMAIL

URL = "/usuarios/funcionarios"
EMAIL_ADMIN = f"admin@{DOMINIO_EMAIL}"
EMAIL_GERENTE = f"gerente.recife@{DOMINIO_EMAIL}"
EMAIL_CLIENTE = f"cliente@{DOMINIO_EMAIL}"
SENHA_VALIDA = "SenhaForte123"
UNIDADE_RECIFE = 1
UNIDADE_INEXISTENTE = 9999


def _novo_funcionario(**alteracoes) -> dict:
    return {
        "nome": "Paula Atendente",
        "email": f"paula-{uuid.uuid4().hex[:12]}@{DOMINIO_EMAIL}",
        "senha": SENHA_VALIDA,
        "perfil": "ATENDENTE",
        "unidadeId": UNIDADE_RECIFE,
    } | alteracoes


def _detalhes(resposta) -> list[dict]:
    return resposta.json()["details"]


def test_admin_cadastra_atendente(cliente_http, entrar):
    dados = _novo_funcionario()

    resposta = cliente_http.post(URL, json=dados, headers=entrar(EMAIL_ADMIN))
    corpo = resposta.json()

    assert resposta.status_code == 201
    assert corpo == {
        "id": corpo["id"],
        "nome": "Paula Atendente",
        "email": dados["email"],
        "perfil": "ATENDENTE",
        "unidadeId": UNIDADE_RECIFE,
    }


def test_funcionario_cadastrado_consegue_entrar(cliente_http, entrar):
    dados = _novo_funcionario(perfil="COZINHA")
    cliente_http.post(URL, json=dados, headers=entrar(EMAIL_ADMIN))

    resposta = cliente_http.post(
        "/auth/login", json={"email": dados["email"], "senha": SENHA_VALIDA}
    )

    assert resposta.json()["user"]["perfil"] == "COZINHA"


def test_admin_cadastra_admin_sem_unidade(cliente_http, entrar):
    resposta = cliente_http.post(
        URL, json=_novo_funcionario(perfil="ADMIN", unidadeId=None), headers=entrar(EMAIL_ADMIN)
    )

    assert resposta.status_code == 201
    assert resposta.json()["unidadeId"] is None


def test_cliente_recebe_403(cliente_http, entrar):
    resposta = cliente_http.post(URL, json=_novo_funcionario(), headers=entrar(EMAIL_CLIENTE))

    assert resposta.status_code == 403
    assert resposta.json()["error"] == "ACESSO_NEGADO"


def test_cliente_recebe_403_mesmo_com_body_invalido(cliente_http, entrar):
    resposta = cliente_http.post(URL, json={}, headers=entrar(EMAIL_CLIENTE))

    assert resposta.status_code == 403


def test_gerente_recebe_403(cliente_http, entrar):
    resposta = cliente_http.post(URL, json=_novo_funcionario(), headers=entrar(EMAIL_GERENTE))

    assert resposta.status_code == 403


def test_sem_token_devolve_401(cliente_http):
    assert cliente_http.post(URL, json=_novo_funcionario()).status_code == 401


def test_unidade_inexistente_devolve_404(cliente_http, entrar):
    resposta = cliente_http.post(
        URL, json=_novo_funcionario(unidadeId=UNIDADE_INEXISTENTE), headers=entrar(EMAIL_ADMIN)
    )

    assert resposta.status_code == 404
    assert resposta.json()["message"] == f"Unidade {UNIDADE_INEXISTENTE} não encontrada"


def test_unidade_acima_do_maximo_devolve_422(cliente_http, entrar):
    resposta = cliente_http.post(
        URL, json=_novo_funcionario(unidadeId=2147483648), headers=entrar(EMAIL_ADMIN)
    )

    assert resposta.status_code == 422
    assert _detalhes(resposta) == [
        {"field": "unidadeId", "issue": "Deve ser menor ou igual a 2147483647"}
    ]


def test_gerente_sem_unidade_devolve_422(cliente_http, entrar):
    dados = _novo_funcionario(perfil="GERENTE")
    del dados["unidadeId"]

    resposta = cliente_http.post(URL, json=dados, headers=entrar(EMAIL_ADMIN))

    assert resposta.status_code == 422
    assert resposta.json()["error"] == "VALIDACAO_FALHOU"
    assert _detalhes(resposta) == [
        {"field": "unidadeId", "issue": "Obrigatório para o perfil GERENTE"}
    ]


def test_admin_com_unidade_devolve_422(cliente_http, entrar):
    resposta = cliente_http.post(
        URL, json=_novo_funcionario(perfil="ADMIN"), headers=entrar(EMAIL_ADMIN)
    )

    assert resposta.status_code == 422
    assert _detalhes(resposta) == [{"field": "unidadeId", "issue": "Não se aplica ao perfil ADMIN"}]


def test_perfil_cliente_devolve_422(cliente_http, entrar):
    resposta = cliente_http.post(
        URL, json=_novo_funcionario(perfil="CLIENTE", unidadeId=None), headers=entrar(EMAIL_ADMIN)
    )

    assert resposta.status_code == 422
    assert _detalhes(resposta) == [
        {"field": "perfil", "issue": "CLIENTE não é perfil de funcionário"}
    ]


def test_email_ja_cadastrado_devolve_409(cliente_http, entrar):
    resposta = cliente_http.post(
        URL, json=_novo_funcionario(email=EMAIL_GERENTE), headers=entrar(EMAIL_ADMIN)
    )

    assert resposta.status_code == 409
    assert resposta.json()["error"] == "EMAIL_JA_CADASTRADO"
