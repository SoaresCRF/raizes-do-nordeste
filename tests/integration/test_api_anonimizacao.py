from sqlalchemy import func, select

from src.infrastructure.database.seeds.dados_iniciais import DOMINIO_EMAIL
from src.infrastructure.database.tabelas import consentimento, usuario
from src.infrastructure.seguranca.hash_senha import HashSenha

URL = "/usuarios/me"


def test_anonimiza_a_propria_conta(cliente_http, cliente_novo, entrar, banco_semeado):
    resposta = cliente_http.delete(
        URL, headers=entrar(cliente_novo["email"], cliente_novo["senha"])
    )

    assert resposta.status_code == 204
    with banco_semeado.connect() as conexao:
        registro = conexao.execute(select(usuario).where(usuario.c.id == cliente_novo["id"])).one()
    assert registro.nome == "Cliente anonimizado"
    assert registro.email == f"cliente-{cliente_novo['id']}@anonimizado.invalid"
    assert registro.ativo is False
    assert registro.anonimizado_em is not None
    assert not HashSenha().confere(cliente_novo["senha"], registro.senha_hash)


def test_login_com_os_dados_antigos_falha(cliente_http, cliente_novo, entrar):
    cliente_http.delete(URL, headers=entrar(cliente_novo["email"], cliente_novo["senha"]))

    resposta = cliente_http.post(
        "/auth/login", json={"email": cliente_novo["email"], "senha": cliente_novo["senha"]}
    )

    assert resposta.status_code == 401
    assert resposta.json()["error"] == "CREDENCIAIS_INVALIDAS"


def test_token_antigo_deixa_de_valer_apos_anonimizar(cliente_http, cliente_novo, entrar):
    cabecalho = entrar(cliente_novo["email"], cliente_novo["senha"])
    outra_sessao = entrar(cliente_novo["email"], cliente_novo["senha"])
    cliente_http.delete(URL, headers=cabecalho)

    assert cliente_http.get(URL, headers=outra_sessao).status_code == 401


def test_mantem_o_historico_de_consentimento(cliente_http, cliente_novo, entrar, banco_semeado):
    cliente_http.delete(URL, headers=entrar(cliente_novo["email"], cliente_novo["senha"]))

    with banco_semeado.connect() as conexao:
        registros = conexao.execute(
            select(func.count()).where(consentimento.c.usuario_id == cliente_novo["id"])
        ).scalar_one()
    assert registros == 1


def test_email_fica_livre_para_novo_cadastro(cliente_http, cliente_novo, entrar):
    cliente_http.delete(URL, headers=entrar(cliente_novo["email"], cliente_novo["senha"]))
    dados = {
        campo: cliente_novo[campo]
        for campo in ("nome", "email", "senha", "consentimentoFidelidade")
    }

    assert cliente_http.post("/usuarios", json=dados).status_code == 201


def test_funcionario_recebe_403(cliente_http, entrar):
    resposta = cliente_http.delete(URL, headers=entrar(f"gerente.recife@{DOMINIO_EMAIL}"))

    assert resposta.status_code == 403


def test_sem_token_devolve_401(cliente_http):
    assert cliente_http.delete(URL).status_code == 401
