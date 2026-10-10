from http import HTTPStatus
from typing import Any

from src.api.openapi.respostas import (
    ID_NAO_INTEIRO,
    JSON_MALFORMADO,
    TOKEN_AUSENTE,
    nao_encontrado,
    perfil_sem_permissao,
    resposta_de_sucesso,
    resposta_sem_conteudo,
    respostas_de_erro,
    validacao_falhou,
)
from src.domain.usuario.usuario import Perfil

TAPIOCA = {
    "id": 1,
    "nome": "Tapioca",
    "descricao": "Tapioca de queijo coalho",
    "preco": 18.9,
    "ativo": True,
    "disponivelDe": None,
    "disponivelAte": None,
}
CUSCUZ = {
    "id": 2,
    "nome": "Cuscuz recheado",
    "descricao": "Cuscuz de milho recheado com carne de sol",
    "preco": 24.9,
    "ativo": True,
    "disponivelDe": None,
    "disponivelAte": None,
}
CANJICA = {
    "id": 7,
    "nome": "Canjica junina",
    "descricao": "Canjica de milho verde do período junino",
    "preco": 14.9,
    "ativo": True,
    "disponivelDe": "2026-06-01",
    "disponivelAte": "2026-07-31",
}
PRODUTO_INEXISTENTE = nao_encontrado("Produto 99 não encontrado")
SEM_PERMISSAO = perfil_sem_permissao(Perfil.GERENTE)

LISTAR_PRODUTOS: dict[str, Any] = {
    "summary": "Listar produtos",
    "description": (
        "**Perfil:** público.\n\n"
        "Catálogo da rede, inclusive produtos inativos e fora do período, em ordem de id, "
        "paginado (o que uma unidade vende hoje está em `GET /unidades/{id}/cardapio`). "
        "`nome` busca por trecho do nome, sem diferenciar maiúsculas."
    ),
    "responses": {
        **resposta_de_sucesso(
            HTTPStatus.OK,
            "Página de produtos",
            {
                "catalogo": {
                    "dados": [TAPIOCA, CUSCUZ],
                    "paginacao": {"page": 1, "limit": 2, "total": 7, "totalPaginas": 4},
                }
            },
        ),
        **respostas_de_erro(
            "/produtos", validacao_falhou("limit", "Deve ser menor ou igual a 100")
        ),
    },
}

CONSULTAR_PRODUTO: dict[str, Any] = {
    "summary": "Consultar produto",
    "description": "**Perfil:** público.\n\nDados de um produto, ativo ou não.",
    "responses": {
        **resposta_de_sucesso(HTTPStatus.OK, "Produto", {"sazonal": CANJICA}),
        **respostas_de_erro("/produtos/99", PRODUTO_INEXISTENTE),
        **respostas_de_erro("/produtos/abc", ID_NAO_INTEIRO),
    },
}

PAMONHA = {
    "nome": "Pamonha",
    "descricao": "Pamonha de milho verde",
    "preco": 11.5,
    "disponivelDe": "2026-06-01",
    "disponivelAte": "2026-07-31",
}
EXEMPLOS_CADASTRAR_PRODUTO = {
    "sazonal": {"summary": "Produto sazonal do período junino", "value": PAMONHA}
}

CADASTRAR_PRODUTO: dict[str, Any] = {
    "summary": "Cadastrar produto",
    "description": (
        "**Perfil:** ADMIN.\n\n"
        "Cria um produto ativo no catálogo da rede. `preco` maior que zero, com até 2 casas "
        "decimais. `disponivelDe` e `disponivelAte` (opcionais, AAAA-MM-DD) limitam o período "
        "de venda de um sazonal (RN24); `disponivelAte` não pode ser anterior a "
        "`disponivelDe`. O produto só entra no cardápio de uma unidade depois da primeira "
        "entrada de estoque nela (RN03)."
    ),
    "responses": {
        **resposta_de_sucesso(
            HTTPStatus.CREATED,
            "Produto cadastrado",
            {"sazonal": {"id": 8, **PAMONHA, "ativo": True}},
        ),
        **respostas_de_erro(
            "/produtos",
            JSON_MALFORMADO,
            TOKEN_AUSENTE,
            SEM_PERMISSAO,
            validacao_falhou("disponivelAte", "Deve ser igual ou posterior a disponivelDe"),
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
        **resposta_de_sucesso(
            HTTPStatus.OK, "Produto atualizado", {"reajuste": TAPIOCA_REAJUSTADA}
        ),
        **respostas_de_erro(
            "/produtos/1",
            JSON_MALFORMADO,
            TOKEN_AUSENTE,
            SEM_PERMISSAO,
            validacao_falhou("preco", "Deve ser maior que 0"),
        ),
        **respostas_de_erro("/produtos/99", PRODUTO_INEXISTENTE),
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
        **resposta_sem_conteudo("Produto desativado"),
        **respostas_de_erro("/produtos/1", TOKEN_AUSENTE, SEM_PERMISSAO),
        **respostas_de_erro("/produtos/99", PRODUTO_INEXISTENTE),
        **respostas_de_erro("/produtos/abc", ID_NAO_INTEIRO),
    },
}
