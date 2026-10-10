from http import HTTPStatus
from typing import Any

from src.api.openapi.respostas import (
    JSON_MALFORMADO,
    TOKEN_AUSENTE,
    ExemploErro,
    resposta_de_sucesso,
    resposta_sem_conteudo,
    respostas_de_erro,
    validacao_falhou,
)
from src.application.auth.sessoes import MENSAGEM_CREDENCIAIS_INVALIDAS, MENSAGEM_REFRESH_INVALIDO
from src.domain.erros.erros import CredenciaisInvalidas, NaoAutenticado

# Encurtados e inválidos: só mostram o formato. O refresh token real tem 43 caracteres.
ACCESS_TOKEN_EXEMPLO = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2In0.assinatura"
REFRESH_TOKEN_EXEMPLO = "q8Zr1v2kX9wP4tN7yH3mB6cJ0dF5gL8sA1eU2iO3pQ4"
EXPIRES_IN_EXEMPLO = 3600

EXEMPLOS_LOGIN = {
    "cliente": {
        "summary": "Cliente do seed",
        "value": {"email": "cliente@raizesdonordeste.com.br", "senha": "Raizes@2026"},
    }
}

LOGIN: dict[str, Any] = {
    "summary": "Fazer login",
    "description": (
        "**Perfil:** público.\n\n"
        "Confere e-mail (sem diferenciar maiúsculas) e senha e abre uma sessão. Devolve o "
        "`accessToken` (JWT, válido por `expiresIn` segundos), usado no header "
        "`Authorization: Bearer`, e o `refreshToken` (válido por 7 dias), usado em "
        "`POST /auth/refresh`. E-mail inexistente, senha errada e conta inativa recebem a "
        "mesma resposta 401."
    ),
    "responses": {
        **resposta_de_sucesso(
            HTTPStatus.OK,
            "Sessão aberta",
            {
                "cliente": {
                    "accessToken": ACCESS_TOKEN_EXEMPLO,
                    "refreshToken": REFRESH_TOKEN_EXEMPLO,
                    "tokenType": "Bearer",
                    "expiresIn": EXPIRES_IN_EXEMPLO,
                    "user": {"id": 6, "nome": "Maria Cliente", "perfil": "CLIENTE"},
                }
            },
        ),
        **respostas_de_erro(
            "/auth/login",
            JSON_MALFORMADO,
            ExemploErro(
                HTTPStatus.UNAUTHORIZED, CredenciaisInvalidas.codigo, MENSAGEM_CREDENCIAIS_INVALIDAS
            ),
            validacao_falhou("email", "Deve ser um e-mail válido"),
        ),
    },
}

EXEMPLOS_REFRESH = {
    "refresh": {
        "summary": "Refresh token do login",
        "value": {"refreshToken": REFRESH_TOKEN_EXEMPLO},
    }
}

REFRESH: dict[str, Any] = {
    "summary": "Renovar o access token",
    "description": (
        "**Perfil:** público (o `refreshToken` do body é a credencial).\n\n"
        "Emite um novo `accessToken` para a mesma sessão. O `refreshToken` continua o mesmo "
        "até expirar (7 dias) ou até o logout."
    ),
    "responses": {
        **resposta_de_sucesso(
            HTTPStatus.OK,
            "Access token renovado",
            {
                "renovado": {
                    "accessToken": ACCESS_TOKEN_EXEMPLO,
                    "tokenType": "Bearer",
                    "expiresIn": EXPIRES_IN_EXEMPLO,
                }
            },
        ),
        **respostas_de_erro(
            "/auth/refresh",
            JSON_MALFORMADO,
            ExemploErro(HTTPStatus.UNAUTHORIZED, NaoAutenticado.codigo, MENSAGEM_REFRESH_INVALIDO),
            validacao_falhou("refreshToken", "Campo obrigatório"),
        ),
    },
}

LOGOUT: dict[str, Any] = {
    "summary": "Encerrar a sessão",
    "description": (
        "**Perfil:** autenticado (qualquer perfil).\n\n"
        "Revoga a sessão do token: o `accessToken` e o `refreshToken` dela deixam de valer."
    ),
    "responses": {
        **resposta_sem_conteudo("Sessão encerrada"),
        **respostas_de_erro("/auth/logout", TOKEN_AUSENTE),
    },
}
