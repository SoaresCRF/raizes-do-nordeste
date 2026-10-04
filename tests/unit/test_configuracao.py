import pytest

from src.config.configuracao import ConfiguracaoInvalida, carregar_configuracao

VARIAVEIS_VALIDAS = {
    "PORTA": "8000",
    "BANCO_URL": "postgresql+psycopg://app:senha@localhost:5432/raizes",
    "JWT_SEGREDO": "x" * 32,
    "JWT_EXPIRACAO_MINUTOS": "60",
    "GATEWAY_TIMEOUT_SEGUNDOS": "2.5",
    "NIVEL_LOG": "INFO",
}


@pytest.fixture
def ambiente(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BANCO_URL_TESTE", raising=False)
    for nome, valor in VARIAVEIS_VALIDAS.items():
        monkeypatch.setenv(nome, valor)
    return monkeypatch


def test_carrega_variaveis_validas(ambiente):
    configuracao = carregar_configuracao()

    assert configuracao.porta == 8000
    assert configuracao.jwt_expiracao_minutos == 60
    assert configuracao.gateway_timeout_segundos == 2.5
    assert configuracao.nivel_log == "INFO"
    assert configuracao.banco_url_teste is None


def test_le_variaveis_do_arquivo_env(ambiente, tmp_path):
    ambiente.delenv("PORTA")
    (tmp_path / ".env").write_text("PORTA=9001\n", encoding="utf-8")

    assert carregar_configuracao().porta == 9001


def test_ignora_variaveis_do_docker_no_env(ambiente, tmp_path):
    (tmp_path / ".env").write_text("BANCO_ADMIN_SENHA=qualquer\n", encoding="utf-8")

    assert carregar_configuracao().porta == 8000


def test_falha_nomeando_variavel_ausente(ambiente):
    ambiente.delenv("JWT_SEGREDO")

    with pytest.raises(ConfiguracaoInvalida, match="JWT_SEGREDO"):
        carregar_configuracao()


def test_falha_nomeando_variavel_invalida(ambiente):
    ambiente.setenv("PORTA", "abc")
    ambiente.setenv("NIVEL_LOG", "VERBOSO")

    with pytest.raises(ConfiguracaoInvalida, match="PORTA, NIVEL_LOG|NIVEL_LOG, PORTA"):
        carregar_configuracao()


def test_rejeita_segredo_jwt_curto(ambiente):
    ambiente.setenv("JWT_SEGREDO", "curto")

    with pytest.raises(ConfiguracaoInvalida, match="JWT_SEGREDO"):
        carregar_configuracao()


def test_rejeita_url_de_banco_que_nao_e_postgres(ambiente):
    ambiente.setenv("BANCO_URL", "sqlite:///raizes.db")

    with pytest.raises(ConfiguracaoInvalida, match="BANCO_URL"):
        carregar_configuracao()


def test_repr_da_configuracao_nao_expoe_segredos(ambiente):
    texto = repr(carregar_configuracao())

    assert VARIAVEIS_VALIDAS["JWT_SEGREDO"] not in texto
    assert "senha" not in texto


def test_erro_de_configuracao_nao_expoe_o_valor_recebido(ambiente):
    ambiente.setenv("JWT_SEGREDO", "segredo-curto")

    with pytest.raises(ConfiguracaoInvalida) as erro:
        carregar_configuracao()

    assert "segredo-curto" not in str(erro.value.__cause__)
