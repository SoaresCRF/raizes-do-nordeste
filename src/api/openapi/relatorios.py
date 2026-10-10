from http import HTTPStatus
from typing import Any

from src.api.openapi.respostas import (
    TOKEN_AUSENTE,
    perfil_sem_permissao,
    resposta_de_sucesso,
    respostas_de_erro,
    validacao_falhou,
)
from src.domain.usuario.usuario import Perfil

RELATORIO_DE_VENDAS: dict[str, Any] = {
    "summary": "Relatório de vendas",
    "description": (
        "**Perfil:** GERENTE (só a própria unidade) e ADMIN (rede toda).\n\n"
        "Totais de venda agrupados por `unidade`, `regiao`, `canal` ou `produto`. Venda é "
        "pedido pago e não cancelado (`EM_PREPARO`, `PRONTO` ou `ENTREGUE`). `de` e `ate` "
        "(opcionais, AAAA-MM-DD) filtram pelo dia UTC de criação do pedido, inclusive nas "
        "pontas. Sem paginação; as linhas vêm em ordem de total decrescente e, no empate, pelo "
        "nome do grupo. `grupoId` é nulo quando o grupo não tem id (região e canal)."
    ),
    "responses": {
        **resposta_de_sucesso(
            HTTPStatus.OK,
            "Totais de venda",
            {
                "por_canal": {
                    "agrupamento": "canal",
                    "de": "2026-02-01",
                    "ate": "2026-02-28",
                    "dados": [
                        {
                            "grupoId": None,
                            "grupo": "APP",
                            "pedidos": 12,
                            "quantidade": 31,
                            "total": 612.4,
                        },
                        {
                            "grupoId": None,
                            "grupo": "BALCAO",
                            "pedidos": 5,
                            "quantidade": 9,
                            "total": 158.3,
                        },
                    ],
                }
            },
        ),
        **respostas_de_erro(
            "/relatorios/vendas",
            TOKEN_AUSENTE,
            perfil_sem_permissao(Perfil.COZINHA),
            validacao_falhou("ate", "Deve ser igual ou posterior a de"),
        ),
    },
}
