from sqlalchemy import Connection

from src.application.produtos.produtos import consultar_produto
from src.application.unidades.unidades import consultar_unidade
from src.domain.auditoria.auditoria import AcaoAuditoria
from src.domain.estoque.estoque import (
    DadosMovimentacao,
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
    repositorio.inserir_se_nao_existir(dados.unidade_id, dados.produto_id)
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
