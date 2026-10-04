from sqlalchemy import Connection, insert

from src.domain.auditoria.auditoria import AcaoAuditoria
from src.infrastructure.database.tabelas import log_auditoria
from src.infrastructure.logging.logger import request_id_atual


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
