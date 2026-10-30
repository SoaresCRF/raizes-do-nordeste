from sqlalchemy import ColumnElement, Connection, func, insert, select

from src.domain.auditoria.auditoria import AcaoAuditoria, FiltrosAuditoria, LogAuditoria
from src.domain.pedido.pedido import ENTIDADE_PEDIDO, Pedido
from src.infrastructure.database.tabelas import log_auditoria
from src.infrastructure.logging.logger import request_id_atual


def _montar_condicoes(filtros: FiltrosAuditoria) -> list[ColumnElement[bool]]:
    pares = [
        (log_auditoria.c.entidade, filtros.entidade),
        (log_auditoria.c.entidade_id, filtros.entidade_id),
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

    def registrar_do_pedido(
        self,
        usuario_id: int,
        acao: AcaoAuditoria,
        pedido: Pedido,
        dados_antes: dict | None,
        dados_depois: dict,
    ) -> None:
        self.registrar(
            usuario_id=usuario_id,
            unidade_id=pedido.unidade_id,
            acao=acao,
            entidade=ENTIDADE_PEDIDO,
            entidade_id=pedido.id,
            dados_antes=dados_antes,
            dados_depois=dados_depois,
        )

    def listar(self, filtros: FiltrosAuditoria, limit: int, offset: int) -> list[LogAuditoria]:
        consulta = (
            select(log_auditoria)
            .where(*_montar_condicoes(filtros))
            .order_by(log_auditoria.c.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return [LogAuditoria(**linha._mapping) for linha in self._conexao.execute(consulta)]

    def contar(self, filtros: FiltrosAuditoria) -> int:
        consulta = (
            select(func.count()).select_from(log_auditoria).where(*_montar_condicoes(filtros))
        )
        return self._conexao.execute(consulta).scalar_one()
