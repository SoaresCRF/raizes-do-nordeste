from http import HTTPStatus
from typing import Any

from src.api.openapi.respostas import (
    ID_NAO_INTEIRO,
    JSON_MALFORMADO,
    TOKEN_AUSENTE,
    UNIDADE_INEXISTENTE,
    ExemploErro,
    documentar_erros,
    documentar_sucesso,
    nao_encontrado,
    perfil_sem_permissao,
    sem_acesso_a_unidade,
    validacao_falhou,
)
from src.domain.erros import (
    AcessoNegado,
    EstoqueInsuficiente,
    PagamentoNaoPermitido,
    ProdutoIndisponivelNaUnidade,
    TransicaoStatusInvalida,
)
from src.domain.pedido import MENSAGEM_ESTOQUE_INSUFICIENTE
from src.domain.usuario import Perfil

PEDIDO_INEXISTENTE = nao_encontrado("Pedido 99 não encontrado")
PAGAMENTO_NAO_PERMITIDO = ExemploErro(
    HTTPStatus.CONFLICT,
    PagamentoNaoPermitido.codigo,
    "Pedido 9002 está EM_PREPARO e não aceita pagamento nem resgate",
)

EXEMPLOS_CRIAR_PEDIDO = {
    "totem": {
        "summary": "Cliente no totem (exemplo do roteiro)",
        "value": {
            "canalPedido": "TOTEM",
            "unidadeId": 2,
            "itens": [
                {"produtoId": 101, "quantidade": 2},
                {"produtoId": 305, "quantidade": 1},
            ],
            "formaPagamento": "MOCK",
        },
    },
    "balcao": {
        "summary": "Atendente no balcão, para um cliente cadastrado",
        "value": {
            "canalPedido": "BALCAO",
            "unidadeId": 1,
            "clienteId": 5,
            "itens": [{"produtoId": 1, "quantidade": 1}],
            "formaPagamento": "MOCK",
        },
    },
}

CRIAR_PEDIDO: dict[str, Any] = {
    "summary": "Criar pedido",
    "description": (
        "**Perfil:** CLIENTE e ATENDENTE (só a própria unidade).\n\n"
        "Cria o pedido em `AGUARDANDO_PAGAMENTO`, já baixa o estoque dos itens (RN04) e grava "
        "o preço de cada produto no momento. Preço, status e total não são enviados (campos a "
        "mais dão 422). Canal por perfil (RN26): CLIENTE usa `APP`, `TOTEM`, `PICKUP` ou "
        "`WEB` e o cliente vem do token; ATENDENTE usa `BALCAO` e pode informar `clienteId` "
        "(sem ele o pedido não acumula pontos). Cada produto aparece uma vez em `itens`. "
        "Produto não oferecido na unidade ou inativo: 409 "
        "`PRODUTO_INDISPONIVEL_NA_UNIDADE` (RN03); saldo insuficiente: 409 "
        "`ESTOQUE_INSUFICIENTE`. Unidade, produto ou `clienteId` inexistente (ou de um usuário "
        "que não é cliente ativo): 404. A criação fica na auditoria."
    ),
    "responses": {
        **documentar_sucesso(
            HTTPStatus.CREATED,
            "Pedido criado",
            {
                "totem": {
                    "pedidoId": 9001,
                    "clienteId": 5,
                    "canalPedido": "TOTEM",
                    "unidadeId": 2,
                    "status": "AGUARDANDO_PAGAMENTO",
                    "subtotal": 129.7,
                    "desconto": 0,
                    "total": 129.7,
                    "itens": [
                        {"produtoId": 101, "quantidade": 2, "precoUnitario": 39.9},
                        {"produtoId": 305, "quantidade": 1, "precoUnitario": 49.9},
                    ],
                    "createdAt": "2026-02-05T12:00:00Z",
                }
            },
        ),
        **documentar_erros(
            "/pedidos",
            JSON_MALFORMADO,
            TOKEN_AUSENTE,
            perfil_sem_permissao(Perfil.COZINHA),
            UNIDADE_INEXISTENTE,
            ExemploErro(
                HTTPStatus.CONFLICT,
                EstoqueInsuficiente.codigo,
                MENSAGEM_ESTOQUE_INSUFICIENTE,
                (("itens[0].quantidade", "Disponível: 1"),),
            ),
            ExemploErro(
                HTTPStatus.CONFLICT,
                ProdutoIndisponivelNaUnidade.codigo,
                "Produto indisponível na unidade 2",
                (("itens[0].produtoId", "Indisponível na unidade 2"),),
            ),
            validacao_falhou("canalPedido", "Canal BALCAO não permitido para o perfil CLIENTE"),
        ),
    },
}

