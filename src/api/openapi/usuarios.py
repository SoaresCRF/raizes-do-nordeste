from http import HTTPStatus
from typing import Any

from src.api.openapi.respostas import (
    JSON_MALFORMADO,
    TIMESTAMP_EXEMPLO,
    TOKEN_AUSENTE,
    ExemploErro,
    documentar_erros,
    documentar_sem_conteudo,
    documentar_sucesso,
    perfil_sem_permissao,
    validacao_falhou,
)
from src.domain.erros import EmailJaCadastrado
from src.domain.usuario import Perfil
from src.infrastructure.database.repositorios.usuarios import MENSAGEM_EMAIL_JA_CADASTRADO

EMAIL_JA_CADASTRADO = ExemploErro(
    HTTPStatus.CONFLICT, EmailJaCadastrado.codigo, MENSAGEM_EMAIL_JA_CADASTRADO
)

EXEMPLOS_CADASTRAR_CLIENTE = {
    "com_fidelidade": {
        "summary": "Cliente que aceita o programa de fidelidade",
        "value": {
            "nome": "Ana Souza",
            "email": "ana.souza@raizesdonordeste.com.br",
            "senha": "Senha@2026",
            "consentimentoFidelidade": True,
        },
    }
}

CADASTRAR_CLIENTE: dict[str, Any] = {
    "summary": "Cadastrar cliente",
    "description": (
        "**Perfil:** público.\n\n"
        "Cria uma conta com perfil `CLIENTE` recebendo só os dados necessários: nome, e-mail, "
        "senha e a escolha sobre o programa de fidelidade (campos a mais dão 422). O e-mail é "
        "guardado em minúsculas e não pode repetir (RN25); a senha (8 a 128 caracteres) é "
        "guardada só como hash argon2. `consentimentoFidelidade` fica registrado no histórico "
        "de consentimentos mesmo quando `false` (LGPD)."
    ),
    "responses": {
        **documentar_sucesso(
            HTTPStatus.CREATED,
            "Cliente cadastrado",
            {
                "cliente": {
                    "id": 6,
                    "nome": "Ana Souza",
                    "email": "ana.souza@raizesdonordeste.com.br",
                    "perfil": "CLIENTE",
                }
            },
        ),
        **documentar_erros(
            "/usuarios",
            JSON_MALFORMADO,
            EMAIL_JA_CADASTRADO,
            validacao_falhou("senha", "Deve ter pelo menos 8 caractere(s)"),
        ),
    },
}

EXEMPLOS_REGISTRAR_CONSENTIMENTO = {
    "revogar_fidelidade": {
        "summary": "Revogar o consentimento do programa de fidelidade",
        "value": {"finalidade": "FIDELIDADE", "concedido": False, "versaoTermo": "1.0"},
    }
}

REGISTRAR_CONSENTIMENTO: dict[str, Any] = {
    "summary": "Registrar consentimento",
    "description": (
        "**Perfil:** CLIENTE.\n\n"
        "Acrescenta um registro ao histórico de consentimentos (LGPD); nada é sobrescrito. "
        "Vale o registro mais recente de cada finalidade, então `concedido: false` revoga. "
        "Sem consentimento `FIDELIDADE` vigente o cliente não acumula nem resgata pontos (RN17)."
    ),
    "responses": {
        **documentar_sucesso(
            HTTPStatus.CREATED,
            "Consentimento registrado",
            {
                "revogado": {
                    "finalidade": "FIDELIDADE",
                    "concedido": False,
                    "registradoEm": TIMESTAMP_EXEMPLO,
                }
            },
        ),
        **documentar_erros(
            "/usuarios/me/consentimentos",
            JSON_MALFORMADO,
            TOKEN_AUSENTE,
            perfil_sem_permissao(Perfil.ATENDENTE),
            validacao_falhou("finalidade", "Deve ser um destes valores: 'FIDELIDADE'"),
        ),
    },
}

ANONIMIZAR_CONTA: dict[str, Any] = {
    "summary": "Anonimizar a própria conta",
    "description": (
        "**Perfil:** CLIENTE.\n\n"
        "Direito de exclusão (LGPD): apaga nome, e-mail e senha da conta e encerra todas as "
        "sessões. Pedidos, pagamentos e consentimentos continuam, sem os dados pessoais, para a "
        "contabilidade e a auditoria."
    ),
    "responses": {
        **documentar_sem_conteudo("Conta anonimizada"),
        **documentar_erros("/usuarios/me", TOKEN_AUSENTE, perfil_sem_permissao(Perfil.ADMIN)),
    },
}
