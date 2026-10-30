from datetime import UTC, datetime, timedelta

import jwt

from src.domain.erros.erros import NaoAutenticado
from src.domain.usuario.usuario import Perfil, Usuario, UsuarioAutenticado

ALGORITMO = "HS256"
CLAIMS_OBRIGATORIAS = ["sub", "perfil", "sid", "exp"]
MENSAGEM_TOKEN_INVALIDO = "Token de acesso inválido ou expirado"


class ServicoTokenJwt:
    def __init__(self, segredo: str, validade: timedelta) -> None:
        self._segredo = segredo
        self.validade = validade

    def emitir(self, usuario: Usuario, sessao_id: int) -> str:
        agora = datetime.now(UTC)
        claims = {
            "sub": str(usuario.id),
            "perfil": usuario.perfil,
            "unidadeId": usuario.unidade_id,
            "sid": sessao_id,
            "iat": agora,
            "exp": agora + self.validade,
        }
        return jwt.encode(claims, self._segredo, algorithm=ALGORITMO)

    def validar(self, token: str) -> UsuarioAutenticado:
        try:
            claims = jwt.decode(
                token,
                self._segredo,
                algorithms=[ALGORITMO],
                options={"require": CLAIMS_OBRIGATORIAS},
            )
            return UsuarioAutenticado(
                id=int(claims["sub"]),
                perfil=Perfil(claims["perfil"]),
                unidade_id=claims.get("unidadeId"),
                sessao_id=int(claims["sid"]),
            )
        except (jwt.InvalidTokenError, ValueError) as erro:
            raise NaoAutenticado(MENSAGEM_TOKEN_INVALIDO) from erro
