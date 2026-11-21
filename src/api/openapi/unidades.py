from http import HTTPStatus
from typing import Any

from src.api.openapi.respostas import (
    ID_NAO_INTEIRO,
    JSON_MALFORMADO,
    TOKEN_AUSENTE,
    UNIDADE_INEXISTENTE,
    documentar_erros,
    documentar_sucesso,
    perfil_sem_permissao,
    validacao_falhou,
)
from src.domain.usuario import Perfil

UNIDADE_RECIFE = {
    "id": 1,
    "nome": "Raízes do Nordeste Recife",
    "cidade": "Recife",
    "uf": "PE",
    "regiao": "Nordeste",
    "tipo": "COZINHA_COMPLETA",
    "ativa": True,
}
UNIDADE_CARUARU = {
    "id": 2,
    "nome": "Raízes do Nordeste Caruaru",
    "cidade": "Caruaru",
    "uf": "PE",
    "regiao": "Nordeste",
    "tipo": "FORMATO_REDUZIDO",
    "ativa": True,
}
LIMIT_ACIMA_DO_MAXIMO = validacao_falhou("limit", "Deve ser menor ou igual a 100")

LISTAR_UNIDADES: dict[str, Any] = {
    "summary": "Listar unidades",
    "description": (
        "**Perfil:** público.\n\n"
        "Unidades da rede, inclusive as inativas (campo `ativa`), em ordem de id, paginadas."
    ),
    "responses": {
        **documentar_sucesso(
            HTTPStatus.OK,
            "Página de unidades",
            {
                "nordeste": {
                    "dados": [UNIDADE_RECIFE, UNIDADE_CARUARU],
                    "paginacao": {"page": 1, "limit": 10, "total": 2, "totalPaginas": 1},
                }
            },
        ),
        **documentar_erros("/unidades", LIMIT_ACIMA_DO_MAXIMO),
    },
}

CONSULTAR_UNIDADE: dict[str, Any] = {
    "summary": "Consultar unidade",
    "description": "**Perfil:** público.\n\nDados de uma unidade, ativa ou não.",
    "responses": {
        **documentar_sucesso(HTTPStatus.OK, "Unidade", {"recife": UNIDADE_RECIFE}),
        **documentar_erros("/unidades/99", UNIDADE_INEXISTENTE),
        **documentar_erros("/unidades/abc", ID_NAO_INTEIRO),
    },
}

EXEMPLOS_CADASTRAR_UNIDADE = {
    "olinda": {
        "summary": "Unidade de formato reduzido",
        "value": {
            "nome": "Raízes do Nordeste Olinda",
            "cidade": "Olinda",
            "uf": "PE",
            "regiao": "Nordeste",
            "tipo": "FORMATO_REDUZIDO",
        },
    }
}

CADASTRAR_UNIDADE: dict[str, Any] = {
    "summary": "Cadastrar unidade",
    "description": (
        "**Perfil:** ADMIN.\n\n"
        "Cria uma unidade ativa. `uf` aceita só as 27 siglas (maiúsculas ou minúsculas); "
        "`tipo` define o formato da unidade. A criação fica na auditoria."
    ),
    "responses": {
        **documentar_sucesso(
            HTTPStatus.CREATED,
            "Unidade cadastrada",
            {
                "olinda": {
                    "id": 3,
                    "nome": "Raízes do Nordeste Olinda",
                    "cidade": "Olinda",
                    "uf": "PE",
                    "regiao": "Nordeste",
                    "tipo": "FORMATO_REDUZIDO",
                    "ativa": True,
                }
            },
        ),
        **documentar_erros(
            "/unidades",
            JSON_MALFORMADO,
            TOKEN_AUSENTE,
            perfil_sem_permissao(Perfil.GERENTE),
            validacao_falhou("uf", "Deve ser a sigla de uma UF do Brasil"),
        ),
    },
}

CARUARU_INATIVA = {**UNIDADE_CARUARU, "ativa": False}
EXEMPLOS_ATUALIZAR_UNIDADE = {
    "desativar": {
        "summary": "Desativar a unidade Caruaru",
        "value": {campo: valor for campo, valor in CARUARU_INATIVA.items() if campo != "id"},
    }
}

ATUALIZAR_UNIDADE: dict[str, Any] = {
    "summary": "Atualizar unidade",
    "description": (
        "**Perfil:** ADMIN.\n\n"
        "Substitui todos os dados da unidade, inclusive `ativa` (o body vai completo). Mesmas "
        "validações do cadastro."
    ),
    "responses": {
        **documentar_sucesso(HTTPStatus.OK, "Unidade atualizada", {"desativada": CARUARU_INATIVA}),
        **documentar_erros(
            "/unidades/2",
            JSON_MALFORMADO,
            TOKEN_AUSENTE,
            perfil_sem_permissao(Perfil.GERENTE),
            validacao_falhou("ativa", "Campo obrigatório"),
        ),
        **documentar_erros("/unidades/99", UNIDADE_INEXISTENTE),
    },
}

CONSULTAR_CARDAPIO: dict[str, Any] = {
    "summary": "Consultar o cardápio da unidade",
    "description": (
        "**Perfil:** público.\n\n"
        "Produtos que a unidade oferece (RN03): ativos e com estoque cadastrado na unidade. "
        "`disponivel` é `false` quando o saldo está zerado. Paginado, em ordem de produto."
    ),
    "responses": {
        **documentar_sucesso(
            HTTPStatus.OK,
            "Página do cardápio",
            {
                "recife": {
                    "dados": [
                        {
                            "produtoId": 1,
                            "nome": "Tapioca",
                            "descricao": "Tapioca de queijo coalho",
                            "preco": 18.9,
                            "disponivel": True,
                        },
                        {
                            "produtoId": 2,
                            "nome": "Cuscuz recheado",
                            "descricao": "Cuscuz de milho recheado com carne de sol",
                            "preco": 24.9,
                            "disponivel": True,
                        },
                    ],
                    "paginacao": {"page": 1, "limit": 2, "total": 6, "totalPaginas": 3},
                }
            },
        ),
        **documentar_erros("/unidades/99/cardapio", UNIDADE_INEXISTENTE),
        **documentar_erros(
            "/unidades/1/cardapio", validacao_falhou("page", "Deve ser maior ou igual a 1")
        ),
    },
}
