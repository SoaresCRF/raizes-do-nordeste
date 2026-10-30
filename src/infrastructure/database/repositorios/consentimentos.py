from sqlalchemy import Connection, insert, select
from sqlalchemy.dialects.postgresql import distinct_on

from src.domain.usuario.usuario import Consentimento, FinalidadeConsentimento
from src.infrastructure.database.tabelas import consentimento


class RepositorioConsentimentos:
    def __init__(self, conexao: Connection) -> None:
        self._conexao = conexao

    def inserir(
        self,
        usuario_id: int,
        finalidade: FinalidadeConsentimento,
        concedido: bool,
        versao_termo: str,
    ) -> Consentimento:
        comando = (
            insert(consentimento)
            .values(
                usuario_id=usuario_id,
                finalidade=finalidade,
                concedido=concedido,
                versao_termo=versao_termo,
            )
            .returning(consentimento)
        )
        return Consentimento(**self._conexao.execute(comando).one()._mapping)

    def listar_vigentes(self, usuario_id: int) -> list[Consentimento]:
        consulta = (
            select(consentimento)
            .ext(distinct_on(consentimento.c.finalidade))
            .where(consentimento.c.usuario_id == usuario_id)
            .order_by(
                consentimento.c.finalidade,
                consentimento.c.registrado_em.desc(),
                consentimento.c.id.desc(),
            )
        )
        return [Consentimento(**linha._mapping) for linha in self._conexao.execute(consulta)]