EXEMPLOS_CANAL_PEDIDO = {"app": {"summary": "Pedidos do aplicativo", "value": "APP"}}
EXEMPLOS_STATUS_PEDIDO = {
    "aguardando": {"summary": "Aguardando pagamento", "value": "AGUARDANDO_PAGAMENTO"}
}

PEDIDO_AGUARDANDO = {
    "pedidoId": 9002,
    "clienteId": 5,
    "canalPedido": "APP",
    "unidadeId": 1,
    "status": "AGUARDANDO_PAGAMENTO",
    "subtotal": 47.7,
    "desconto": 0,
    "total": 47.7,
    "createdAt": "2026-02-05T12:30:00Z",
}

LISTAR_PEDIDOS: dict[str, Any] = {
    "summary": "Listar pedidos",
    "description": (
        "**Perfil:** autenticado. CLIENTE vê só os próprios pedidos; ATENDENTE, COZINHA e "
        "GERENTE, os da própria unidade (RN23); ADMIN vê todos.\n\n"
        "Resumo dos pedidos, mais recentes primeiro, paginado. Filtros opcionais: "
        "`canalPedido` e `status`. Exemplo: "
        "`GET /pedidos?canalPedido=APP&status=AGUARDANDO_PAGAMENTO`."
    ),
    "responses": {
        **documentar_sucesso(
            HTTPStatus.OK,
            "Página de pedidos",
            {
                "app_aguardando": {
                    "dados": [PEDIDO_AGUARDANDO],
                    "paginacao": {"page": 1, "limit": 10, "total": 1, "totalPaginas": 1},
                }
            },
        ),
        **documentar_erros(
            "/pedidos",
            TOKEN_AUSENTE,
            validacao_falhou(
                "status",
                "Deve ser um destes valores: 'AGUARDANDO_PAGAMENTO', 'EM_PREPARO', 'PRONTO', "
                "'ENTREGUE' ou 'CANCELADO'",
            ),
        ),
    },
}

PEDIDO_EM_PREPARO = {
    **PEDIDO_AGUARDANDO,
    "status": "EM_PREPARO",
    "itens": [
        {"produtoId": 1, "quantidade": 2, "precoUnitario": 18.9},
        {"produtoId": 4, "quantidade": 1, "precoUnitario": 9.9},
    ],
    "motivoCancelamento": None,
    "cliente": {"id": 5, "nome": "Maria Cliente"},
    "ultimoPagamento": {
        "pagamentoId": 31,
        "status": "APROVADO",
        "valor": 47.7,
        "createdAt": "2026-02-05T12:31:00Z",
    },
    "updatedAt": "2026-02-05T12:31:00Z",
}

CONSULTAR_PEDIDO: dict[str, Any] = {
    "summary": "Consultar pedido",
    "description": (
        "**Perfil:** autenticado. CLIENTE só o próprio pedido (o de outro cliente responde "
        "404, RN22); ATENDENTE, COZINHA e GERENTE só pedidos da própria unidade (403, RN23); "
        "ADMIN qualquer um.\n\n"
        "Pedido com itens, cliente (`id` e `nome`; nulo no balcão sem cadastro) e o último "
        "pagamento. Quando um funcionário consulta um pedido com cliente, o acesso aos dados "
        "pessoais fica na auditoria (RN21)."
    ),
    "responses": {
        **documentar_sucesso(HTTPStatus.OK, "Pedido", {"pago": PEDIDO_EM_PREPARO}),
        **documentar_erros("/pedidos/9002", TOKEN_AUSENTE, sem_acesso_a_unidade(1)),
        **documentar_erros("/pedidos/99", PEDIDO_INEXISTENTE),
        **documentar_erros("/pedidos/abc", ID_NAO_INTEIRO),
    },
}

