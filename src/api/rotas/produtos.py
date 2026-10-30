from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Body, Depends

from src.api.autenticacao import AdminLogado, exigir_perfil
from src.api.dependencias import ConexaoBanco
from src.api.openapi import produtos as documentacao
from src.api.schemas.campos import IdDoRecurso
from src.api.schemas.paginacao import Pagina, ParametrosPaginacao, obter_paginacao
from src.api.schemas.produtos import AlteracaoProduto, NovoProduto, ProdutoResposta
from src.application.produtos.produtos import (
    atualizar_produto,
    cadastrar_produto,
    consultar_produto,
    desativar_produto,
    listar_produtos,
)
from src.domain.produto.produto import DadosProduto
from src.domain.usuario.usuario import Perfil

roteador = APIRouter(prefix="/produtos", tags=["Produtos"])


@roteador.get("", **documentacao.LISTAR_PRODUTOS)
def listar_produtos_da_rede(
    paginacao: Annotated[ParametrosPaginacao, Depends(obter_paginacao)],
    conexao: ConexaoBanco,
) -> Pagina[ProdutoResposta]:
    produtos, total = listar_produtos(conexao, paginacao.limit, paginacao.offset)
    return Pagina[ProdutoResposta].criar(
        [ProdutoResposta.model_validate(produto) for produto in produtos],
        total,
        paginacao,
    )


@roteador.get("/{id}", **documentacao.CONSULTAR_PRODUTO)
def consultar_produto_por_id(produto_id: IdDoRecurso, conexao: ConexaoBanco) -> ProdutoResposta:
    return ProdutoResposta.model_validate(consultar_produto(conexao, produto_id))


@roteador.post(
    "",
    status_code=HTTPStatus.CREATED,
    dependencies=[Depends(exigir_perfil(Perfil.ADMIN))],
    **documentacao.CADASTRAR_PRODUTO,
)
def cadastrar_novo_produto(
    novo: Annotated[NovoProduto, Body(openapi_examples=documentacao.EXEMPLOS_CADASTRAR_PRODUTO)],
    conexao: ConexaoBanco,
) -> ProdutoResposta:
    return ProdutoResposta.model_validate(
        cadastrar_produto(conexao, DadosProduto(**novo.model_dump()))
    )


@roteador.put("/{id}", **documentacao.ATUALIZAR_PRODUTO)
def atualizar_produto_existente(
    produto_id: IdDoRecurso,
    alteracao: Annotated[
        AlteracaoProduto, Body(openapi_examples=documentacao.EXEMPLOS_ATUALIZAR_PRODUTO)
    ],
    admin: AdminLogado,
    conexao: ConexaoBanco,
) -> ProdutoResposta:
    dados = DadosProduto(**alteracao.model_dump(exclude={"ativo"}))
    produto = atualizar_produto(conexao, admin.id, produto_id, dados, alteracao.ativo)
    return ProdutoResposta.model_validate(produto)


@roteador.delete("/{id}", status_code=HTTPStatus.NO_CONTENT, **documentacao.DESATIVAR_PRODUTO)
def desativar_produto_existente(
    produto_id: IdDoRecurso, admin: AdminLogado, conexao: ConexaoBanco
) -> None:
    desativar_produto(conexao, admin.id, produto_id)
