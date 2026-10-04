import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from src.api.middlewares.limite_corpo import TAMANHO_MAXIMO_CORPO_BYTES


@pytest.fixture
def cliente(app):
    @app.post("/teste/eco")
    async def ecoar_tamanho(request: Request):
        return {"tamanho": len(await request.body())}

    return TestClient(app)


def _em_partes(tamanho: int, parte: int = 64 * 1024):
    enviado = 0
    while enviado < tamanho:
        pedaco = min(parte, tamanho - enviado)
        enviado += pedaco
        yield b"x" * pedaco


def test_aceita_body_exatamente_no_limite(cliente):
    resposta = cliente.post("/teste/eco", content=b"x" * TAMANHO_MAXIMO_CORPO_BYTES)

    assert resposta.status_code == 200
    assert resposta.json() == {"tamanho": TAMANHO_MAXIMO_CORPO_BYTES}


def test_rejeita_body_acima_do_limite(cliente):
    resposta = cliente.post("/teste/eco", content=b"x" * (TAMANHO_MAXIMO_CORPO_BYTES + 1))
    corpo = resposta.json()

    assert resposta.status_code == 413
    assert corpo["error"] == "CORPO_MUITO_GRANDE"
    assert corpo["message"] == f"Corpo da requisição excede {TAMANHO_MAXIMO_CORPO_BYTES} bytes"
    assert corpo["path"] == "/teste/eco"
    assert corpo["requestId"]


def test_rejeita_body_em_partes_acima_do_limite(cliente):
    resposta = cliente.post("/teste/eco", content=_em_partes(TAMANHO_MAXIMO_CORPO_BYTES + 1))

    assert resposta.status_code == 413


def test_body_em_partes_dentro_do_limite_chega_inteiro_na_rota(cliente):
    resposta = cliente.post("/teste/eco", content=_em_partes(200 * 1024))

    assert resposta.json() == {"tamanho": 200 * 1024}
