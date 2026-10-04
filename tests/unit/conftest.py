import io
import json
import logging

import pytest

from src.infrastructure.logging.logger import FormatadorJson
from src.main import criar_app


@pytest.fixture
def app(configuracao_api):
    return criar_app(configuracao_api)


@pytest.fixture
def log_json():
    fluxo = io.StringIO()
    handler = logging.StreamHandler(fluxo)
    handler.setFormatter(FormatadorJson())
    raiz = logging.getLogger()
    nivel_anterior = raiz.level
    raiz.addHandler(handler)
    raiz.setLevel(logging.INFO)
    yield lambda: [json.loads(linha) for linha in fluxo.getvalue().splitlines()]
    raiz.removeHandler(handler)
    raiz.setLevel(nivel_anterior)
