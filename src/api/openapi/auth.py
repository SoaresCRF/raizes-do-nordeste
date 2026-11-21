from http import HTTPStatus
from typing import Any

from src.api.openapi.respostas import (
    JSON_MALFORMADO,
    TOKEN_AUSENTE,
    ExemploErro,
    documentar_erros,
    documentar_sem_conteudo,
    documentar_sucesso,
    validacao_falhou,
)
from src.application.auth import MENSAGEM_CREDENCIAIS_INVALIDAS
from src.domain.erros import CredenciaisInvalidas

ACCESS_TOKEN_EXEMPLO = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1In0.assinatura"
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
        "`Authorization: Bearer`; depois desse prazo é preciso fazer login de novo. E-mail "
        "inexistente, senha errada e conta inativa recebem a mesma resposta 401."
    ),
    "responses": {
        **documentar_sucesso(
            HTTPStatus.OK,
            "Sessão aberta",
            {
                "cliente": {
                    "accessToken": ACCESS_TOKEN_EXEMPLO,
                    "tokenType": "Bearer",
                    "expiresIn": EXPIRES_IN_EXEMPLO,
                    "user": {"id": 5, "nome": "Maria Cliente", "perfil": "CLIENTE"},
                }
            },
        ),
        **documentar_erros(
            "/auth/login",
            JSON_MALFORMADO,
            ExemploErro(
                HTTPStatus.UNAUTHORIZED, CredenciaisInvalidas.codigo, MENSAGEM_CREDENCIAIS_INVALIDAS
            ),
            validacao_falhou("email", "Deve ser um e-mail válido"),
        ),
    },
}

LOGOUT: dict[str, Any] = {
    "summary": "Encerrar a sessão",
    "description": (
        "**Perfil:** autenticado (qualquer perfil).\n\n"
        "Revoga a sessão do token: o `accessToken` deixa de valer antes de expirar."
    ),
    "responses": {
        **documentar_sem_conteudo("Sessão encerrada"),
        **documentar_erros("/auth/logout", TOKEN_AUSENTE),
    },
}
