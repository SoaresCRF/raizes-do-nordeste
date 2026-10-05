from datetime import date

from src.api.schemas.base import EsquemaSaida, ValorMonetario
from src.domain.relatorio.relatorio import Agrupamento


class LinhaRelatorioResposta(EsquemaSaida):
    grupo_id: int | None
    grupo: str
    pedidos: int
    quantidade: int
    total: ValorMonetario


class RelatorioVendasResposta(EsquemaSaida):
    agrupamento: Agrupamento
    de: date | None
    ate: date | None
    dados: list[LinhaRelatorioResposta]
