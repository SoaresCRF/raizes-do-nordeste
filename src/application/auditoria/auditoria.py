from dataclasses import replace

from sqlalchemy import Connection

from src.domain.auditoria.auditoria import FiltrosAuditoria, LogAuditoria
from src.domain.usuario.usuario import Perfil, UsuarioAutenticado, verificar_acesso_a_unidade
from src.infrastructure.database.repositorios.auditoria import RepositorioAuditoria


def listar_auditoria(
    conexao: Connection,
    usuario: UsuarioAutenticado,
    filtros: FiltrosAuditoria,
    limit: int,
    offset: int,
) -> tuple[list[LogAuditoria], int]:
    if usuario.perfil == Perfil.GERENTE:
        # Sem o filtro, o gerente vê a própria unidade; com outra unidade, 403 (RN23).
        # Registros sem unidade (produto, que vale para a rede) ficam só com o ADMIN.
        unidade_id = usuario.unidade_id if filtros.unidade_id is None else filtros.unidade_id
        verificar_acesso_a_unidade(usuario, unidade_id)
        filtros = replace(filtros, unidade_id=unidade_id)
    repositorio = RepositorioAuditoria(conexao)
    return repositorio.listar(filtros, limit, offset), repositorio.contar(filtros)
