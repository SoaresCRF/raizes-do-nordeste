from http import HTTPStatus
from typing import Any

from src.api.openapi.respostas import (
    REQUEST_ID_EXEMPLO,
    TOKEN_AUSENTE,
    documentar_erros,
    documentar_sucesso,
    perfil_sem_permissao,
    validacao_falhou,
)
from src.domain.usuario.usuario import Perfil

LISTAR_AUDITORIA: dict[str, Any] = {
    "summary": "Listar registros de auditoria",
    "description": (
        "**Perfil:** GERENTE (só a própria unidade) e ADMIN.\n\n"
        "Registros de ações sensíveis (criação, mudança de status e cancelamento de pedido, "
        "pagamento, resgate de pontos, movimentação de estoque, criação de unidade e "
        "alteração de produto) e de acesso a dados pessoais (RN21), mais recentes primeiro, "
        "paginados. O gerente vê só a própria unidade; registros sem unidade (produtos) só o "
        "ADMIN vê. Filtros: `entidade` e `entidadeId`. "
        "Valores em dinheiro aparecem como texto em `dadosAntes` e `dadosDepois`."
    ),
    "responses": {
        **documentar_sucesso(
            HTTPStatus.OK,
            "Página de registros",
            {
                "pagamento": {
                    "dados": [
                        {
                            "logId": 58,
                            "usuarioId": 5,
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
        **documentar_erros(
            "/auditoria",
            TOKEN_AUSENTE,
            perfil_sem_permissao(Perfil.CLIENTE),
            validacao_falhou("entidadeId", "Deve ser um número inteiro"),
        ),
    },
}
