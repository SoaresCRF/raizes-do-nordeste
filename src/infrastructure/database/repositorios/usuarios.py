from sqlalchemy import Connection, func, insert, select, update
from sqlalchemy.exc import IntegrityError

from src.domain.erros import DetalheErro, EmailJaCadastrado
from src.domain.usuario import Perfil, Usuario
from src.infrastructure.database.tabelas import usuario

RESTRICAO_EMAIL_UNICO = "uq_usuario_email"
MENSAGEM_EMAIL_JA_CADASTRADO = "E-mail já cadastrado"


class RepositorioUsuarios:
    def __init__(self, conexao: Connection) -> None:
        self._conexao = conexao

    def buscar_por_email(self, email: str) -> Usuario | None:
        linha = self._conexao.execute(select(usuario).where(usuario.c.email == email)).one_or_none()
        return Usuario(**linha._mapping) if linha else None

    def inserir(
        self, nome: str, email: str, senha_hash: str, perfil: Perfil, unidade_id: int | None
    ) -> Usuario:
        comando = (
            insert(usuario)
            .values(
                nome=nome,
                email=email,
                senha_hash=senha_hash,
                perfil=perfil,
                unidade_id=unidade_id,
            )
            .returning(usuario)
        )
        try:
            linha = self._conexao.execute(comando).one()
        except IntegrityError as erro:
            if erro.orig.diag.constraint_name == RESTRICAO_EMAIL_UNICO:
                raise EmailJaCadastrado(
                    MENSAGEM_EMAIL_JA_CADASTRADO, [DetalheErro("email", "Já cadastrado")]
                ) from None
            raise
        return Usuario(**linha._mapping)

    def buscar_por_id(self, usuario_id: int) -> Usuario | None:
        linha = self._conexao.execute(
            select(usuario).where(usuario.c.id == usuario_id)
        ).one_or_none()
        return Usuario(**linha._mapping) if linha else None

    def travar(self, usuario_id: int) -> None:
        self._conexao.execute(
            select(usuario.c.id).where(usuario.c.id == usuario_id).with_for_update(key_share=True)
        )

    def anonimizar(self, usuario_id: int, nome: str, email: str, senha_hash: str) -> None:
        self._conexao.execute(
            update(usuario)
            .where(usuario.c.id == usuario_id)
            .values(
                nome=nome,
                email=email,
                senha_hash=senha_hash,
                ativo=False,
                anonimizado_em=func.now(),
            )
        )
