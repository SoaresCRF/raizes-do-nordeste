from datetime import date

from sqlalchemy import Connection

from src.domain.relatorio.relatorio import (
    Agrupamento,
    LinhaRelatorio,
    validar_periodo_do_relatorio,
)
from src.domain.usuario.usuario import Perfil, UsuarioAutenticado
from src.infrastructure.database.repositorios.relatorios import RepositorioRelatorios


def gerar_relatorio_de_vendas(
    conexao: Connection,
    usuario: UsuarioAutenticado,
    agrupamento: Agrupamento,
    de: date | None,
    ate: date | None,
) -> list[LinhaRelatorio]:
    validar_periodo_do_relatorio(de, ate)
    # Pela matriz da seção 3, o gerente vê a própria unidade e o ADMIN, a rede.
    unidade_id = usuario.unidade_id if usuario.perfil == Perfil.GERENTE else None
    return RepositorioRelatorios(conexao).somar_vendas(agrupamento, unidade_id, de, ate)
