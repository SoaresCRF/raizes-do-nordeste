from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Body, Depends

from src.api.autenticacao import AdminLogado, exigir_perfil
from src.api.dependencias import ConexaoBanco
from src.api.openapi import unidades as documentacao
from src.api.schemas.campos import IdDoRecurso
from src.api.schemas.paginacao import Pagina, ParametrosPaginacao, obter_paginacao
from src.api.schemas.produtos import ItemCardapioResposta
from src.api.schemas.unidades import (
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
) -> Pagina[UnidadeResposta]:
    unidades, total = listar_unidades(conexao, paginacao.limit, paginacao.offset)
    return Pagina[UnidadeResposta].criar(
        [UnidadeResposta.model_validate(unidade) for unidade in unidades],
        total,
        paginacao,
    )


@roteador.get("/{id}", **documentacao.CONSULTAR_UNIDADE)
def consultar_unidade_por_id(unidade_id: IdDoRecurso, conexao: ConexaoBanco) -> UnidadeResposta:
    return UnidadeResposta.model_validate(consultar_unidade(conexao, unidade_id))


@roteador.post("", status_code=HTTPStatus.CREATED, **documentacao.CADASTRAR_UNIDADE)
def cadastrar_nova_unidade(
    nova: Annotated[NovaUnidade, Body(openapi_examples=documentacao.EXEMPLOS_CADASTRAR_UNIDADE)],
    admin: AdminLogado,
    conexao: ConexaoBanco,
) -> UnidadeResposta:
    return UnidadeResposta.model_validate(
        cadastrar_unidade(conexao, admin.id, DadosUnidade(**nova.model_dump()))
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
    dados = DadosUnidade(**alteracao.model_dump(exclude={"ativa"}))
    unidade = atualizar_unidade(conexao, unidade_id, dados, alteracao.ativa)
    return UnidadeResposta.model_validate(unidade)


@roteador.get("/{id}/cardapio", **documentacao.CONSULTAR_CARDAPIO)
def consultar_cardapio_da_unidade(
    unidade_id: IdDoRecurso,
    paginacao: Annotated[ParametrosPaginacao, Depends(obter_paginacao)],
    conexao: ConexaoBanco,
) -> Pagina[ItemCardapioResposta]:
    itens, total = consultar_cardapio(conexao, unidade_id, paginacao.limit, paginacao.offset)
    return Pagina[ItemCardapioResposta].criar(
        [ItemCardapioResposta.model_validate(item) for item in itens],
        total,
        paginacao,
    )
