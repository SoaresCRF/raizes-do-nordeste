from sqlalchemy import Connection

from src.domain.auditoria.auditoria import AcaoAuditoria
from src.domain.erros.erros import ConsentimentoAusente
from src.domain.fidelidade.fidelidade import (
    TipoTransacaoFidelidade,
    TransacaoFidelidade,
    calcular_desconto_do_resgate,
    calcular_pontos_ganhos,
    tem_consentimento_fidelidade,
)
from src.domain.pedido.pedido import (
    ENTIDADE_PEDIDO,
    Pedido,
    verificar_aguardando_pagamento,
    verificar_pedido_acessivel,
)
from src.domain.usuario.usuario import UsuarioAutenticado
from src.infrastructure.database.repositorios.auditoria import RepositorioAuditoria
from src.infrastructure.database.repositorios.consentimentos import RepositorioConsentimentos
from src.infrastructure.database.repositorios.fidelidade import RepositorioFidelidade
from src.infrastructure.database.repositorios.pedidos import RepositorioPedidos
from src.infrastructure.database.repositorios.usuarios import RepositorioUsuarios


def _consentiu_fidelidade(conexao: Connection, cliente_id: int) -> bool:
    vigentes = RepositorioConsentimentos(conexao).listar_vigentes(cliente_id)
    return tem_consentimento_fidelidade(vigentes)


def creditar_pontos(conexao: Connection, pedido: Pedido) -> None:
    """Credita os pontos do pagamento aprovado (RN18) se o cliente consentiu (RN17)."""
    # Pedido de balcão sem cliente não pontua (Q03).
    if pedido.cliente_id is None or not _consentiu_fidelidade(conexao, pedido.cliente_id):
        return
    pontos = calcular_pontos_ganhos(pedido.total)
    # Abaixo de R$ 1,00 não há ponto inteiro, e a tabela não aceita transação de 0 pontos.
    if pontos == 0:
        return
    RepositorioFidelidade(conexao).inserir(
        pedido.cliente_id, TipoTransacaoFidelidade.ACUMULO, pontos, pedido.id
    )


def consultar_saldo(conexao: Connection, cliente_id: int) -> int:
    return RepositorioFidelidade(conexao).calcular_saldo(cliente_id)


def listar_historico(
    conexao: Connection, cliente_id: int, limit: int, offset: int
) -> tuple[list[TransacaoFidelidade], int]:
    repositorio = RepositorioFidelidade(conexao)
    return repositorio.listar(cliente_id, limit, offset), repositorio.contar(cliente_id)


def resgatar_pontos(
    conexao: Connection, cliente: UsuarioAutenticado, pedido_id: int, pontos: int
) -> tuple[Pedido, int]:
    repositorio_pedidos = RepositorioPedidos(conexao)
    pedido = verificar_pedido_acessivel(cliente, pedido_id, repositorio_pedidos.travar(pedido_id))
    verificar_aguardando_pagamento(pedido)
    if not _consentiu_fidelidade(conexao, cliente.id):
        raise ConsentimentoAusente(f"Cliente {cliente.id} sem consentimento FIDELIDADE ativo")
    # Trava o cliente antes de ler o saldo: dois resgates simultâneos em pedidos
    # diferentes não gastam os mesmos pontos.
    RepositorioUsuarios(conexao).travar(cliente.id)
    repositorio = RepositorioFidelidade(conexao)
    saldo = repositorio.calcular_saldo(cliente.id)
    desconto = calcular_desconto_do_resgate(pontos, saldo, pedido.total)
    repositorio.inserir(cliente.id, TipoTransacaoFidelidade.RESGATE, -pontos, pedido.id)
    com_desconto = repositorio_pedidos.aplicar_desconto(pedido.id, desconto)
    RepositorioAuditoria(conexao).registrar(
        usuario_id=cliente.id,
        unidade_id=pedido.unidade_id,
        acao=AcaoAuditoria.PONTOS_RESGATADOS,
        entidade=ENTIDADE_PEDIDO,
        entidade_id=pedido.id,
        dados_antes={"desconto": str(pedido.desconto), "total": str(pedido.total)},
        dados_depois={
            "pontos": pontos,
            "desconto": str(com_desconto.desconto),
            "total": str(com_desconto.total),
        },
    )
    return com_desconto, saldo - pontos


def estornar_pontos(conexao: Connection, pedido: Pedido, tipo: TipoTransacaoFidelidade) -> None:
    """Lança um ESTORNO que desfaz as transações do tipo dado no pedido (RN16, Q12).

    O saldo pode ficar negativo quando os pontos ganhos já foram usados.
    """
    if pedido.cliente_id is None:
        return
    repositorio = RepositorioFidelidade(conexao)
    pontos = repositorio.somar_do_pedido(pedido.id, tipo)
    if pontos == 0:
        return
    repositorio.inserir(pedido.cliente_id, TipoTransacaoFidelidade.ESTORNO, -pontos, pedido.id)
