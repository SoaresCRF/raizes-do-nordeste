from http import HTTPStatus
from typing import Any

from src.api.openapi.respostas import (
    JSON_MALFORMADO,
    TIMESTAMP_EXEMPLO,
    TOKEN_AUSENTE,
    UNIDADE_INEXISTENTE,
    ExemploErro,
    perfil_sem_permissao,
    resposta_de_sucesso,
    resposta_sem_conteudo,
    respostas_de_erro,
    validacao_falhou,
)
from src.domain.erros.erros import EmailJaCadastrado
from src.domain.usuario.usuario import Perfil
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
        **resposta_de_sucesso(
            HTTPStatus.CREATED,
            "Cliente cadastrado",
            {
                "cliente": {
                    "id": 8,
                    "nome": "Ana Souza",
                    "email": "ana.souza@raizesdonordeste.com.br",
                    "perfil": "CLIENTE",
                }
            },
        ),
        **respostas_de_erro(
            "/usuarios",
            JSON_MALFORMADO,
            EMAIL_JA_CADASTRADO,
            validacao_falhou("senha", "Deve ter pelo menos 8 caractere(s)"),
        ),
    },
}

MINHA_CONTA: dict[str, Any] = {
    "summary": "Consultar a própria conta",
    "description": (
        "**Perfil:** autenticado (qualquer perfil).\n\n"
        "Dados da própria conta, sem senha nem tokens, e os consentimentos vigentes (o "
        "registro mais recente de cada finalidade). `unidadeId` só vem preenchido para "
        "funcionário de unidade."
    ),
    "responses": {
        **resposta_de_sucesso(
            HTTPStatus.OK,
            "Dados da conta",
            {
                "cliente": {
                    "id": 6,
                    "nome": "Maria Cliente",
                    "email": "cliente@raizesdonordeste.com.br",
                    "perfil": "CLIENTE",
                    "unidadeId": None,
                    "consentimentos": [
                        {
                            "finalidade": "FIDELIDADE",
                            "concedido": True,
                            "registradoEm": TIMESTAMP_EXEMPLO,
                        }
                    ],
                }
            },
        ),
        **respostas_de_erro("/usuarios/me", TOKEN_AUSENTE),
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
        **resposta_de_sucesso(
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
        **respostas_de_erro(
            "/usuarios/me/consentimentos",
            JSON_MALFORMADO,
            TOKEN_AUSENTE,
            perfil_sem_permissao(Perfil.ATENDENTE),
            validacao_falhou(
                "finalidade", "Deve ser um destes valores: 'FIDELIDADE' ou 'MARKETING'"
            ),
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
        **resposta_sem_conteudo("Conta anonimizada"),
        **respostas_de_erro("/usuarios/me", TOKEN_AUSENTE, perfil_sem_permissao(Perfil.ADMIN)),
    },
}

EXEMPLOS_CADASTRAR_FUNCIONARIO = {
    "atendente": {
        "summary": "Atendente da unidade Recife",
        "value": {
            "nome": "Carlos Lima",
            "email": "carlos.lima@raizesdonordeste.com.br",
            "senha": "Senha@2026",
            "perfil": "ATENDENTE",
            "unidadeId": 1,
        },
    }
}

CADASTRAR_FUNCIONARIO: dict[str, Any] = {
    "summary": "Cadastrar funcionário",
    "description": (
        "**Perfil:** ADMIN.\n\n"
        "Cria a conta de um funcionário: `ATENDENTE`, `COZINHA` ou `GERENTE` exigem "
        "`unidadeId`; `ADMIN` atua na rede toda e não recebe `unidadeId`; `CLIENTE` não é "
        "perfil de funcionário. Perfil e unidade incoerentes dão 422. E-mail único (RN25)."
    ),
    "responses": {
        **resposta_de_sucesso(
            HTTPStatus.CREATED,
            "Funcionário cadastrado",
            {
                "atendente": {
                    "id": 8,
                    "nome": "Carlos Lima",
                    "email": "carlos.lima@raizesdonordeste.com.br",
                    "perfil": "ATENDENTE",
                    "unidadeId": 1,
                }
            },
        ),
        **respostas_de_erro(
            "/usuarios/funcionarios",
            JSON_MALFORMADO,
            TOKEN_AUSENTE,
            perfil_sem_permissao(Perfil.GERENTE),
            UNIDADE_INEXISTENTE,
            EMAIL_JA_CADASTRADO,
            validacao_falhou("unidadeId", "Obrigatório para o perfil ATENDENTE"),
        ),
    },
}
