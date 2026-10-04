from datetime import UTC, datetime, timedelta

import jwt
import pytest

from src.config.configuracao import TAMANHO_MINIMO_SEGREDO_JWT
from src.domain.erros.erros import NaoAutenticado
from src.domain.usuario.usuario import Perfil, Usuario, UsuarioAutenticado
from src.infrastructure.seguranca.token import (
    TokenJwt,
    gerar_refresh_token,
    resumir_refresh_token,
)

SEGREDO = "s" * TAMANHO_MINIMO_SEGREDO_JWT
OUTRO_SEGREDO = "o" * TAMANHO_MINIMO_SEGREDO_JWT
VALIDADE = timedelta(minutes=60)
SESSAO_ID = 42
TAMANHO_SHA256_HEX = 64


def _gerente() -> Usuario:
    agora = datetime.now(UTC)
    return Usuario(
        id=7,
        nome="Gerente Recife",
        email="gerente@exemplo.com.br",
        senha_hash="$argon2id$fake",
        perfil=Perfil.GERENTE,
        unidade_id=1,
        ativo=True,
        anonimizado_em=None,
        created_at=agora,
        updated_at=agora,
    )


def test_le_de_volta_o_usuario_e_a_sessao_do_token():
    token_jwt = TokenJwt(SEGREDO, VALIDADE)

    usuario = token_jwt.ler(token_jwt.emitir(_gerente(), SESSAO_ID))

    assert usuario == UsuarioAutenticado(
        id=7, perfil=Perfil.GERENTE, unidade_id=1, sessao_id=SESSAO_ID
    )


def test_token_tem_expiracao_conforme_a_validade():
    token = TokenJwt(SEGREDO, VALIDADE).emitir(_gerente(), SESSAO_ID)

    claims = jwt.decode(token, SEGREDO, algorithms=["HS256"])

    assert claims["exp"] - claims["iat"] == VALIDADE.total_seconds()
    assert claims["unidadeId"] == 1


def test_recusa_token_expirado():
    token = TokenJwt(SEGREDO, timedelta(seconds=-1)).emitir(_gerente(), SESSAO_ID)

    with pytest.raises(NaoAutenticado):
        TokenJwt(SEGREDO, VALIDADE).ler(token)


def test_recusa_token_assinado_com_outro_segredo():
    token = TokenJwt(OUTRO_SEGREDO, VALIDADE).emitir(_gerente(), SESSAO_ID)

    with pytest.raises(NaoAutenticado):
        TokenJwt(SEGREDO, VALIDADE).ler(token)


def test_recusa_token_sem_assinatura():
    agora = datetime.now(UTC)
    claims = {"sub": "7", "perfil": "ADMIN", "sid": SESSAO_ID, "exp": agora + VALIDADE}
    token = jwt.encode(claims, key=None, algorithm="none")

    with pytest.raises(NaoAutenticado):
        TokenJwt(SEGREDO, VALIDADE).ler(token)


def test_recusa_token_sem_sessao():
    agora = datetime.now(UTC)
    token = jwt.encode(
        {"sub": "7", "perfil": "GERENTE", "exp": agora + VALIDADE}, SEGREDO, algorithm="HS256"
    )

    with pytest.raises(NaoAutenticado):
        TokenJwt(SEGREDO, VALIDADE).ler(token)


def test_recusa_texto_que_nao_e_jwt():
    with pytest.raises(NaoAutenticado):
        TokenJwt(SEGREDO, VALIDADE).ler("abc")


def test_refresh_tokens_sao_diferentes_a_cada_geracao():
    assert gerar_refresh_token() != gerar_refresh_token()


def test_resumo_do_refresh_token_e_estavel_e_nao_contem_o_token():
    refresh_token = gerar_refresh_token()

    resumo = resumir_refresh_token(refresh_token)

    assert resumo == resumir_refresh_token(refresh_token)
    assert len(resumo) == TAMANHO_SHA256_HEX
    assert refresh_token not in resumo
