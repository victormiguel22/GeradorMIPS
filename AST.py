from dataclasses import dataclass
from typing import List, Optional, Any

@dataclass
class NoAST:
    linha: int
    coluna: int


@dataclass
class Programa(NoAST):
    comandos: List[NoAST]


@dataclass
class DeclaracaoVariavel(NoAST):
    tipo: str
    nome: str
    tamanho_array: Optional[int] = None
    valor_inicial: Optional[NoAST] = None


@dataclass
class DeclaracaoFuncao(NoAST):
    tipo_retorno: str
    nome: str
    parametros: List['Parametro']
    corpo: List[NoAST]


@dataclass
class Parametro(NoAST):
    tipo: str
    nome: str


@dataclass
class Atribuicao(NoAST):
    nome: str
    expressao: NoAST


@dataclass
class ComandoSe(NoAST):
    condicao: NoAST
    bloco_verdadeiro: List[NoAST]
    bloco_falso: Optional[List[NoAST]] = None


@dataclass
class ComandoEnquanto(NoAST):
    condicao: NoAST
    bloco: List[NoAST]


@dataclass
class ComandoPara(NoAST):
    inicializacao: Optional[NoAST]
    condicao: Optional[NoAST]
    incremento: Optional[NoAST]
    bloco: List[NoAST]


@dataclass
class ComandoEscreva(NoAST):
    expressao: NoAST


@dataclass
class ComandoLeia(NoAST):
    variavel: str


@dataclass
class ChamadaFuncao(NoAST):
    nome: str
    argumentos: List[NoAST]


@dataclass
class ExpressaoBinaria(NoAST):
    esquerda: NoAST
    operador: str
    direita: NoAST


@dataclass
class ExpressaoUnaria(NoAST):
    operador: str
    expressao: NoAST


@dataclass
class Literal(NoAST):
    valor: Any
    tipo: str


@dataclass
class Identificador(NoAST):
    nome: str