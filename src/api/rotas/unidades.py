from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query
from pydantic import StringConstraints

from src.api.autenticacao import AdminLogado, exigir_perfil
from src.api.dependencias import ConexaoBanco
from src.api.openapi import unidades as documentacao
from src.api.schemas.campos import IdDoRecurso, SemCaractereNulo
from src.api.schemas.paginacao import Pagina, ParametrosPaginacao, obter_paginacao
from src.api.schemas.produtos import ItemCardapioResposta
from src.api.schemas.unidades import (
    TAMANHO_MAXIMO_REGIAO,
    AlteracaoUnidade,
    NovaUnidade,
    UnidadeResposta,
)
from src.application.produtos.produtos import consultar_cardapio
from src.application.unidades.unidades import (
    atualizar_unidade,
    cadastrar_unidade,
    consultar_unidade,
    listar_unidades,
)
from src.domain.unidade.unidade import DadosUnidade
from src.domain.usuario.usuario import Perfil

roteador = APIRouter(prefix="/unidades", tags=["Unidades"])


@roteador.get("", **documentacao.LISTAR_UNIDADES)
def listar_unidades_da_rede(
    paginacao: Annotated[ParametrosPaginacao, Depends(obter_paginacao)],
    conexao: ConexaoBanco,
    regiao: Annotated[
        str | None,
        StringConstraints(min_length=1, max_length=TAMANHO_MAXIMO_REGIAO),
        SemCaractereNulo,
        Query(),
    ] = None,
) -> Pagina[UnidadeResposta]:
    unidades, total = listar_unidades(conexao, regiao, paginacao.limit, paginacao.offset)
    return Pagina[UnidadeResposta].criar(
        [UnidadeResposta.model_validate(unidade, from_attributes=True) for unidade in unidades],
        total,
        paginacao,
    )


@roteador.get("/{id}", **documentacao.CONSULTAR_UNIDADE)
def consultar_unidade_por_id(unidade_id: IdDoRecurso, conexao: ConexaoBanco) -> UnidadeResposta:
    return UnidadeResposta.model_validate(
        consultar_unidade(conexao, unidade_id), from_attributes=True
    )


@roteador.post("", status_code=HTTPStatus.CREATED, **documentacao.CADASTRAR_UNIDADE)
def cadastrar_nova_unidade(
    nova: Annotated[NovaUnidade, Body(openapi_examples=documentacao.EXEMPLOS_CADASTRAR_UNIDADE)],
    admin: AdminLogado,
    conexao: ConexaoBanco,
) -> UnidadeResposta:
    dados = DadosUnidade(
        nome=nova.nome, cidade=nova.cidade, uf=nova.uf, regiao=nova.regiao, tipo=nova.tipo
    )
    return UnidadeResposta.model_validate(
        cadastrar_unidade(conexao, admin.id, dados), from_attributes=True
    )


@roteador.put(
    "/{id}",
    dependencies=[Depends(exigir_perfil(Perfil.ADMIN))],
    **documentacao.ATUALIZAR_UNIDADE,
)
def atualizar_unidade_existente(
    unidade_id: IdDoRecurso,
    alteracao: Annotated[
        AlteracaoUnidade, Body(openapi_examples=documentacao.EXEMPLOS_ATUALIZAR_UNIDADE)
    ],
    conexao: ConexaoBanco,
) -> UnidadeResposta:
    dados = DadosUnidade(
        nome=alteracao.nome,
        cidade=alteracao.cidade,
        uf=alteracao.uf,
        regiao=alteracao.regiao,
        tipo=alteracao.tipo,
    )
    return UnidadeResposta.model_validate(
        atualizar_unidade(conexao, unidade_id, dados, alteracao.ativa), from_attributes=True
    )


@roteador.get("/{id}/cardapio", **documentacao.CONSULTAR_CARDAPIO)
def consultar_cardapio_da_unidade(
    unidade_id: IdDoRecurso,
    paginacao: Annotated[ParametrosPaginacao, Depends(obter_paginacao)],
    conexao: ConexaoBanco,
) -> Pagina[ItemCardapioResposta]:
    itens, total = consultar_cardapio(conexao, unidade_id, paginacao.limit, paginacao.offset)
    return Pagina[ItemCardapioResposta].criar(
        [ItemCardapioResposta.model_validate(item, from_attributes=True) for item in itens],
        total,
        paginacao,
    )
