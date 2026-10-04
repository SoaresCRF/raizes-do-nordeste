import json
import logging
import sys

import pytest

from src.infrastructure.logging.logger import FormatadorJson, configurar_logging, request_id_atual


def _registro(mensagem: str = "Pedido criado", **atributos) -> logging.LogRecord:
    return logging.makeLogRecord(
        {"name": "teste", "levelno": logging.INFO, "levelname": "INFO", "msg": mensagem} | atributos
    )


def _formatar(registro: logging.LogRecord) -> dict:
    return json.loads(FormatadorJson().format(registro))


@pytest.fixture
def logger_raiz():
    raiz = logging.getLogger()
    nivel, handlers = raiz.level, raiz.handlers[:]
    yield raiz
    raiz.setLevel(nivel)
    raiz.handlers[:] = handlers


def test_formata_registro_como_json_com_campos_extras():
    linha = _formatar(_registro(pedido_id=9001))

    assert linha["nivel"] == "INFO"
    assert linha["logger"] == "teste"
    assert linha["mensagem"] == "Pedido criado"
    assert linha["pedido_id"] == 9001
    assert linha["timestamp"].endswith("Z")


def test_ignora_color_message_do_uvicorn():
    linha = _formatar(_registro(color_message="[32mPedido criado[0m"))

    assert "color_message" not in linha


def test_inclui_request_id_da_requisicao_atual():
    token = request_id_atual.set("3f2c9a4e")
    try:
        linha = _formatar(_registro())
    finally:
        request_id_atual.reset(token)

    assert linha["request_id"] == "3f2c9a4e"


def test_request_id_fica_nulo_fora_de_requisicao():
    assert _formatar(_registro())["request_id"] is None


def test_inclui_traceback_da_excecao():
    try:
        raise ValueError("falha de teste")
    except ValueError:
        registro = _registro(exc_info=sys.exc_info())

    assert "ValueError: falha de teste" in _formatar(registro)["excecao"]


def test_configura_nivel_e_formato_do_logger_raiz(logger_raiz):
    configurar_logging("WARNING")

    assert logger_raiz.level == logging.WARNING
    assert isinstance(logger_raiz.handlers[0].formatter, FormatadorJson)
