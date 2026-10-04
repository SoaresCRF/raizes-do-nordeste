import ast
from pathlib import Path

import pytest

PASTA_DOMAIN = Path(__file__).resolve().parents[2] / "src" / "domain"
MODULOS_PROIBIDOS_NO_DOMAIN = (
    "src.application",
    "src.infrastructure",
    "src.api",
    "src.config",
    "sqlalchemy",
    "fastapi",
    "pydantic",
)


def _modulos_importados(arquivo: Path) -> set[str]:
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    modulos = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            modulos.update(alias.name for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module:
            modulos.add(no.module)
    return modulos


@pytest.mark.parametrize(
    "arquivo",
    sorted(PASTA_DOMAIN.rglob("*.py")),
    ids=lambda arquivo: arquivo.relative_to(PASTA_DOMAIN).as_posix(),
)
def test_domain_nao_importa_outras_camadas(arquivo):
    importados = _modulos_importados(arquivo)

    proibidos = {modulo for modulo in importados if modulo.startswith(MODULOS_PROIBIDOS_NO_DOMAIN)}
    assert proibidos == set()
