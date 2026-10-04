import re
import uuid

from sqlalchemy import select

from src.domain.usuario.usuario import FinalidadeConsentimento
from src.infrastructure.database.seeds.dados_iniciais import DOMINIO_EMAIL
from src.infrastructure.database.tabelas import consentimento, usuario

SENHA_VALIDA = "SenhaForte123"
FORMATO_DATA_HORA = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _novo_cliente(**alteracoes) -> dict:
    return {
        "nome": "Ana Cliente",
        "email": f"ana-{uuid.uuid4().hex[:12]}@exemplo.com.br",
        "senha": SENHA_VALIDA,
        "consentimentoFidelidade": True,
    } | alteracoes


def _detalhes(resposta) -> list[dict]:
    return resposta.json()["details"]


def test_cadastra_cliente_sem_expor_a_senha(cliente_http, banco_semeado):
    dados = _novo_cliente()

    resposta = cliente_http.post("/usuarios", json=dados)
    corpo = resposta.json()

    assert resposta.status_code == 201
    assert corpo == {
        "id": corpo["id"],
        "nome": "Ana Cliente",
        "email": dados["email"],
        "perfil": "CLIENTE",
    }
    with banco_semeado.connect() as conexao:
        consulta = select(usuario.c.senha_hash).where(usuario.c.id == corpo["id"])
        senha_hash = conexao.execute(consulta).scalar_one()
    assert senha_hash.startswith("$argon2id$")


def test_registra_a_escolha_de_fidelidade_do_cadastro(cliente_http, banco_semeado):
    resposta = cliente_http.post("/usuarios", json=_novo_cliente(consentimentoFidelidade=False))

    with banco_semeado.connect() as conexao:
        consulta = select(consentimento).where(consentimento.c.usuario_id == resposta.json()["id"])
        registro = conexao.execute(consulta).one()
    assert registro.finalidade == FinalidadeConsentimento.FIDELIDADE
    assert registro.concedido is False
    assert registro.versao_termo == "1.0"


def test_email_invalido_devolve_422(cliente_http):
    resposta = cliente_http.post("/usuarios", json=_novo_cliente(email="abc"))

    assert resposta.status_code == 422
    assert _detalhes(resposta) == [{"field": "email", "issue": "Deve ser um e-mail válido"}]


def test_cadastro_sem_senha_devolve_422(cliente_http):
    dados = _novo_cliente()
    del dados["senha"]

    resposta = cliente_http.post("/usuarios", json=dados)

    assert resposta.status_code == 422
    assert _detalhes(resposta) == [{"field": "senha", "issue": "Campo obrigatório"}]


def test_senha_curta_devolve_422(cliente_http):
    resposta = cliente_http.post("/usuarios", json=_novo_cliente(senha="curta"))

    assert _detalhes(resposta) == [
        {"field": "senha", "issue": "Deve ter pelo menos 8 caractere(s)"}
    ]


def test_nome_em_branco_devolve_422(cliente_http):
    resposta = cliente_http.post("/usuarios", json=_novo_cliente(nome="   "))

    assert _detalhes(resposta) == [{"field": "nome", "issue": "Deve ter pelo menos 1 caractere(s)"}]


def test_perfil_no_body_e_rejeitado(cliente_http):
    resposta = cliente_http.post("/usuarios", json=_novo_cliente(perfil="ADMIN"))

    assert resposta.status_code == 422
    assert _detalhes(resposta) == [{"field": "perfil", "issue": "Campo não permitido"}]


def test_email_ja_cadastrado_devolve_409(cliente_http):
    dados = _novo_cliente()
    cliente_http.post("/usuarios", json=dados)

    resposta = cliente_http.post("/usuarios", json=dados)

    assert resposta.status_code == 409
    assert resposta.json()["error"] == "EMAIL_JA_CADASTRADO"
    assert _detalhes(resposta) == [{"field": "email", "issue": "Já cadastrado"}]


def test_email_e_unico_sem_diferenciar_maiusculas(cliente_http):
    dados = _novo_cliente()
    cliente_http.post("/usuarios", json=dados)

    resposta = cliente_http.post("/usuarios", json=dados | {"email": dados["email"].upper()})

    assert resposta.status_code == 409


def test_guarda_o_email_em_minusculas(cliente_http):
    email = f"Ana.{uuid.uuid4().hex[:12]}@Exemplo.COM.br"

    resposta = cliente_http.post("/usuarios", json=_novo_cliente(email=email))

    assert resposta.json()["email"] == email.lower()


def test_consulta_a_propria_conta_com_consentimentos(cliente_http, cliente_novo, entrar):
    cabecalho = entrar(cliente_novo["email"], cliente_novo["senha"])

    resposta = cliente_http.get("/usuarios/me", headers=cabecalho)
    corpo = resposta.json()

    assert resposta.status_code == 200
    assert set(corpo) == {"id", "nome", "email", "perfil", "unidadeId", "consentimentos"}
    assert corpo["email"] == cliente_novo["email"]
    assert corpo["unidadeId"] is None
    [fidelidade] = corpo["consentimentos"]
    assert (fidelidade["finalidade"], fidelidade["concedido"]) == ("FIDELIDADE", True)
    assert FORMATO_DATA_HORA.match(fidelidade["registradoEm"])


def test_funcionario_consulta_a_propria_conta_com_unidade(cliente_http, entrar):
    cabecalho = entrar(f"gerente.recife@{DOMINIO_EMAIL}")

    corpo = cliente_http.get("/usuarios/me", headers=cabecalho).json()

    assert (corpo["perfil"], corpo["unidadeId"], corpo["consentimentos"]) == ("GERENTE", 1, [])


def test_consultar_conta_sem_token_devolve_401(cliente_http):
    resposta = cliente_http.get("/usuarios/me")
    corpo = resposta.json()

    assert resposta.status_code == 401
    assert corpo["error"] == "NAO_AUTENTICADO"
    assert set(corpo) == {"error", "message", "details", "timestamp", "path", "requestId"}


def test_nome_com_caractere_nulo_devolve_422(cliente_http):
    resposta = cliente_http.post("/usuarios", json=_novo_cliente(nome="Ana\u0000"))

    assert resposta.status_code == 422
    assert _detalhes(resposta) == [{"field": "nome", "issue": "Não pode conter o caractere nulo"}]
