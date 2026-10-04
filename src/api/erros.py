from datetime import UTC, datetime
from http import HTTPStatus

from fastapi.responses import JSONResponse

from src.api.schemas.base import EsquemaSaida
from src.domain.erros.erros import (
    AcessoNegado,
    ConsentimentoAusente,
    CredenciaisInvalidas,
    DadosInvalidos,
    EmailJaCadastrado,
    ErroDominio,
    EstoqueInsuficiente,
    GatewayPagamentoIndisponivel,
    NaoAutenticado,
    PagamentoNaoPermitido,
    ProdutoIndisponivelNaUnidade,
    RecursoNaoEncontrado,
    SaldoPontosInsuficiente,
    TransicaoStatusInvalida,
)
from src.infrastructure.logging.logger import request_id_atual

ERRO_INTERNO = "ERRO_INTERNO"
MENSAGEM_ERRO_INTERNO = "Erro interno no servidor"
JSON_INVALIDO = "JSON_INVALIDO"
MENSAGEM_JSON_INVALIDO = "Corpo da requisição não é um JSON válido"
VALIDACAO_FALHOU = "VALIDACAO_FALHOU"
MENSAGEM_VALIDACAO_FALHOU = "Dados de entrada inválidos"
RECURSO_NAO_ENCONTRADO = "RECURSO_NAO_ENCONTRADO"
# Fora do catálogo da seção 8: o Starlette devolve 405 e 413 e o formato padrão vale para eles.
METODO_NAO_PERMITIDO = "METODO_NAO_PERMITIDO"
CORPO_MUITO_GRANDE = "CORPO_MUITO_GRANDE"

STATUS_POR_ERRO: dict[type[ErroDominio], HTTPStatus] = {
    CredenciaisInvalidas: HTTPStatus.UNAUTHORIZED,
    NaoAutenticado: HTTPStatus.UNAUTHORIZED,
    AcessoNegado: HTTPStatus.FORBIDDEN,
    RecursoNaoEncontrado: HTTPStatus.NOT_FOUND,
    EmailJaCadastrado: HTTPStatus.CONFLICT,
    EstoqueInsuficiente: HTTPStatus.CONFLICT,
    ProdutoIndisponivelNaUnidade: HTTPStatus.CONFLICT,
    TransicaoStatusInvalida: HTTPStatus.CONFLICT,
    PagamentoNaoPermitido: HTTPStatus.CONFLICT,
    ConsentimentoAusente: HTTPStatus.CONFLICT,
    SaldoPontosInsuficiente: HTTPStatus.CONFLICT,
    DadosInvalidos: HTTPStatus.UNPROCESSABLE_CONTENT,
    GatewayPagamentoIndisponivel: HTTPStatus.SERVICE_UNAVAILABLE,
}


class DetalheResposta(EsquemaSaida):
    field: str
    issue: str


class RespostaErro(EsquemaSaida):
    error: str
    message: str
    details: list[DetalheResposta]
    timestamp: datetime
    path: str
    request_id: str | None


def resposta_de_erro(
    status: HTTPStatus,
    codigo: str,
    mensagem: str,
    caminho: str,
    detalhes: list[DetalheResposta] | None = None,
) -> JSONResponse:
    corpo = RespostaErro(
        error=codigo,
        message=mensagem,
        details=detalhes or [],
        timestamp=datetime.now(UTC).replace(microsecond=0),
        path=caminho,
        request_id=request_id_atual.get(),
    )
    return JSONResponse(corpo.model_dump(mode="json", by_alias=True), status_code=status)
