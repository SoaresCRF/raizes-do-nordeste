from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

from src.api.autenticacao import MENSAGEM_PERFIL_SEM_PERMISSAO, MENSAGEM_TOKEN_AUSENTE
from src.api.erros import (
    JSON_INVALIDO,
    MENSAGEM_JSON_INVALIDO,
    RespostaErro,
)
from src.domain.erros.erros import (
    MENSAGEM_DADOS_INVALIDOS,
    AcessoNegado,
    DadosInvalidos,
    NaoAutenticado,
    RecursoNaoEncontrado,
)
from src.domain.usuario.usuario import MENSAGEM_SEM_ACESSO_A_UNIDADE, Perfil

TIMESTAMP_EXEMPLO = "2026-02-05T12:00:00Z"
REQUEST_ID_EXEMPLO = "3f2c9a4e-7b1d-4c2a-9e8f-5d6c7b8a9e0f"

DESCRICAO_POR_STATUS = {
    HTTPStatus.BAD_REQUEST: "Corpo da requisição não é um JSON válido",
    HTTPStatus.UNAUTHORIZED: "Não autenticado",
    HTTPStatus.FORBIDDEN: "Perfil ou unidade sem permissão",
    HTTPStatus.NOT_FOUND: "Recurso não encontrado",
    HTTPStatus.CONFLICT: "Conflito com o estado atual do recurso",
    HTTPStatus.UNPROCESSABLE_CONTENT: "Dados de entrada inválidos",
    HTTPStatus.SERVICE_UNAVAILABLE: "Gateway de pagamento indisponível",
}


@dataclass(frozen=True)
class ExemploErro:
    status: HTTPStatus
    codigo: str
    mensagem: str
    detalhes: tuple[tuple[str, str], ...] = ()


JSON_MALFORMADO = ExemploErro(HTTPStatus.BAD_REQUEST, JSON_INVALIDO, MENSAGEM_JSON_INVALIDO)
TOKEN_AUSENTE = ExemploErro(HTTPStatus.UNAUTHORIZED, NaoAutenticado.codigo, MENSAGEM_TOKEN_AUSENTE)


def perfil_sem_permissao(perfil: Perfil) -> ExemploErro:
    return ExemploErro(
        HTTPStatus.FORBIDDEN,
        AcessoNegado.codigo,
        MENSAGEM_PERFIL_SEM_PERMISSAO.format(perfil=perfil),
    )


def sem_acesso_a_unidade(unidade_id: int) -> ExemploErro:
    return ExemploErro(
        HTTPStatus.FORBIDDEN,
        AcessoNegado.codigo,
        MENSAGEM_SEM_ACESSO_A_UNIDADE.format(unidade_id=unidade_id),
    )


def nao_encontrado(mensagem: str) -> ExemploErro:
    return ExemploErro(HTTPStatus.NOT_FOUND, RecursoNaoEncontrado.codigo, mensagem)


def validacao_falhou(campo: str, problema: str) -> ExemploErro:
    return ExemploErro(
        HTTPStatus.UNPROCESSABLE_CONTENT,
        DadosInvalidos.codigo,
        MENSAGEM_DADOS_INVALIDOS,
        ((campo, problema),),
    )


UNIDADE_INEXISTENTE = nao_encontrado("Unidade 99 não encontrada")
ID_NAO_INTEIRO = validacao_falhou("id", "Deve ser um número inteiro")


def documentar_erros(caminho: str, *exemplos: ExemploErro) -> dict[int, dict[str, Any]]:
    respostas: dict[int, dict[str, Any]] = {}
    for exemplo in exemplos:
        resposta = respostas.setdefault(
            int(exemplo.status),
            {
                "model": RespostaErro,
                "description": DESCRICAO_POR_STATUS[exemplo.status],
                "content": {"application/json": {"examples": {}}},
            },
        )
        exemplos_do_status = resposta["content"]["application/json"]["examples"]
        if exemplo.codigo in exemplos_do_status:
            raise ValueError(f"Exemplo {exemplo.codigo} repetido em {caminho}")
        exemplos_do_status[exemplo.codigo] = {
            "summary": exemplo.mensagem,
            "value": {
                "error": exemplo.codigo,
                "message": exemplo.mensagem,
                "details": [
                    {"field": campo, "issue": problema} for campo, problema in exemplo.detalhes
                ],
                "timestamp": TIMESTAMP_EXEMPLO,
                "path": caminho,
                "requestId": REQUEST_ID_EXEMPLO,
            },
        }
    return respostas


def documentar_sucesso(
    status: HTTPStatus, descricao: str, exemplos: dict[str, Any]
) -> dict[int, dict[str, Any]]:
    return {
        int(status): {
            "description": descricao,
            "content": {
                "application/json": {
                    "examples": {nome: {"value": valor} for nome, valor in exemplos.items()}
                }
            },
        }
    }


def documentar_sem_conteudo(descricao: str) -> dict[int, dict[str, Any]]:
    return {int(HTTPStatus.NO_CONTENT): {"description": descricao}}
