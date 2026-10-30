from dataclasses import replace

from sqlalchemy import Connection

from src.domain.auditoria.auditoria import FiltrosAuditoria, LogAuditoria
from src.domain.usuario.usuario import UsuarioAutenticado, obter_unidade_restrita
from src.infrastructure.database.repositorios.auditoria import RepositorioAuditoria


def listar_auditoria(
    conexao: Connection,
    usuario: UsuarioAutenticado,
    filtros: FiltrosAuditoria,
    limit: int,
    offset: int,
) -> tuple[list[LogAuditoria], int]:
    filtros = replace(filtros, unidade_id=obter_unidade_restrita(usuario))
    repositorio = RepositorioAuditoria(conexao)
    return repositorio.listar(filtros, limit, offset), repositorio.contar(filtros)
