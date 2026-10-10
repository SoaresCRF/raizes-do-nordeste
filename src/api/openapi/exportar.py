import json
from pathlib import Path

from src.config.configuracao import carregar_configuracao
from src.main import criar_app

# Contrato legível no repositório sem subir a API (CF14).
CONTRATO_VERSIONADO = Path(__file__).resolve().parents[3] / "docs" / "openapi.json"


def exportar_contrato() -> None:
    contrato = criar_app(carregar_configuracao()).openapi()
    CONTRATO_VERSIONADO.write_text(
        json.dumps(contrato, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


if __name__ == "__main__":
    exportar_contrato()
