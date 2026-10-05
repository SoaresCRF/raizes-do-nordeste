from src.api.schemas.base import DataHoraUtc, EsquemaSaida

# Coluna log_auditoria.entidade: varchar(40).
TAMANHO_MAXIMO_ENTIDADE = 40


class LogAuditoriaResposta(EsquemaSaida):
    log_id: int
    usuario_id: int | None
    unidade_id: int | None
    acao: str
    entidade: str
    entidade_id: int
    dados_antes: dict | None
    dados_depois: dict | None
    request_id: str | None
    created_at: DataHoraUtc
