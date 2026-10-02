from enum import StrEnum


class TipoTransacaoFidelidade(StrEnum):
    ACUMULO = "ACUMULO"
    RESGATE = "RESGATE"
    ESTORNO = "ESTORNO"
