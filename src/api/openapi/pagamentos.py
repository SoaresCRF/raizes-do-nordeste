from http import HTTPStatus
from typing import Any

from src.api.erros import GATEWAY_PAGAMENTO_INDISPONIVEL
from src.api.openapi.pedidos import PAGAMENTO_NAO_PERMITIDO, PEDIDO_INEXISTENTE
from src.api.openapi.respostas import (
    JSON_MALFORMADO,
    TOKEN_AUSENTE,
    ExemploErro,
    documentar_erros,
    documentar_sucesso,
    perfil_sem_permissao,
    validacao_falhou,
)
from src.api.schemas.pagamentos import MENSAGEM_APROVADO, MENSAGEM_RECUSADO
from src.domain.usuario import Perfil
from src.infrastructure.gateway_mock import MOTIVO_RECUSA_SIMULADA

TRANSACAO_APROVADA = "MOCK-3b9f0c2a7d5e4f1a8c6b9d0e2f4a6c8e"
TRANSACAO_RECUSADA = "MOCK-9d1e7a3c5b0f4e2a8c6d1b3f5a7e9c0d"
PAYLOAD_APROVADO = {
    "transacaoId": TRANSACAO_APROVADA,
    "referencia": 9002,
    "valor": "47.70",
    "status": "APROVADO",
    "motivo": None,
}

EXEMPLOS_SOLICITAR_PAGAMENTO = {
    "pedido": {"summary": "Pagar o pedido 9002", "value": {"pedidoId": 9002}}
}

SOLICITAR_PAGAMENTO: dict[str, Any] = {
    "summary": "Pagar pedido",
    "description": (
        "**Perfil:** CLIENTE (só o próprio pedido) e ATENDENTE (só pedidos da própria "
        "unidade).\n\n"
        "Cobra o total do pedido no gateway simulado; nenhum pagamento real acontece (RN11). "
        "Só pedido `AGUARDANDO_PAGAMENTO` aceita pagamento (409 `PAGAMENTO_NAO_PERMITIDO`, "
        "RN14). Aprovado: o pedido vai para `EM_PREPARO` e o cliente com consentimento ganha 1 "
        "ponto por real (RN18). Recusado: o pedido continua aguardando e aceita nova "
        "tentativa. Aprovado e recusado devolvem 201, porque o pagamento foi registrado. Falha "
        "do gateway: o pagamento fica registrado como `ERRO`, o pedido não muda e a "
        "resposta é 503 (RN15). O header `X-Simular-Resultado` escolhe o resultado do mock. O "
        "pagamento fica na auditoria."
    ),
    "responses": {
        **documentar_sucesso(
            HTTPStatus.CREATED,
            "Pagamento registrado (aprovado ou recusado)",
            {
                "aprovado": {
                    "pagamentoId": 31,
                    "pedidoId": 9002,
                    "status": "APROVADO",
                    "valor": 47.7,
                    "transacaoExternaId": TRANSACAO_APROVADA,
                    "mensagem": MENSAGEM_APROVADO,
                    "statusPedido": "EM_PREPARO",
                    "payloadGateway": PAYLOAD_APROVADO,
                },
                "recusado": {
                    "pagamentoId": 30,
                    "pedidoId": 9002,
                    "status": "RECUSADO",
                    "valor": 47.7,
                    "transacaoExternaId": TRANSACAO_RECUSADA,
                    "mensagem": MENSAGEM_RECUSADO.format(motivo=MOTIVO_RECUSA_SIMULADA),
                    "statusPedido": "AGUARDANDO_PAGAMENTO",
                    "payloadGateway": {
                        "transacaoId": TRANSACAO_RECUSADA,
                        "referencia": 9002,
                        "valor": "47.70",
                        "status": "RECUSADO",
                        "motivo": MOTIVO_RECUSA_SIMULADA,
                    },
                },
            },
        ),
        **documentar_erros(
            "/pagamentos",
            JSON_MALFORMADO,
            TOKEN_AUSENTE,
            perfil_sem_permissao(Perfil.COZINHA),
            PEDIDO_INEXISTENTE,
            PAGAMENTO_NAO_PERMITIDO,
            validacao_falhou("pedidoId", "Campo obrigatório"),
            ExemploErro(
                HTTPStatus.SERVICE_UNAVAILABLE,
                GATEWAY_PAGAMENTO_INDISPONIVEL,
                "Gateway de pagamento indisponível; pagamento 32 registrado com erro",
            ),
        ),
    },
}
