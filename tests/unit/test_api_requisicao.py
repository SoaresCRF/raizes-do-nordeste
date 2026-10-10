import re
import uuid

import pytest
from fastapi.testclient import TestClient
from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError

FORMATO_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
EMAIL_DA_LINHA = "maria@exemplo.com.br"


@pytest.fixture
def cliente(app):
    @app.get("/teste/ok")
    def responder_ok():
        return {"ok": True}

    @app.get("/teste/falha")
    def falhar():
        raise RuntimeError("detalhe interno do banco")

    @app.get("/teste/falha-banco")
    def falhar_no_banco():
        raise IntegrityError(
            "INSERT INTO usuario (email) VALUES (%(email)s)",
            None,
            UniqueViolation(
                'duplicate key value violates unique constraint "usuario_email_key"\n'
                f"DETAIL:  Key (email)=({EMAIL_DA_LINHA}) already exists."
            ),
        )

    return TestClient(app)


def _linhas_com(log_json, mensagem: str) -> list[dict]:
    return [linha for linha in log_json() if linha["mensagem"].startswith(mensagem)]


def test_erro_inesperado_vira_500_padronizado_sem_detalhe_interno(cliente):
    resposta = cliente.get("/teste/falha")
    corpo = resposta.json()

    assert resposta.status_code == 500
    assert set(corpo) == {"error", "message", "details", "timestamp", "path", "requestId"}
    assert corpo["error"] == "ERRO_INTERNO"
    assert corpo["message"] == "Erro interno no servidor"
    assert corpo["details"] == []
    assert corpo["path"] == "/teste/falha"
    assert FORMATO_TIMESTAMP.match(corpo["timestamp"])
    assert "detalhe interno" not in resposta.text


def test_erro_inesperado_vai_para_o_log_com_o_mesmo_request_id(cliente, log_json):
    corpo = cliente.get("/teste/falha").json()

    [erro] = _linhas_com(log_json, "Erro inesperado")
    uuid.UUID(corpo["requestId"])
    assert erro["request_id"] == corpo["requestId"]
    assert "RuntimeError: detalhe interno do banco" in erro["excecao"]


def test_erro_de_banco_vai_para_o_log_sem_os_dados_da_linha(cliente, log_json):
    resposta = cliente.get("/teste/falha-banco")

    [erro] = _linhas_com(log_json, "Erro de banco")
    assert resposta.status_code == 500
    assert resposta.json()["error"] == "ERRO_INTERNO"
    assert erro["nivel"] == "ERROR"
    assert erro["request_id"] == resposta.json()["requestId"]
    assert (erro["tipo_erro"], erro["sqlstate"]) == ("UniqueViolation", "23505")
    assert EMAIL_DA_LINHA not in str(log_json())


def test_registra_acesso_com_metodo_caminho_status_e_duracao(cliente, log_json):
    cliente.get("/teste/ok")

    [acesso] = _linhas_com(log_json, "Requisição concluída")
    assert acesso["metodo"] == "GET"
    assert acesso["caminho"] == "/teste/ok"
    assert acesso["status"] == 200
    assert acesso["duracao_ms"] >= 0
    uuid.UUID(acesso["request_id"])


def test_cada_requisicao_recebe_um_request_id_diferente(cliente, log_json):
    cliente.get("/teste/ok")
    cliente.get("/teste/ok")

    primeiro, segundo = _linhas_com(log_json, "Requisição concluída")
    assert primeiro["request_id"] != segundo["request_id"]


def test_log_de_acesso_nao_registra_query_string(cliente, log_json):
    cliente.get("/teste/ok?email=cliente@raizesdonordeste.com.br")

    [acesso] = _linhas_com(log_json, "Requisição concluída")
    assert acesso["caminho"] == "/teste/ok"
    # O httpx do TestClient loga a URL completa; só interessa o log do servidor.
    logs_do_servidor = [linha for linha in log_json() if linha["logger"].startswith("src.")]
    assert "cliente@raizesdonordeste.com.br" not in str(logs_do_servidor)


def test_expoe_o_contrato_openapi_em_docs(cliente):
    resposta = cliente.get("/docs/openapi.json")

    assert resposta.status_code == 200
    assert resposta.json()["info"]["title"] == "Raízes do Nordeste"
