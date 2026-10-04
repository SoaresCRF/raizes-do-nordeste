from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from src.domain.erros.erros import MENSAGEM_DADOS_INVALIDOS, DadosInvalidos, DetalheErro


@dataclass(frozen=True)
class DadosProduto:
    nome: str
    descricao: str | None
    preco: Decimal
    disponivel_de: date | None
    disponivel_ate: date | None


@dataclass(frozen=True)
class ItemCardapio:
    produto_id: int
    nome: str
    descricao: str | None
    preco: Decimal
    disponivel: bool


def validar_periodo(disponivel_de: date | None, disponivel_ate: date | None) -> None:
    """Período sazonal (RN24): cada ponta é opcional, mas não termina antes de começar."""
    if disponivel_de is None or disponivel_ate is None or disponivel_de <= disponivel_ate:
        return
    raise DadosInvalidos(
        MENSAGEM_DADOS_INVALIDOS,
        [DetalheErro("disponivelAte", "Deve ser igual ou posterior a disponivelDe")],
    )


@dataclass
class Produto:
    id: int
    nome: str
    descricao: str | None
    preco: Decimal
    ativo: bool
    disponivel_de: date | None
    disponivel_ate: date | None
    created_at: datetime
    updated_at: datetime
