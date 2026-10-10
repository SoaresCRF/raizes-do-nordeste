from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query

from src.api.autenticacao import FuncionarioLogado, GestorLogado
from src.api.dependencias import ConexaoBanco
from src.api.openapi import estoque as documentacao
from src.api.schemas.campos import ID_MAXIMO
from src.api.schemas.estoque import (
    MovimentacaoHistoricoResposta,
    MovimentacaoResposta,
    NovaMovimentacao,
    SaldoResposta,
)
from src.api.schemas.paginacao import Pagina, ParametrosPaginacao, obter_paginacao
from src.application.estoque.estoque import (
    consultar_saldos,
    listar_movimentacoes,
    movimentar_estoque,
)
from src.domain.estoque.estoque import DadosMovimentacao

roteador = APIRouter(prefix="/estoque", tags=["Estoque"])

UnidadeDoFiltro = Annotated[int, Query(alias="unidadeId", gt=0, le=ID_MAXIMO)]


@roteador.get("", **documentacao.CONSULTAR_SALDOS)
def consultar_saldos_da_unidade(
    unidade_id: UnidadeDoFiltro,
    paginacao: Annotated[ParametrosPaginacao, Depends(obter_paginacao)],
    usuario: FuncionarioLogado,
    conexao: ConexaoBanco,
) -> Pagina[SaldoResposta]:
    saldos, total = consultar_saldos(
        conexao, usuario, unidade_id, paginacao.limit, paginacao.offset
    )
    return Pagina[SaldoResposta].criar(
        [SaldoResposta.model_validate(saldo, from_attributes=True) for saldo in saldos],
        total,
        paginacao,
    )


@roteador.post("/movimentacoes", status_code=HTTPStatus.CREATED, **documentacao.MOVIMENTAR_ESTOQUE)
def movimentar_estoque_da_unidade(
    nova: Annotated[
        NovaMovimentacao, Body(openapi_examples=documentacao.EXEMPLOS_MOVIMENTAR_ESTOQUE)
    ],
    usuario: GestorLogado,
    conexao: ConexaoBanco,
) -> MovimentacaoResposta:
    dados = DadosMovimentacao(
        unidade_id=nova.unidade_id,
        produto_id=nova.produto_id,
        tipo=nova.tipo,
        quantidade=nova.quantidade,
        motivo=nova.motivo,
    )
    movimentacao, saldo_atual = movimentar_estoque(conexao, usuario, dados)
    return MovimentacaoResposta(
        movimentacao_id=movimentacao.id,
        tipo=movimentacao.tipo,
        quantidade=movimentacao.quantidade,
        saldo_atual=saldo_atual,
    )


@roteador.get("/movimentacoes", **documentacao.LISTAR_MOVIMENTACOES)
def listar_movimentacoes_da_unidade(
    unidade_id: UnidadeDoFiltro,
    paginacao: Annotated[ParametrosPaginacao, Depends(obter_paginacao)],
    usuario: GestorLogado,
    conexao: ConexaoBanco,
    produto_id: Annotated[int | None, Query(alias="produtoId", gt=0, le=ID_MAXIMO)] = None,
) -> Pagina[MovimentacaoHistoricoResposta]:
    itens, total = listar_movimentacoes(
        conexao, usuario, unidade_id, produto_id, paginacao.limit, paginacao.offset
    )
    return Pagina[MovimentacaoHistoricoResposta].criar(
        [
            MovimentacaoHistoricoResposta.model_validate(item, from_attributes=True)
            for item in itens
        ],
        total,
        paginacao,
    )
