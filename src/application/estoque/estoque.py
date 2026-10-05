from sqlalchemy import Connection

from src.application.produtos.produtos import consultar_produto
from src.application.unidades.unidades import consultar_unidade
from src.domain.auditoria.auditoria import AcaoAuditoria
from src.domain.estoque.estoque import (
    DadosMovimentacao,
    ItemHistoricoEstoque,
    MovimentacaoEstoque,
    SaldoProduto,
    calcular_saldo,
)
from src.domain.usuario.usuario import UsuarioAutenticado, verificar_acesso_a_unidade
from src.infrastructure.database.repositorios.auditoria import RepositorioAuditoria
from src.infrastructure.database.repositorios.estoque import RepositorioEstoque

ENTIDADE_ESTOQUE = "Estoque"


def consultar_saldos(
    conexao: Connection, usuario: UsuarioAutenticado, unidade_id: int, limit: int, offset: int
) -> tuple[list[SaldoProduto], int]:
    # RN23 antes da existência: o funcionário não descobre pelo 404 se a unidade existe.
    verificar_acesso_a_unidade(usuario, unidade_id)
    consultar_unidade(conexao, unidade_id)
    repositorio = RepositorioEstoque(conexao)
    return (
        repositorio.listar_saldos(unidade_id, limit, offset),
        repositorio.contar_saldos(unidade_id),
    )


def movimentar_estoque(
    conexao: Connection, usuario: UsuarioAutenticado, dados: DadosMovimentacao
) -> tuple[MovimentacaoEstoque, int]:
    verificar_acesso_a_unidade(usuario, dados.unidade_id)
    consultar_unidade(conexao, dados.unidade_id)
    consultar_produto(conexao, dados.produto_id)
    repositorio = RepositorioEstoque(conexao)
    # A primeira ENTRADA cria a linha e passa a oferecer o produto na unidade (RN03,
    # seção 9.4). Numa SAIDA recusada o erro desfaz a transação e a linha some junto.
    repositorio.criar_se_nao_existir(dados.unidade_id, dados.produto_id)
    estoque = repositorio.travar(dados.unidade_id, dados.produto_id)
    saldo_atual = calcular_saldo(estoque.quantidade, dados.tipo, dados.quantidade, dados.produto_id)
    repositorio.atualizar_quantidade(estoque.id, saldo_atual)
    movimentacao = repositorio.registrar_movimentacao(
        estoque_id=estoque.id,
        tipo=dados.tipo,
        quantidade=dados.quantidade,
        motivo=dados.motivo,
        usuario_id=usuario.id,
    )
    RepositorioAuditoria(conexao).registrar(
        usuario_id=usuario.id,
        unidade_id=dados.unidade_id,
        acao=AcaoAuditoria.ESTOQUE_MOVIMENTADO,
        entidade=ENTIDADE_ESTOQUE,
        entidade_id=estoque.id,
        dados_antes={"produtoId": dados.produto_id, "quantidade": estoque.quantidade},
        dados_depois={
            "produtoId": dados.produto_id,
            "quantidade": saldo_atual,
            "movimentacaoId": movimentacao.id,
            "tipo": dados.tipo,
            "motivo": dados.motivo,
        },
    )
    return movimentacao, saldo_atual


def listar_movimentacoes(
    conexao: Connection,
    usuario: UsuarioAutenticado,
    unidade_id: int,
    produto_id: int | None,
    limit: int,
    offset: int,
) -> tuple[list[ItemHistoricoEstoque], int]:
    verificar_acesso_a_unidade(usuario, unidade_id)
    repositorio = RepositorioEstoque(conexao)
    return (
        repositorio.listar_movimentacoes(unidade_id, produto_id, limit, offset),
        repositorio.contar_movimentacoes(unidade_id, produto_id),
    )
