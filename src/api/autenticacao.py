from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.api.dependencias import ConexaoBanco, ServicoToken
from src.application.auth.sessoes import autenticar
from src.domain.erros.erros import AcessoNegado, NaoAutenticado
from src.domain.usuario.usuario import Perfil, UsuarioAutenticado

MENSAGEM_TOKEN_AUSENTE = "Token de acesso ausente"
DESCRICAO_BEARER = "accessToken devolvido pelo POST /auth/login"

# auto_error=False: sem o header, o HTTPBearer levantaria HTTPException, que o
# tratador converte em 500; a ausência vira NaoAutenticado (401) aqui.
esquema_bearer = HTTPBearer(auto_error=False, bearerFormat="JWT", description=DESCRICAO_BEARER)


def obter_usuario_autenticado(
    credenciais: Annotated[HTTPAuthorizationCredentials | None, Depends(esquema_bearer)],
    conexao: ConexaoBanco,
    token_jwt: ServicoToken,
) -> UsuarioAutenticado:
    if credenciais is None:
        raise NaoAutenticado(MENSAGEM_TOKEN_AUSENTE)
    return autenticar(conexao, token_jwt, credenciais.credentials)


UsuarioLogado = Annotated[UsuarioAutenticado, Depends(obter_usuario_autenticado)]


def exigir_perfil(*perfis: Perfil) -> Callable[[UsuarioAutenticado], UsuarioAutenticado]:
    def verificar_perfil(usuario: UsuarioLogado) -> UsuarioAutenticado:
        if usuario.perfil not in perfis:
            raise AcessoNegado(f"Perfil {usuario.perfil} sem permissão para esta operação")
        return usuario

    return verificar_perfil


ClienteLogado = Annotated[UsuarioAutenticado, Depends(exigir_perfil(Perfil.CLIENTE))]
AdminLogado = Annotated[UsuarioAutenticado, Depends(exigir_perfil(Perfil.ADMIN))]
FuncionarioLogado = Annotated[
    UsuarioAutenticado,
    Depends(exigir_perfil(Perfil.ATENDENTE, Perfil.COZINHA, Perfil.GERENTE, Perfil.ADMIN)),
]

GestorLogado = Annotated[UsuarioAutenticado, Depends(exigir_perfil(Perfil.GERENTE, Perfil.ADMIN))]
