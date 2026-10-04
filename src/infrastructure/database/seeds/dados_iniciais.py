from datetime import date
from decimal import Decimal

from sqlalchemy import Connection, Table, insert, text

from src.domain.unidade.unidade import TipoUnidade
from src.domain.usuario.usuario import FinalidadeConsentimento, Perfil
from src.infrastructure.database.tabelas import (
    consentimento,
    estoque,
    metadata,
    produto,
    unidade,
    usuario,
)
from src.infrastructure.seguranca.hash_senha import HashSenha

SENHA_DESENVOLVIMENTO = "Raizes@2026"
VERSAO_TERMO = "1.0"
DOMINIO_EMAIL = "raizesdonordeste.com.br"
SALDO_INICIAL_RECIFE = 100
SALDO_INICIAL_CARUARU = 50
# Saldo baixo de propósito para o cenário de estoque insuficiente (T56).
SALDO_BOLO_RECIFE = 2
PRODUTO_COM_SALDO_BAIXO = "Bolo de macaxeira"

UNIDADES = [
    {
        "nome": "Raízes do Nordeste Recife",
        "cidade": "Recife",
        "uf": "PE",
        "regiao": "Nordeste",
        "tipo": TipoUnidade.COZINHA_COMPLETA,
    },
    {
        "nome": "Raízes do Nordeste Caruaru",
        "cidade": "Caruaru",
        "uf": "PE",
        "regiao": "Nordeste",
        "tipo": TipoUnidade.FORMATO_REDUZIDO,
    },
]

# Preços fictícios: os documentos não informam valores.
PRODUTOS = [
    {"nome": "Tapioca", "descricao": "Tapioca de queijo coalho", "preco": Decimal("18.90")},
    {
        "nome": "Cuscuz recheado",
        "descricao": "Cuscuz de milho recheado com carne de sol",
        "preco": Decimal("24.90"),
    },
    {
        "nome": "Bolo de macaxeira",
        "descricao": "Fatia de bolo de macaxeira",
        "preco": Decimal("12.50"),
    },
    {
        "nome": "Suco regional",
        "descricao": "Suco de cajá, caju ou acerola (500 ml)",
        "preco": Decimal("9.90"),
    },
    {
        "nome": "Café da manhã completo",
        "descricao": "Tapioca, cuscuz, bolo, suco e café",
        "preco": Decimal("49.90"),
    },
    {"nome": "Café passado", "descricao": "Café coado na hora (200 ml)", "preco": Decimal("6.50")},
    {
        "nome": "Canjica junina",
        "descricao": "Canjica de milho verde do período junino",
        "preco": Decimal("14.90"),
        "disponivel_de": date(2026, 6, 1),
        "disponivel_ate": date(2026, 7, 31),
    },
]

# Formato reduzido não serve o café da manhã completo (cenário T88).
PRODUTOS_FORA_DE_CARUARU = {"Café da manhã completo"}


def popular_banco(conexao: Connection, hash_senha: HashSenha) -> None:
    """Apaga todos os dados e recria os dados de desenvolvimento com ids a partir de 1."""
    _limpar(conexao)
    recife_id, caruaru_id = _inserir(conexao, unidade, UNIDADES)
    # O executemany usa só as chaves do primeiro registro; sem o padrão a janela do sazonal some.
    produtos = [{"disponivel_de": None, "disponivel_ate": None, **p} for p in PRODUTOS]
    produto_ids = dict(
        zip((p["nome"] for p in PRODUTOS), _inserir(conexao, produto, produtos), strict=True)
    )
    _inserir_estoque(conexao, recife_id, caruaru_id, produto_ids)
    cliente_id = _inserir_usuarios(conexao, hash_senha, recife_id, caruaru_id)
    conexao.execute(
        insert(consentimento),
        {
            "usuario_id": cliente_id,
            "finalidade": FinalidadeConsentimento.FIDELIDADE,
            "concedido": True,
            "versao_termo": VERSAO_TERMO,
        },
    )


def _limpar(conexao: Connection) -> None:
    tabelas = ", ".join(metadata.tables)
    conexao.execute(text(f"TRUNCATE TABLE {tabelas} RESTART IDENTITY CASCADE"))


def _inserir(conexao: Connection, tabela: Table, registros: list[dict]) -> list[int]:
    return list(
        conexao.execute(
            insert(tabela).returning(tabela.c.id, sort_by_parameter_order=True), registros
        ).scalars()
    )


def _inserir_estoque(
    conexao: Connection, recife_id: int, caruaru_id: int, produto_ids: dict[str, int]
) -> None:
    registros = [
        {
            "unidade_id": recife_id,
            "produto_id": produto_id,
            "quantidade": SALDO_BOLO_RECIFE
            if nome == PRODUTO_COM_SALDO_BAIXO
            else SALDO_INICIAL_RECIFE,
        }
        for nome, produto_id in produto_ids.items()
    ]
    registros += [
        {"unidade_id": caruaru_id, "produto_id": produto_id, "quantidade": SALDO_INICIAL_CARUARU}
        for nome, produto_id in produto_ids.items()
        if nome not in PRODUTOS_FORA_DE_CARUARU
    ]
    conexao.execute(insert(estoque), registros)


def _inserir_usuarios(
    conexao: Connection, hash_senha: HashSenha, recife_id: int, caruaru_id: int
) -> int:
    usuarios = [
        ("Administrador da Rede", "admin", Perfil.ADMIN, None),
        ("Gerente Recife", "gerente.recife", Perfil.GERENTE, recife_id),
        ("Gerente Caruaru", "gerente.caruaru", Perfil.GERENTE, caruaru_id),
        ("Atendente Recife", "atendente.recife", Perfil.ATENDENTE, recife_id),
        ("Cozinha Recife", "cozinha.recife", Perfil.COZINHA, recife_id),
        ("Maria Cliente", "cliente", Perfil.CLIENTE, None),
        ("João Sem Consentimento", "cliente.sem.consentimento", Perfil.CLIENTE, None),
    ]
    ids = _inserir(
        conexao,
        usuario,
        [
            {
                "nome": nome,
                "email": f"{local}@{DOMINIO_EMAIL}",
                "senha_hash": hash_senha.gerar(SENHA_DESENVOLVIMENTO),
                "perfil": perfil,
                "unidade_id": unidade_id,
            }
            for nome, local, perfil, unidade_id in usuarios
        ],
    )
    ids_por_email_local = dict(zip((local for _, local, _, _ in usuarios), ids, strict=True))
    return ids_por_email_local["cliente"]
