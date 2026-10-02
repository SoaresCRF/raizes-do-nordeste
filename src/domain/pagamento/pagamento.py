from enum import StrEnum


class FormaPagamento(StrEnum):
    MOCK = "MOCK"


class StatusPagamento(StrEnum):
    PENDENTE = "PENDENTE"
    APROVADO = "APROVADO"
    RECUSADO = "RECUSADO"
    ERRO = "ERRO"
    ESTORNADO = "ESTORNADO"
