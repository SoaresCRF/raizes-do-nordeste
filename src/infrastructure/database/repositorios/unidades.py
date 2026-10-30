from dataclasses import asdict

from sqlalchemy import Connection, func, insert, select, update

from src.domain.unidade.unidade import DadosUnidade, Unidade
from src.infrastructure.database.tabelas import unidade


class RepositorioUnidades:
    def __init__(self, conexao: Connection) -> None:
        self._conexao = conexao

    def buscar_por_id(self, unidade_id: int) -> Unidade | None:
        linha = self._conexao.execute(
            select(unidade).where(unidade.c.id == unidade_id)
        ).one_or_none()
        return Unidade(**linha._mapping) if linha else None

    def listar(self, limit: int, offset: int) -> list[Unidade]:
        consulta = select(unidade).order_by(unidade.c.id).limit(limit).offset(offset)
        return [Unidade(**linha._mapping) for linha in self._conexao.execute(consulta)]

    def contar(self) -> int:
        consulta = select(func.count()).select_from(unidade)
        return self._conexao.execute(consulta).scalar_one()

    def inserir(self, dados: DadosUnidade) -> Unidade:
        comando = insert(unidade).values(**asdict(dados)).returning(unidade)
        return Unidade(**self._conexao.execute(comando).one()._mapping)

    def atualizar(self, unidade_id: int, dados: DadosUnidade, ativa: bool) -> Unidade | None:
        comando = (
            update(unidade)
            .where(unidade.c.id == unidade_id)
            .values(**asdict(dados), ativa=ativa)
            .returning(unidade)
        )
        linha = self._conexao.execute(comando).one_or_none()
        return Unidade(**linha._mapping) if linha else None
