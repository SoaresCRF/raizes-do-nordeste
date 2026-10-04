from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


class HashSenha:
    def __init__(self) -> None:
        self._hasher = PasswordHasher()

    def gerar(self, senha: str) -> str:
        return self._hasher.hash(senha)

    def confere(self, senha: str, senha_hash: str) -> bool:
        try:
            return self._hasher.verify(senha_hash, senha)
        except VerifyMismatchError:
            return False