EXEMPLOS_ALTERAR_STATUS = {
    "pronto": {"summary": "Cozinha marca o pedido como pronto", "value": {"status": "PRONTO"}}
}

ALTERAR_STATUS: dict[str, Any] = {
    "summary": "Alterar o status do pedido",
    "description": (
        "**Perfil:** COZINHA, ATENDENTE e GERENTE (só pedidos da própria unidade) e ADMIN, "
        "conforme o status.\n\n"
        "Avança o pedido no ciclo de vida (RN10): `PRONTO` a partir de `EM_PREPARO` (COZINHA, "
        "GERENTE, ADMIN) e `ENTREGUE` a partir de `PRONTO` (ATENDENTE, GERENTE, ADMIN). "
        "`EM_PREPARO` só vem do pagamento aprovado e `CANCELADO` só do cancelamento; enviados "
        "aqui, dão 422. Transição fora do ciclo: 409 `TRANSICAO_STATUS_INVALIDA`. A mudança "
        "fica na auditoria."
    ),
    "responses": {
        **documentar_sucesso(
            HTTPStatus.OK,
            "Status alterado",
            {
                "pronto": {
                    "pedidoId": 9002,
                    "statusAnterior": "EM_PREPARO",
                    "status": "PRONTO",
                    "updatedAt": "2026-02-05T12:45:00Z",
                }
            },
        ),
        **documentar_erros(
            "/pedidos/9002/status",
            JSON_MALFORMADO,
            TOKEN_AUSENTE,
            ExemploErro(
                HTTPStatus.FORBIDDEN,
                AcessoNegado.codigo,
                "Perfil ATENDENTE não pode marcar pedido como PRONTO",
            ),
            ExemploErro(
                HTTPStatus.CONFLICT,
                TransicaoStatusInvalida.codigo,
                "Pedido em AGUARDANDO_PAGAMENTO não pode passar para PRONTO",
            ),
            validacao_falhou("status", "Deve ser um destes valores: 'PRONTO' ou 'ENTREGUE'"),
        ),
        **documentar_erros("/pedidos/99/status", PEDIDO_INEXISTENTE),
    },
}

MOTIVO_EXEMPLO = "Cliente desistiu da compra"
EXEMPLOS_CANCELAR_PEDIDO = {
    "desistencia": {
        "summary": "Cancelamento a pedido do cliente",
        "value": {"motivo": MOTIVO_EXEMPLO},
    }
}

CANCELAR_PEDIDO: dict[str, Any] = {
    "summary": "Cancelar pedido",
    "description": (
        "**Perfil:** CLIENTE (só o próprio pedido), ATENDENTE e GERENTE (só pedidos da "
        "própria unidade) e ADMIN (RN16).\n\n"
        "Só pedido `AGUARDANDO_PAGAMENTO` pode ser cancelado; nos demais status a resposta é "
        "409 `TRANSICAO_STATUS_INVALIDA`, porque pedido pago não tem estorno pela API. O "
        "cancelamento devolve o estoque dos itens (RN07) e os pontos resgatados no pedido e "
        "fica na auditoria."
    ),
    "responses": {
        **documentar_sucesso(
            HTTPStatus.OK,
            "Pedido cancelado",
            {
                "desistencia": {
                    "pedidoId": 9001,
                    "status": "CANCELADO",
                    "motivoCancelamento": MOTIVO_EXEMPLO,
                }
            },
        ),
        **documentar_erros(
            "/pedidos/9002/cancelamento",
            JSON_MALFORMADO,
            TOKEN_AUSENTE,
            perfil_sem_permissao(Perfil.COZINHA),
            ExemploErro(
                HTTPStatus.CONFLICT,
                TransicaoStatusInvalida.codigo,
                "Pedido em EM_PREPARO não pode passar para CANCELADO",
            ),
            validacao_falhou("motivo", "Campo obrigatório"),
        ),
        **documentar_erros("/pedidos/99/cancelamento", PEDIDO_INEXISTENTE),
    },
}
