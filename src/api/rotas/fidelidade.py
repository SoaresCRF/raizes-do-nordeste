from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.autenticacao import ClienteLogado
from src.api.dependencias import ConexaoBanco
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
from src.domain.fidelidade.fidelidade import valor_dos_pontos

roteador = APIRouter(prefix="/fidelidade", tags=["Fidelidade"])


@roteador.get("/saldo")
def consultar_meu_saldo(cliente: ClienteLogado, conexao: ConexaoBanco) -> SaldoPontosResposta:
    saldo = consultar_saldo(conexao, cliente.id)
    return SaldoPontosResposta(saldo_pontos=saldo, valor_equivalente=valor_dos_pontos(saldo))


@roteador.get("/historico")
def listar_meu_historico(
    paginacao: Annotated[ParametrosPaginacao, Depends(obter_paginacao)],
    cliente: ClienteLogado,
    conexao: ConexaoBanco,
) -> Pagina[TransacaoFidelidadeResposta]:
    transacoes, total = listar_historico(conexao, cliente.id, paginacao.limit, paginacao.offset)
    return Pagina[TransacaoFidelidadeResposta].criar(
        [
            TransacaoFidelidadeResposta(
                transacao_id=transacao.id,
                tipo=transacao.tipo,
                pontos=transacao.pontos,
                pedido_id=transacao.pedido_id,
                created_at=transacao.created_at,
            )
            for transacao in transacoes
        ],
        total,
        paginacao,
    )


@roteador.post("/resgates", status_code=HTTPStatus.CREATED)
def resgatar_meus_pontos(
    novo: NovoResgate, cliente: ClienteLogado, conexao: ConexaoBanco
) -> ResgateResposta:
    pedido, saldo = resgatar_pontos(conexao, cliente, novo.pedido_id, novo.pontos)
    return ResgateResposta(
        pedido_id=pedido.id,
        pontos_resgatados=novo.pontos,
        desconto=pedido.desconto,
        total_atualizado=pedido.total,
        saldo_pontos=saldo,
    )
