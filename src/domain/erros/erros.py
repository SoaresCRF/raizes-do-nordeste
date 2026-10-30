from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True)
class DetalheErro:
    campo: str
    problema: str


class ErroDominio(Exception):
    codigo: str

    def __init__(self, mensagem: str, detalhes: list[DetalheErro] | None = None) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.detalhes = detalhes or []


class CredenciaisInvalidas(ErroDominio):
    codigo = "CREDENCIAIS_INVALIDAS"


class NaoAutenticado(ErroDominio):
    codigo = "NAO_AUTENTICADO"


class AcessoNegado(ErroDominio):
    codigo = "ACESSO_NEGADO"


class RecursoNaoEncontrado(ErroDominio):
    codigo = "RECURSO_NAO_ENCONTRADO"


class EmailJaCadastrado(ErroDominio):
    codigo = "EMAIL_JA_CADASTRADO"


class EstoqueInsuficiente(ErroDominio):
    codigo = "ESTOQUE_INSUFICIENTE"


class ProdutoIndisponivelNaUnidade(ErroDominio):
    codigo = "PRODUTO_INDISPONIVEL_NA_UNIDADE"


class TransicaoStatusInvalida(ErroDominio):
    codigo = "TRANSICAO_STATUS_INVALIDA"


class PagamentoNaoPermitido(ErroDominio):
    codigo = "PAGAMENTO_NAO_PERMITIDO"


class ConsentimentoAusente(ErroDominio):
    codigo = "CONSENTIMENTO_AUSENTE"


class SaldoPontosInsuficiente(ErroDominio):
    codigo = "SALDO_PONTOS_INSUFICIENTE"


class GatewayPagamentoIndisponivel(ErroDominio):
    codigo = "GATEWAY_PAGAMENTO_INDISPONIVEL"


MENSAGEM_DADOS_INVALIDOS = "Dados de entrada inválidos"


class DadosInvalidos(ErroDominio):
    codigo = "VALIDACAO_FALHOU"

    @classmethod
    def no_campo(cls, campo: str, problema: str) -> Self:
        return cls(MENSAGEM_DADOS_INVALIDOS, [DetalheErro(campo, problema)])
