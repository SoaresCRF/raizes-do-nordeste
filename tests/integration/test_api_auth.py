from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import func, select, update

from src.domain.usuario.usuario import Perfil
from src.infrastructure.database.seeds.dados_iniciais import DOMINIO_EMAIL, SENHA_DESENVOLVIMENTO
from src.infrastructure.database.tabelas import sessao, usuario
from src.infrastructure.seguranca.token import TokenJwt, resumir_refresh_token

EMAIL_CLIENTE = f"cliente@{DOMINIO_EMAIL}"
SEGUNDOS_POR_MINUTO = 60


def _validade_do_token(configuracao_api) -> timedelta:
    return timedelta(minutes=configuracao_api.jwt_expiracao_minutos)


def _login(cliente_http, email: str, senha: str = SENHA_DESENVOLVIMENTO):
    return cliente_http.post("/auth/login", json={"email": email, "senha": senha})


def test_login_valido_devolve_tokens_e_usuario(cliente_http, configuracao_api):
    resposta = _login(cliente_http, EMAIL_CLIENTE)
    corpo = resposta.json()

    assert resposta.status_code == 200
    assert set(corpo) == {"accessToken", "refreshToken", "tokenType", "expiresIn", "user"}
    assert corpo["tokenType"] == "Bearer"
    assert corpo["expiresIn"] == configuracao_api.jwt_expiracao_minutos * SEGUNDOS_POR_MINUTO
    assert corpo["user"] == {
        "id": corpo["user"]["id"],
        "nome": "Maria Cliente",
        "perfil": "CLIENTE",
    }


def test_access_token_identifica_o_usuario(cliente_http, configuracao_api):
    corpo = _login(cliente_http, EMAIL_CLIENTE).json()
    token_jwt = TokenJwt(configuracao_api.jwt_segredo, _validade_do_token(configuracao_api))

    usuario_do_token = token_jwt.ler(corpo["accessToken"])

    assert usuario_do_token.id == corpo["user"]["id"]
    assert usuario_do_token.perfil == Perfil.CLIENTE


def test_login_guarda_so_o_resumo_do_refresh_token(cliente_http, banco_semeado):
    refresh_token = _login(cliente_http, EMAIL_CLIENTE).json()["refreshToken"]

    with banco_semeado.connect() as conexao:
        resumo = resumir_refresh_token(refresh_token)
        sessoes = conexao.execute(
            select(func.count()).where(sessao.c.refresh_token_hash == resumo)
        ).scalar_one()
        em_claro = conexao.execute(
            select(func.count()).where(sessao.c.refresh_token_hash == refresh_token)
        ).scalar_one()
    assert (sessoes, em_claro) == (1, 0)


def test_senha_errada_devolve_401(cliente_http):
    resposta = _login(cliente_http, EMAIL_CLIENTE, "senha-errada")

    assert resposta.status_code == 401
    assert resposta.json()["error"] == "CREDENCIAIS_INVALIDAS"


def test_email_inexistente_e_senha_errada_tem_a_mesma_resposta(cliente_http):
    senha_errada = _login(cliente_http, EMAIL_CLIENTE, "senha-errada")
    inexistente = _login(cliente_http, f"ninguem@{DOMINIO_EMAIL}")

    assert senha_errada.status_code == inexistente.status_code == 401
    assert senha_errada.json()["error"] == inexistente.json()["error"]
    assert senha_errada.json()["message"] == inexistente.json()["message"]


def test_login_sem_email_devolve_422(cliente_http):
    resposta = cliente_http.post("/auth/login", json={"senha": SENHA_DESENVOLVIMENTO})

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [{"field": "email", "issue": "Campo obrigatório"}]


def test_login_aceita_email_com_maiusculas(cliente_http):
    assert _login(cliente_http, EMAIL_CLIENTE.upper()).status_code == 200


def test_usuario_inativo_nao_entra(cliente_http, cliente_novo, banco_semeado):
    with banco_semeado.begin() as conexao:
        conexao.execute(
            update(usuario).where(usuario.c.id == cliente_novo["id"]).values(ativo=False)
        )

    resposta = _login(cliente_http, cliente_novo["email"], cliente_novo["senha"])

    assert resposta.status_code == 401
    assert resposta.json()["error"] == "CREDENCIAIS_INVALIDAS"


