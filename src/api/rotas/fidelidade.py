from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Body, Depends

from src.api.autenticacao import ClienteLogado
from src.api.dependencias import ConexaoBanco
from src.api.openapi import fidelidade as documentacao
from src.api.schemas.fidelidade import (
    NovoResgate,
    ResgateResposta,
    SaldoPontosResposta,
    TransacaoFidelidadeResposta,
)
from src.api.schemas.paginacao import Pagina, ParametrosPaginacao, obter_paginacao
from src.application.fidelidade.fidelidade import (
    consultar_saldo,
    listar_historico,
    resgatar_pontos,
)
from src.domain.fidelidade.fidelidade import calcular_valor_dos_pontos

roteador = APIRouter(prefix="/fidelidade", tags=["Fidelidade"])


@roteador.get("/saldo", **documentacao.CONSULTAR_SALDO_PONTOS)
def consultar_meu_saldo(cliente: ClienteLogado, conexao: ConexaoBanco) -> SaldoPontosResposta:
    saldo = consultar_saldo(conexao, cliente.id)
    return SaldoPontosResposta(
        saldo_pontos=saldo, valor_equivalente=calcular_valor_dos_pontos(saldo)
    )


@roteador.get("/historico", **documentacao.LISTAR_HISTORICO_PONTOS)
def listar_meu_historico(
    paginacao: Annotated[ParametrosPaginacao, Depends(obter_paginacao)],
    cliente: ClienteLogado,
    conexao: ConexaoBanco,
) -> Pagina[TransacaoFidelidadeResposta]:
    transacoes, total = listar_historico(conexao, cliente.id, paginacao.limit, paginacao.offset)
    return Pagina[TransacaoFidelidadeResposta].criar(
        [
            TransacaoFidelidadeResposta.model_validate(
                {**vars(transacao), "transacao_id": transacao.id}
            )
            for transacao in transacoes
        ],
        total,
        paginacao,
    )


@roteador.post("/resgates", status_code=HTTPStatus.CREATED, **documentacao.RESGATAR_PONTOS)
def resgatar_meus_pontos(
    novo: Annotated[NovoResgate, Body(openapi_examples=documentacao.EXEMPLOS_RESGATAR_PONTOS)],
    cliente: ClienteLogado,
    conexao: ConexaoBanco,
) -> ResgateResposta:
    pedido, saldo = resgatar_pontos(conexao, cliente, novo.pedido_id, novo.pontos)
    return ResgateResposta(
        pedido_id=pedido.id,
        pontos_resgatados=novo.pontos,
        desconto=pedido.desconto,
        total_atualizado=pedido.total,
        saldo_pontos=saldo,
    )
