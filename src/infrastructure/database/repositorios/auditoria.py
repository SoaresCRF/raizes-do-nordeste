from sqlalchemy import ColumnElement, Connection, func, insert, select

from src.domain.auditoria.auditoria import AcaoAuditoria, FiltrosAuditoria, LogAuditoria
from src.infrastructure.database.tabelas import log_auditoria
from src.infrastructure.logging.logger import request_id_atual


def _filtros(filtros: FiltrosAuditoria) -> list[ColumnElement[bool]]:
    pares = [
        (log_auditoria.c.entidade, filtros.entidade),
        (log_auditoria.c.entidade_id, filtros.entidade_id),
        (log_auditoria.c.acao, filtros.acao),
        (log_auditoria.c.unidade_id, filtros.unidade_id),
    ]
    return [coluna == valor for coluna, valor in pares if valor is not None]


class RepositorioAuditoria:
    def __init__(self, conexao: Connection) -> None:
        self._conexao = conexao

    def registrar(
        self,
        *,
        usuario_id: int | None,
        unidade_id: int | None,
        acao: AcaoAuditoria,
        entidade: str,
        entidade_id: int,
        dados_antes: dict | None,
        dados_depois: dict | None,
    ) -> None:
        # Usa a conexão do caso de uso: o registro só fica se a ação for confirmada.
        # O requestId liga o registro ao log da requisição e ao erro padrão (RN20).
        self._conexao.execute(
            insert(log_auditoria).values(
                usuario_id=usuario_id,
                unidade_id=unidade_id,
                acao=acao,
                entidade=entidade,
                entidade_id=entidade_id,
                dados_antes=dados_antes,
                dados_depois=dados_depois,
                request_id=request_id_atual.get(),
            )
        )

    def listar(self, filtros: FiltrosAuditoria, limit: int, offset: int) -> list[LogAuditoria]:
        consulta = (
            select(log_auditoria)
            .where(*_filtros(filtros))
            .order_by(log_auditoria.c.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return [LogAuditoria(**linha._mapping) for linha in self._conexao.execute(consulta)]

    def contar(self, filtros: FiltrosAuditoria) -> int:
        consulta = select(func.count()).select_from(log_auditoria).where(*_filtros(filtros))
        return self._conexao.execute(consulta).scalar_one()
