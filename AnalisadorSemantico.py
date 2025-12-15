from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

# Importe as classes da AST do arquivo AST.py
from AST import (
    NoAST, Programa, DeclaracaoVariavel, DeclaracaoFuncao, Parametro,
    Atribuicao, ComandoSe, ComandoEnquanto, ComandoPara, ComandoEscreva,
    ComandoLeia, ChamadaFuncao, ExpressaoBinaria, ExpressaoUnaria,
    Literal, Identificador
)

Tipo = str  # 'inteiro', 'flutuante', 'logico', 'cadeia'

@dataclass
class ErroSemantico:
    mensagem: str
    linha: int
    coluna: int

    def __str__(self):
        return f"Erro semântico [linha {self.linha}, coluna {self.coluna}]: {self.mensagem}"

class AnalisadorSemantico:
    def __init__(self):
        self.erros: List[ErroSemantico] = []
        self.tabela_simbolos: List[Dict[str, Tuple[Tipo, bool]]] = [{}]
        self.funcoes: Dict[str, Tuple[Tipo, List[Tipo]]] = {}

    def entrar_escopo(self):
        self.tabela_simbolos.append({})

    def sair_escopo(self):
        if len(self.tabela_simbolos) > 1:
            self.tabela_simbolos.pop()

    def declarar_variavel(self, nome: str, tipo: Tipo, é_array: bool, linha: int, coluna: int):
        escopo_atual = self.tabela_simbolos[-1]
        if nome in escopo_atual:
            self.erros.append(ErroSemantico(f"Variável '{nome}' já declarada neste escopo", linha, coluna))
        else:
            escopo_atual[nome] = (tipo, é_array)

    def buscar_variavel(self, nome: str, linha: int, coluna: int) -> Optional[Tuple[Tipo, bool]]:
        for escopo in reversed(self.tabela_simbolos):
            if nome in escopo:
                return escopo[nome]
        self.erros.append(ErroSemantico(f"Variável '{nome}' não declarada", linha, coluna))
        return None

    def declarar_funcao(self, nome: str, tipo_retorno: Tipo, params: List[Tuple[str, Tipo]], linha: int, coluna: int):
        if nome in self.funcoes:
            self.erros.append(ErroSemantico(f"Função '{nome}' já declarada", linha, coluna))
        else:
            tipos_params = [t for _, t in params]
            self.funcoes[nome] = (tipo_retorno, tipos_params)

    def buscar_funcao(self, nome: str, linha: int, coluna: int) -> Optional[Tuple[Tipo, List[Tipo]]]:
        if nome in self.funcoes:
            return self.funcoes[nome]
        self.erros.append(ErroSemantico(f"Função '{nome}' não declarada", linha, coluna))
        return None

    def inferir_tipo(self, no: NoAST) -> Optional[Tipo]:
        if no is None:
            return None
        
        if isinstance(no, Literal):
            return no.tipo
        
        elif isinstance(no, Identificador):
            info = self.buscar_variavel(no.nome, no.linha, no.coluna)
            if info:
                return info[0]
            return None
        
        elif isinstance(no, ExpressaoBinaria):
            esq_tipo = self.inferir_tipo(no.esquerda)
            dir_tipo = self.inferir_tipo(no.direita)
            op = no.operador
            
            # Operações aritméticas
            if op in ['+', '-', '*', '/']:
                if esq_tipo in ['inteiro', 'flutuante'] and dir_tipo in ['inteiro', 'flutuante']:
                    if esq_tipo == 'flutuante' or dir_tipo == 'flutuante':
                        return 'flutuante'
                    return 'inteiro'
                else:
                    self.erros.append(ErroSemantico(
                        f"Operador '{op}' requer operandos numéricos", 
                        no.linha, no.coluna
                    ))
                    return None
            
            # Operações de comparação
            elif op in ['>', '<', '>=', '<=', '==', '!=']:
                if esq_tipo in ['inteiro', 'flutuante'] and dir_tipo in ['inteiro', 'flutuante']:
                    return 'logico'
                elif esq_tipo == dir_tipo and esq_tipo in ['inteiro', 'flutuante', 'cadeia', 'logico']:
                    return 'logico'
                else:
                    self.erros.append(ErroSemantico(
                        f"Comparação '{op}' entre '{esq_tipo}' e '{dir_tipo}' não é permitida", 
                        no.linha, no.coluna
                    ))
                    return None
            
            # Operações lógicas
            elif op in ['e', 'ou']:
                if esq_tipo == 'logico' and dir_tipo == 'logico':
                    return 'logico'
                else:
                    self.erros.append(ErroSemantico(
                        f"Operador lógico '{op}' requer operandos booleanos (recebeu '{esq_tipo}' e '{dir_tipo}')", 
                        no.linha, no.coluna
                    ))
                    return None
            
            # Concatenação de strings
            elif op == '&&':
                if esq_tipo == 'cadeia' and dir_tipo == 'cadeia':
                    return 'cadeia'
                else:
                    self.erros.append(ErroSemantico(
                        f"Concatenação '&&' requer strings (recebeu '{esq_tipo}' e '{dir_tipo}')", 
                        no.linha, no.coluna
                    ))
                    return None
            
            return None
        
        elif isinstance(no, ExpressaoUnaria):
            expr_tipo = self.inferir_tipo(no.expressao)
            op = no.operador
            
            if op == '!':
                if expr_tipo == 'logico':
                    return 'logico'
                else:
                    self.erros.append(ErroSemantico(
                        f"Negação '!' requer booleano (recebeu '{expr_tipo}')", 
                        no.linha, no.coluna
                    ))
                    return None
            
            elif op == '-':
                if expr_tipo in ['inteiro', 'flutuante']:
                    return expr_tipo
                else:
                    self.erros.append(ErroSemantico(
                        f"Menos unário '-' requer número (recebeu '{expr_tipo}')", 
                        no.linha, no.coluna
                    ))
                    return None
            
            elif op in ['++', '--']:
                if expr_tipo == 'inteiro':
                    return 'inteiro'
                else:
                    self.erros.append(ErroSemantico(
                        f"Operador '{op}' requer inteiro (recebeu '{expr_tipo}')", 
                        no.linha, no.coluna
                    ))
                    return None
            
            return None
        
        elif isinstance(no, ChamadaFuncao):
            info = self.buscar_funcao(no.nome, no.linha, no.coluna)
            if info:
                tipo_ret, tipos_params = info
                
                if len(no.argumentos) != len(tipos_params):
                    self.erros.append(ErroSemantico(
                        f"Função '{no.nome}' espera {len(tipos_params)} argumentos, mas recebeu {len(no.argumentos)}", 
                        no.linha, no.coluna
                    ))
                    return None
                
                for i, arg in enumerate(no.argumentos):
                    arg_tipo = self.inferir_tipo(arg)
                    if arg_tipo != tipos_params[i]:
                        self.erros.append(ErroSemantico(
                            f"Argumento {i+1} de '{no.nome}' deve ser '{tipos_params[i]}', mas é '{arg_tipo}'", 
                            no.linha, no.coluna
                        ))
                
                return tipo_ret
            return None
        
        return None

    def visitar(self, no: NoAST):
        if no is None:
            return
        
        if isinstance(no, Programa):
            for cmd in no.comandos:
                self.visitar(cmd)
                
        elif isinstance(no, DeclaracaoVariavel):
            self.declarar_variavel(no.nome, no.tipo, no.tamanho_array is not None, no.linha, no.coluna)
            if no.valor_inicial:
                init_tipo = self.inferir_tipo(no.valor_inicial)
                if init_tipo and init_tipo != no.tipo:
                    self.erros.append(ErroSemantico(
                        f"Inicialização de '{no.nome}' requer '{no.tipo}', mas é '{init_tipo}'", 
                        no.linha, no.coluna
                    ))
                    
        elif isinstance(no, DeclaracaoFuncao):
            params = [(p.nome, p.tipo) for p in no.parametros]
            self.declarar_funcao(no.nome, no.tipo_retorno, params, no.linha, no.coluna)
            self.entrar_escopo()
            for nome_param, tipo_param in params:
                self.declarar_variavel(nome_param, tipo_param, False, no.linha, no.coluna)
            for cmd in no.corpo:
                self.visitar(cmd)
            self.sair_escopo()
            
        elif isinstance(no, Atribuicao):
            var_info = self.buscar_variavel(no.nome, no.linha, no.coluna)
            if var_info:
                var_tipo, _ = var_info
                expr_tipo = self.inferir_tipo(no.expressao)
                if expr_tipo and expr_tipo != var_tipo:
                    self.erros.append(ErroSemantico(
                        f"Atribuição a '{no.nome}' requer '{var_tipo}', mas é '{expr_tipo}'", 
                        no.linha, no.coluna
                    ))
                    
        elif isinstance(no, ComandoSe):
            cond_tipo = self.inferir_tipo(no.condicao)
            if cond_tipo != 'logico':
                self.erros.append(ErroSemantico("Condição de 'se' deve ser lógica", no.linha, no.coluna))
            
            self.entrar_escopo()
            for cmd in no.bloco_verdadeiro:
                self.visitar(cmd)
            self.sair_escopo()
            
            if no.bloco_falso:
                self.entrar_escopo()
                for cmd in no.bloco_falso:
                    self.visitar(cmd)
                self.sair_escopo()
                
        elif isinstance(no, ComandoEnquanto):
            cond_tipo = self.inferir_tipo(no.condicao)
            if cond_tipo != 'logico':
                self.erros.append(ErroSemantico("Condição de 'enquanto' deve ser lógica", no.linha, no.coluna))
            
            self.entrar_escopo()
            for cmd in no.bloco:
                self.visitar(cmd)
            self.sair_escopo()
            
        elif isinstance(no, ComandoPara):
            self.entrar_escopo()
            if no.inicializacao:
                self.visitar(no.inicializacao)
            if no.condicao:
                cond_tipo = self.inferir_tipo(no.condicao)
                if cond_tipo != 'logico':
                    self.erros.append(ErroSemantico("Condição de 'para' deve ser lógica", no.linha, no.coluna))
            if no.incremento:
                self.visitar(no.incremento)
            for cmd in no.bloco:
                self.visitar(cmd)
            self.sair_escopo()
            
        elif isinstance(no, ComandoEscreva):
            self.inferir_tipo(no.expressao)
            
        elif isinstance(no, ComandoLeia):
            self.buscar_variavel(no.variavel, no.linha, no.coluna)
                
        elif isinstance(no, ChamadaFuncao):
            self.inferir_tipo(no)
            
        elif isinstance(no, ExpressaoBinaria) or isinstance(no, ExpressaoUnaria):
            self.inferir_tipo(no)
            
        elif isinstance(no, Identificador):
            self.buscar_variavel(no.nome, no.linha, no.coluna)

    def analisar(self, ast: Programa):
        """
        Realiza a análise semântica da AST
        
        Args:
            ast: Árvore sintática abstrata do programa
        """
        if ast is None:
            print("ERRO: AST é None!")
            return
        self.visitar(ast)

    def tem_erros(self) -> bool:
        return len(self.erros) > 0

    def imprimir_erros(self):
        if self.tem_erros():
            print("\n=== ERROS SEMÂNTICOS ENCONTRADOS ===")
            for erro in self.erros:
                print(erro)
        else:
            print("\n=== ANÁLISE SEMÂNTICA CONCLUÍDA SEM ERROS ===")