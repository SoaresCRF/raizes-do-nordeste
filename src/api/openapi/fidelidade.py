from http import HTTPStatus
from typing import Any

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
from src.domain.erros.erros import ConsentimentoAusente, SaldoPontosInsuficiente
from src.domain.usuario.usuario import Perfil

ATENDENTE_SEM_PERMISSAO = perfil_sem_permissao(Perfil.ATENDENTE)

CONSULTAR_SALDO_PONTOS: dict[str, Any] = {
    "summary": "Consultar saldo de pontos",
    "description": (
        "**Perfil:** CLIENTE.\n\n"
        "Saldo de pontos do próprio cliente e quanto ele vale em desconto: cada 100 pontos "
        "valem R$ 5,00 (RN19)."
    ),
    "responses": {
        **documentar_sucesso(
            HTTPStatus.OK,
            "Saldo de pontos",
            {"saldo": {"saldoPontos": 247, "valorEquivalente": 10}},
        ),
        **documentar_erros("/fidelidade/saldo", TOKEN_AUSENTE, ATENDENTE_SEM_PERMISSAO),
    },
}

LISTAR_HISTORICO_PONTOS: dict[str, Any] = {
    "summary": "Listar histórico de pontos",
    "description": (
        "**Perfil:** CLIENTE.\n\n"
        "Transações de pontos do próprio cliente, mais recentes primeiro, paginadas: "
        "`ACUMULO` (pagamento aprovado), `RESGATE` (pontos negativos) e `ESTORNO` (pontos "
        "resgatados que voltam quando o pedido é cancelado)."
    ),
    "responses": {
        **documentar_sucesso(
            HTTPStatus.OK,
            "Página de transações",
            {
                "historico": {
                    "dados": [
                        {
                            "transacaoId": 5,
                            "tipo": "RESGATE",
                            "pontos": -100,
                            "pedidoId": 9003,
                            "createdAt": "2026-02-05T13:00:00Z",
                        },
                        {
                            "transacaoId": 4,
                            "tipo": "ACUMULO",
                            "pontos": 47,
                            "pedidoId": 9002,
                            "createdAt": "2026-02-05T12:31:00Z",
                        },
                    ],
                    "paginacao": {"page": 1, "limit": 10, "total": 2, "totalPaginas": 1},
                }
            },
        ),
        **documentar_erros(
            "/fidelidade/historico",
            TOKEN_AUSENTE,
            ATENDENTE_SEM_PERMISSAO,
            validacao_falhou("page", "Deve ser maior ou igual a 1"),
        ),
    },
}

EXEMPLOS_RESGATAR_PONTOS = {
    "cem_pontos": {
        "summary": "Trocar 100 pontos por R$ 5,00 de desconto",
        "value": {"pedidoId": 9003, "pontos": 100},
    }
}

RESGATAR_PONTOS: dict[str, Any] = {
    "summary": "Resgatar pontos",
    "description": (
        "**Perfil:** CLIENTE.\n\n"
        "Troca pontos por desconto num pedido próprio em `AGUARDANDO_PAGAMENTO` (RN19): "
        "`pontos` em múltiplos de 100, cada 100 valendo R$ 5,00. Exige consentimento "
        "`FIDELIDADE` vigente (409 `CONSENTIMENTO_AUSENTE`, RN17) e saldo suficiente (409 "
        "`SALDO_PONTOS_INSUFICIENTE`). O desconto tem de ser menor que o total do pedido "
        "(422). O resgate fica na auditoria e é estornado se o pedido for cancelado."
    ),
    "responses": {
        **documentar_sucesso(
            HTTPStatus.CREATED,
            "Pontos resgatados",
            {
                "cem_pontos": {
                    "pedidoId": 9003,
                    "pontosResgatados": 100,
                    "desconto": 5,
                    "totalAtualizado": 42.7,
                    "saldoPontos": 147,
                }
            },
        ),
        **documentar_erros(
            "/fidelidade/resgates",
            JSON_MALFORMADO,
            TOKEN_AUSENTE,
            ATENDENTE_SEM_PERMISSAO,
            PEDIDO_INEXISTENTE,
            ExemploErro(
                HTTPStatus.CONFLICT,
                ConsentimentoAusente.codigo,
                "Cliente 7 sem consentimento FIDELIDADE ativo",
            ),
            ExemploErro(
                HTTPStatus.CONFLICT,
                SaldoPontosInsuficiente.codigo,
                "Saldo de 47 pontos não cobre o resgate de 100",
                (("pontos", "Saldo disponível: 47"),),
            ),
            PAGAMENTO_NAO_PERMITIDO,
            validacao_falhou("pontos", "Deve ser múltiplo de 100"),
        ),
    },
}
