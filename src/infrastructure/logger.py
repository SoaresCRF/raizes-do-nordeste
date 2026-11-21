import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

request_id_atual: ContextVar[str | None] = ContextVar("request_id_atual", default=None)

_ATRIBUTOS_PADRAO = set(vars(logging.makeLogRecord({}))) | {"message", "asctime", "color_message"}


class FormatadorJson(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        momento = datetime.fromtimestamp(record.created, UTC)
        linha = {
            "timestamp": momento.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "nivel": record.levelname,
            "logger": record.name,
            "mensagem": record.getMessage(),
            "request_id": request_id_atual.get(),
        }
        linha |= {
            chave: valor for chave, valor in vars(record).items() if chave not in _ATRIBUTOS_PADRAO
        }
        if record.exc_info:
            linha["excecao"] = self.formatException(record.exc_info)
        return json.dumps(linha, ensure_ascii=False, default=str)


def configurar_logging(nivel: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(FormatadorJson())
    logging.basicConfig(level=nivel, handlers=[handler], force=True)
