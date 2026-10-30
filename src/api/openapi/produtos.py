from http import HTTPStatus
from typing import Any

from src.api.openapi.respostas import (
    ID_NAO_INTEIRO,
    JSON_MALFORMADO,
    TOKEN_AUSENTE,
    documentar_erros,
    documentar_sem_conteudo,
    documentar_sucesso,
    nao_encontrado,
    perfil_sem_permissao,
    validacao_falhou,
)
from src.domain.usuario.usuario import Perfil

TAPIOCA = {
    "id": 1,
    "nome": "Tapioca",
    "descricao": "Tapioca de queijo coalho",
    "preco": 18.9,
    "ativo": True,
}
CUSCUZ = {
    "id": 2,
    "nome": "Cuscuz recheado",
    "descricao": "Cuscuz de milho recheado com carne de sol",
    "preco": 24.9,
    "ativo": True,
}
PRODUTO_INEXISTENTE = nao_encontrado("Produto 99 não encontrado")
SEM_PERMISSAO = perfil_sem_permissao(Perfil.GERENTE)

LISTAR_PRODUTOS: dict[str, Any] = {
    "summary": "Listar produtos",
    "description": (
        "**Perfil:** público.\n\n"
        "Catálogo da rede, inclusive produtos inativos, em ordem de id, paginado (o que uma "
        "unidade vende hoje está em `GET /unidades/{id}/cardapio`)."
    ),
    "responses": {
        **documentar_sucesso(
            HTTPStatus.OK,
            "Página de produtos",
            {
                "catalogo": {
                    "dados": [TAPIOCA, CUSCUZ],
                    "paginacao": {"page": 1, "limit": 2, "total": 6, "totalPaginas": 3},
                }
            },
        ),
        **documentar_erros("/produtos", validacao_falhou("limit", "Deve ser menor ou igual a 100")),
    },
}

CONSULTAR_PRODUTO: dict[str, Any] = {
    "summary": "Consultar produto",
    "description": "**Perfil:** público.\n\nDados de um produto, ativo ou não.",
    "responses": {
        **documentar_sucesso(HTTPStatus.OK, "Produto", {"tapioca": TAPIOCA}),
        **documentar_erros("/produtos/99", PRODUTO_INEXISTENTE),
        **documentar_erros("/produtos/abc", ID_NAO_INTEIRO),
    },
}

PAMONHA = {
    "nome": "Pamonha",
    "descricao": "Pamonha de milho verde",
    "preco": 11.5,
}
EXEMPLOS_CADASTRAR_PRODUTO = {"pamonha": {"summary": "Novo produto no catálogo", "value": PAMONHA}}

CADASTRAR_PRODUTO: dict[str, Any] = {
    "summary": "Cadastrar produto",
    "description": (
        "**Perfil:** ADMIN.\n\n"
        "Cria um produto ativo no catálogo da rede. `preco` maior que zero, com até 2 casas "
        "decimais. O produto só entra no cardápio de uma unidade depois da primeira entrada "
        "de estoque nela (RN03)."
    ),
    "responses": {
        **documentar_sucesso(
            HTTPStatus.CREATED,
            "Produto cadastrado",
            {"pamonha": {"id": 7, **PAMONHA, "ativo": True}},
        ),
        **documentar_erros(
            "/produtos",
            JSON_MALFORMADO,
            TOKEN_AUSENTE,
            SEM_PERMISSAO,
            validacao_falhou("preco", "Deve ser maior que 0"),
        ),
    },
}

TAPIOCA_REAJUSTADA = {**TAPIOCA, "preco": 19.9}
EXEMPLOS_ATUALIZAR_PRODUTO = {
    "reajuste": {
        "summary": "Reajustar o preço da tapioca",
        "value": {campo: valor for campo, valor in TAPIOCA_REAJUSTADA.items() if campo != "id"},
    }
}

ATUALIZAR_PRODUTO: dict[str, Any] = {
    "summary": "Atualizar produto",
    "description": (
        "**Perfil:** ADMIN.\n\n"
        "Substitui todos os dados do produto, inclusive `ativo` (o body vai completo), com as "
        "mesmas regras do cadastro. Pedidos já feitos mantêm o preço da época. A alteração "
        "fica na auditoria, com os dados antes e depois."
    ),
    "responses": {
        **documentar_sucesso(HTTPStatus.OK, "Produto atualizado", {"reajuste": TAPIOCA_REAJUSTADA}),
        **documentar_erros(
            "/produtos/1",
            JSON_MALFORMADO,
            TOKEN_AUSENTE,
            SEM_PERMISSAO,
            validacao_falhou("preco", "Deve ser maior que 0"),
        ),
        **documentar_erros("/produtos/99", PRODUTO_INEXISTENTE),
    },
}

DESATIVAR_PRODUTO: dict[str, Any] = {
    "summary": "Desativar produto",
    "description": (
        "**Perfil:** ADMIN.\n\n"
        "Desativa o produto (`ativo = false`) sem apagar o registro, que pedidos antigos "
        "referenciam; ele sai do cardápio de todas as unidades. Repetir a chamada não muda "
        "nada e devolve 204 de novo. A desativação fica na auditoria."
    ),
    "responses": {
        **documentar_sem_conteudo("Produto desativado"),
        **documentar_erros("/produtos/1", TOKEN_AUSENTE, SEM_PERMISSAO),
        **documentar_erros("/produtos/99", PRODUTO_INEXISTENTE),
        **documentar_erros("/produtos/abc", ID_NAO_INTEIRO),
    },
}
