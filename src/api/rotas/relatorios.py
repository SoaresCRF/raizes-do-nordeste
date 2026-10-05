from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from src.api.autenticacao import GestorLogado
from src.api.dependencias import ConexaoBanco
from src.api.schemas.relatorios import LinhaRelatorioResposta, RelatorioVendasResposta
from src.application.relatorios.relatorios import gerar_relatorio_de_vendas
from src.domain.relatorio.relatorio import Agrupamento

roteador = APIRouter(prefix="/relatorios", tags=["Relatórios"])


@roteador.get("/vendas")
def gerar_relatorio_de_vendas_da_matriz(
    agrupamento: Annotated[Agrupamento, Query()],
    usuario: GestorLogado,
    conexao: ConexaoBanco,
    de: Annotated[date | None, Query()] = None,
    ate: Annotated[date | None, Query()] = None,
) -> RelatorioVendasResposta:
    linhas = gerar_relatorio_de_vendas(conexao, usuario, agrupamento, de, ate)
    return RelatorioVendasResposta(
        agrupamento=agrupamento,
        de=de,
        ate=ate,
        dados=[
            LinhaRelatorioResposta.model_validate(linha, from_attributes=True) for linha in linhas
        ],
    )
