from sqlalchemy import Connection, func, insert, select

from src.domain.fidelidade.fidelidade import TipoTransacaoFidelidade, TransacaoFidelidade
from src.infrastructure.database.tabelas import transacao_fidelidade


class RepositorioFidelidade:
    def __init__(self, conexao: Connection) -> None:
        self._conexao = conexao

    def inserir(
        self, cliente_id: int, tipo: TipoTransacaoFidelidade, pontos: int, pedido_id: int
    ) -> None:
        self._conexao.execute(
            insert(transacao_fidelidade).values(
                cliente_id=cliente_id, tipo=tipo, pontos=pontos, pedido_id=pedido_id
            )
        )

    def calcular_saldo(self, cliente_id: int) -> int:
        consulta = select(func.coalesce(func.sum(transacao_fidelidade.c.pontos), 0)).where(
            transacao_fidelidade.c.cliente_id == cliente_id
        )
        return self._conexao.execute(consulta).scalar_one()

    def listar(self, cliente_id: int, limit: int, offset: int) -> list[TransacaoFidelidade]:
        consulta = (
            select(transacao_fidelidade)
            .where(transacao_fidelidade.c.cliente_id == cliente_id)
            .order_by(transacao_fidelidade.c.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return [TransacaoFidelidade(**linha._mapping) for linha in self._conexao.execute(consulta)]

    def contar(self, cliente_id: int) -> int:
        consulta = (
            select(func.count())
            .select_from(transacao_fidelidade)
            .where(transacao_fidelidade.c.cliente_id == cliente_id)
        )
        return self._conexao.execute(consulta).scalar_one()

    def somar_do_pedido(self, pedido_id: int, tipo: TipoTransacaoFidelidade) -> int:
        consulta = select(func.coalesce(func.sum(transacao_fidelidade.c.pontos), 0)).where(
            transacao_fidelidade.c.pedido_id == pedido_id, transacao_fidelidade.c.tipo == tipo
        )
        return self._conexao.execute(consulta).scalar_one()
