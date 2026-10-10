from http import HTTPStatus
from typing import Any

from src.api.openapi.respostas import (
    REQUEST_ID_EXEMPLO,
    TOKEN_AUSENTE,
    resposta_de_sucesso,
    respostas_de_erro,
    sem_acesso_a_unidade,
    validacao_falhou,
)

LISTAR_AUDITORIA: dict[str, Any] = {
    "summary": "Listar registros de auditoria",
    "description": (
        "**Perfil:** GERENTE (só a própria unidade) e ADMIN.\n\n"
        "Registros de ações sensíveis (criação, mudança de status e cancelamento de pedido, "
        "pagamento, estorno, resgate de pontos, movimentação de estoque, criação de unidade e "
        "alteração de produto) e de acesso a dados pessoais (RN21), mais recentes primeiro, "
        "paginados. Sem `unidadeId`, o gerente vê a própria unidade; registros sem unidade "
        "(produtos) só o ADMIN vê. Filtros: `entidade`, `entidadeId`, `acao` e `unidadeId`. "
        "Valores em dinheiro aparecem como texto em `dadosAntes` e `dadosDepois`."
    ),
    "responses": {
        **resposta_de_sucesso(
            HTTPStatus.OK,
            "Página de registros",
            {
                "pagamento": {
                    "dados": [
                        {
                            "logId": 58,
                            "usuarioId": 6,
                            "unidadeId": 1,
                            "acao": "PAGAMENTO_REGISTRADO",
                            "entidade": "Pagamento",
                            "entidadeId": 31,
                            "dadosAntes": None,
                            "dadosDepois": {
                                "pedidoId": 9002,
                                "status": "APROVADO",
                                "valor": "47.70",
                            },
                            "requestId": REQUEST_ID_EXEMPLO,
                            "createdAt": "2026-02-05T12:31:00Z",
                        }
                    ],
                    "paginacao": {"page": 1, "limit": 10, "total": 1, "totalPaginas": 1},
                }
            },
        ),
        **respostas_de_erro(
            "/auditoria",
            TOKEN_AUSENTE,
            sem_acesso_a_unidade(2),
            validacao_falhou("entidadeId", "Deve ser um número inteiro"),
        ),
    },
}
