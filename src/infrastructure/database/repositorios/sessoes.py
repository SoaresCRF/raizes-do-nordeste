from sqlalchemy import ColumnElement, Connection, func, insert, select, update

from src.domain.usuario import Sessao
from src.infrastructure.database.tabelas import sessao


class RepositorioSessoes:
    def __init__(self, conexao: Connection) -> None:
        self._conexao = conexao

    def inserir(self, usuario_id: int) -> Sessao:
        comando = insert(sessao).values(usuario_id=usuario_id).returning(sessao)
        return Sessao(**self._conexao.execute(comando).one()._mapping)

    def esta_ativa(self, sessao_id: int, usuario_id: int) -> bool:
        consulta = select(sessao.c.id).where(
            sessao.c.id == sessao_id,
            sessao.c.usuario_id == usuario_id,
            sessao.c.revogada_em.is_(None),
        )
        return self._conexao.execute(consulta).first() is not None

    def revogar(self, sessao_id: int) -> None:
        self._revogar_ativas(sessao.c.id == sessao_id)

    def revogar_do_usuario(self, usuario_id: int) -> None:
        self._revogar_ativas(sessao.c.usuario_id == usuario_id)

    def _revogar_ativas(self, filtro: ColumnElement[bool]) -> None:
        self._conexao.execute(
            update(sessao)
            .where(filtro, sessao.c.revogada_em.is_(None))
            .values(revogada_em=func.now())
        )
