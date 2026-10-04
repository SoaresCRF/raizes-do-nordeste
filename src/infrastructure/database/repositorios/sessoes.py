from datetime import datetime

from sqlalchemy import Connection, func, insert, select, update

from src.domain.usuario.usuario import Sessao
from src.infrastructure.database.tabelas import sessao


class RepositorioSessoes:
    def __init__(self, conexao: Connection) -> None:
        self._conexao = conexao

    def criar(self, usuario_id: int, refresh_token_hash: str, expira_em: datetime) -> Sessao:
        comando = (
            insert(sessao)
            .values(
                usuario_id=usuario_id,
                refresh_token_hash=refresh_token_hash,
                expira_em=expira_em,
            )
            .returning(sessao)
        )
        return Sessao(**self._conexao.execute(comando).one()._mapping)

    def esta_ativa(self, sessao_id: int, usuario_id: int) -> bool:
        consulta = select(sessao.c.id).where(
            sessao.c.id == sessao_id,
            sessao.c.usuario_id == usuario_id,
            sessao.c.revogada_em.is_(None),
            sessao.c.expira_em > func.now(),
        )
        return self._conexao.execute(consulta).first() is not None

    def revogar(self, sessao_id: int) -> None:
        self._conexao.execute(
            update(sessao)
            .where(sessao.c.id == sessao_id, sessao.c.revogada_em.is_(None))
            .values(revogada_em=func.now())
        )

    def buscar_ativa_por_refresh(self, refresh_token_hash: str) -> Sessao | None:
        consulta = select(sessao).where(
            sessao.c.refresh_token_hash == refresh_token_hash,
            sessao.c.revogada_em.is_(None),
            sessao.c.expira_em > func.now(),
        )
        linha = self._conexao.execute(consulta).one_or_none()
        return Sessao(**linha._mapping) if linha else None

    def revogar_do_usuario(self, usuario_id: int) -> None:
        self._conexao.execute(
            update(sessao)
            .where(sessao.c.usuario_id == usuario_id, sessao.c.revogada_em.is_(None))
            .values(revogada_em=func.now())
        )
