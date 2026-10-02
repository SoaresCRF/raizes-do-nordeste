from enum import StrEnum


class Perfil(StrEnum):
    CLIENTE = "CLIENTE"
    ATENDENTE = "ATENDENTE"
    COZINHA = "COZINHA"
    GERENTE = "GERENTE"
    ADMIN = "ADMIN"


PERFIS_LOTADOS_EM_UNIDADE = (Perfil.ATENDENTE, Perfil.COZINHA, Perfil.GERENTE)


class FinalidadeConsentimento(StrEnum):
    FIDELIDADE = "FIDELIDADE"
    MARKETING = "MARKETING"
