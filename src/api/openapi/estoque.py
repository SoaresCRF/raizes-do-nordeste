from http import HTTPStatus
from typing import Any

from src.api.openapi.respostas import (
    JSON_MALFORMADO,
    TOKEN_AUSENTE,
    UNIDADE_INEXISTENTE,
    ExemploErro,
    documentar_erros,
    documentar_sucesso,
    nao_encontrado,
    sem_acesso_a_unidade,
    validacao_falhou,
)
from src.domain.erros import EstoqueInsuficiente

UNIDADE_DO_FILTRO_AUSENTE = validacao_falhou("unidadeId", "Campo obrigatório")

CONSULTAR_SALDOS: dict[str, Any] = {
    "summary": "Consultar o saldo da unidade",
    "description": (
        "**Perfil:** ATENDENTE, COZINHA e GERENTE (só a própria unidade) e ADMIN.\n\n"
        "Saldo de cada produto oferecido na unidade, em ordem de produto, paginado. "
        "`unidadeId` é obrigatório. CLIENTE e funcionário de outra unidade recebem 403; o "
        "funcionário recebe o 403 antes de saber se a unidade existe (RN23)."
    ),
    "responses": {
        **documentar_sucesso(
            HTTPStatus.OK,
            "Página de saldos",
            {
                "recife": {
                    "dados": [
                        {"produtoId": 1, "nome": "Tapioca", "quantidade": 100},
                        {"produtoId": 2, "nome": "Cuscuz recheado", "quantidade": 100},
                    ],
                    "paginacao": {"page": 1, "limit": 2, "total": 6, "totalPaginas": 3},
                }
            },
        ),
        **documentar_erros(
            "/estoque",
            TOKEN_AUSENTE,
            sem_acesso_a_unidade(2),
            UNIDADE_INEXISTENTE,
            UNIDADE_DO_FILTRO_AUSENTE,
        ),
    },
}

EXEMPLOS_MOVIMENTAR_ESTOQUE = {
    "entrada": {
        "summary": "Reposição do bolo de macaxeira em Recife",
        "value": {
            "unidadeId": 1,
            "produtoId": 3,
            "tipo": "ENTRADA",
            "quantidade": 20,
            "motivo": "Reposição semanal",
        },
    }
}

MOVIMENTAR_ESTOQUE: dict[str, Any] = {
    "summary": "Movimentar estoque",
    "description": (
        "**Perfil:** GERENTE (só a própria unidade) e ADMIN.\n\n"
        "Registra uma `ENTRADA` ou `SAIDA` manual, com `quantidade` inteira maior que zero "
        "(RN06), e devolve o saldo resultante. Saída maior que o saldo: 409 "
        "`ESTOQUE_INSUFICIENTE` (RN04). A primeira entrada de um produto numa unidade passa a "
        "oferecê-lo lá (RN03). Unidade ou produto inexistente: 404. A movimentação fica na "
        "auditoria."
    ),
    "responses": {
        **documentar_sucesso(
            HTTPStatus.CREATED,
            "Movimentação registrada",
            {
                "entrada": {
                    "movimentacaoId": 12,
                    "tipo": "ENTRADA",
                    "quantidade": 20,
                    "saldoAtual": 22,
                }
            },
        ),
        **documentar_erros(
            "/estoque/movimentacoes",
            JSON_MALFORMADO,
            TOKEN_AUSENTE,
            sem_acesso_a_unidade(2),
            nao_encontrado("Produto 99 não encontrado"),
            ExemploErro(
                HTTPStatus.CONFLICT,
                EstoqueInsuficiente.codigo,
                "Estoque insuficiente do produto 3",
                (("quantidade", "Disponível: 2"),),
            ),
            validacao_falhou("quantidade", "Deve ser maior que 0"),
        ),
    },
}
