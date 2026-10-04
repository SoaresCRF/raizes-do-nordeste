from src.infrastructure.seguranca.hash_senha import HashSenha

SENHA = "Raizes@2026"


def test_gera_hash_argon2id_sem_a_senha_em_texto():
    senha_hash = HashSenha().gerar(SENHA)

    assert senha_hash.startswith("$argon2id$")
    assert SENHA not in senha_hash


def test_gera_hashes_diferentes_para_a_mesma_senha():
    hash_senha = HashSenha()

    assert hash_senha.gerar(SENHA) != hash_senha.gerar(SENHA)


def test_confere_senha_correta():
    hash_senha = HashSenha()

    assert hash_senha.confere(SENHA, hash_senha.gerar(SENHA))


def test_recusa_senha_errada():
    hash_senha = HashSenha()

    assert not hash_senha.confere("outra-senha", hash_senha.gerar(SENHA))