def test_token_invalido_devolve_401(cliente_http):
    resposta = cliente_http.get("/usuarios/me", headers={"Authorization": "Bearer abc"})

    assert resposta.status_code == 401
    assert resposta.json()["error"] == "NAO_AUTENTICADO"


def test_token_expirado_devolve_401(cliente_http, configuracao_api):
    claims = {
        "sub": "1",
        "perfil": "ADMIN",
        "sid": 1,
        "exp": datetime.now(UTC) - timedelta(minutes=1),
    }
    token = jwt.encode(claims, configuracao_api.jwt_segredo, algorithm="HS256")

    resposta = cliente_http.get("/usuarios/me", headers={"Authorization": f"Bearer {token}"})

    assert resposta.status_code == 401


def test_esquema_diferente_de_bearer_devolve_401(cliente_http):
    resposta = cliente_http.get("/usuarios/me", headers={"Authorization": "Basic dXNlcjpzZW5oYQ=="})

    assert resposta.status_code == 401
    assert resposta.json()["error"] == "NAO_AUTENTICADO"


def test_logout_devolve_204(cliente_http, entrar):
    resposta = cliente_http.post("/auth/logout", headers=entrar(EMAIL_CLIENTE))

    assert resposta.status_code == 204
    assert resposta.content == b""


def test_token_deixa_de_valer_apos_logout(cliente_http, entrar):
    cabecalho = entrar(EMAIL_CLIENTE)
    cliente_http.post("/auth/logout", headers=cabecalho)

    resposta = cliente_http.get("/usuarios/me", headers=cabecalho)

    assert resposta.status_code == 401
    assert resposta.json()["error"] == "NAO_AUTENTICADO"


def test_logout_encerra_so_a_sessao_atual(cliente_http, entrar):
    primeira = entrar(EMAIL_CLIENTE)
    segunda = entrar(EMAIL_CLIENTE)

    cliente_http.post("/auth/logout", headers=primeira)

    assert cliente_http.get("/usuarios/me", headers=segunda).status_code == 200


def test_logout_sem_token_devolve_401(cliente_http):
    assert cliente_http.post("/auth/logout").status_code == 401


def test_refresh_devolve_novo_access_token(cliente_http):
    refresh_token = _login(cliente_http, EMAIL_CLIENTE).json()["refreshToken"]

    resposta = cliente_http.post("/auth/refresh", json={"refreshToken": refresh_token})
    corpo = resposta.json()

    assert resposta.status_code == 200
    assert set(corpo) == {"accessToken", "tokenType", "expiresIn"}
    cabecalho = {"Authorization": f"Bearer {corpo['accessToken']}"}
    assert cliente_http.get("/usuarios/me", headers=cabecalho).status_code == 200


def test_refresh_token_desconhecido_devolve_401(cliente_http):
    resposta = cliente_http.post("/auth/refresh", json={"refreshToken": "qualquer-coisa"})

    assert resposta.status_code == 401
    assert resposta.json()["error"] == "NAO_AUTENTICADO"


def test_refresh_apos_logout_devolve_401(cliente_http):
    corpo = _login(cliente_http, EMAIL_CLIENTE).json()
    cliente_http.post("/auth/logout", headers={"Authorization": f"Bearer {corpo['accessToken']}"})

    resposta = cliente_http.post("/auth/refresh", json={"refreshToken": corpo["refreshToken"]})

    assert resposta.status_code == 401


def test_refresh_de_sessao_expirada_devolve_401(cliente_http, banco_semeado):
    refresh_token = _login(cliente_http, EMAIL_CLIENTE).json()["refreshToken"]
    with banco_semeado.begin() as conexao:
        conexao.execute(
            update(sessao)
            .where(sessao.c.refresh_token_hash == resumir_refresh_token(refresh_token))
            .values(expira_em=func.now() - timedelta(minutes=1))
        )

    resposta = cliente_http.post("/auth/refresh", json={"refreshToken": refresh_token})

    assert resposta.status_code == 401


def test_refresh_sem_token_devolve_422(cliente_http):
    resposta = cliente_http.post("/auth/refresh", json={})

    assert resposta.status_code == 422
    assert resposta.json()["details"] == [{"field": "refreshToken", "issue": "Campo obrigatório"}]
