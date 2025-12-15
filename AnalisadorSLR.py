from dataclasses import dataclass
from typing import List, Optional, Any
import ply.yacc as yacc
from ply.lex import LexToken
import json

try:
    from AnalisadorLexico import AnalisadorLexico, Token, TipoToken
except ImportError:
    print("ERRO: Certifique-se de que AnalisadorLexico.py está no mesmo diretório!")
    exit(1)


# ============================================
# CLASSES DA ÁRVORE SINTÁTICA ABSTRATA (AST)
# ============================================

from AST import (
    NoAST, Programa, DeclaracaoVariavel, DeclaracaoFuncao, Parametro,
    Atribuicao, ComandoSe, ComandoEnquanto, ComandoPara, ComandoEscreva,
    ComandoLeia, ChamadaFuncao, ExpressaoBinaria, ExpressaoUnaria,
    Literal, Identificador
)


# ============================================
# ERRO SINTÁTICO
# ============================================

@dataclass
class ErroSintatico:
    mensagem: str
    linha: int
    coluna: int
    token_encontrado: Optional[str] = None

    def __str__(self):
        msg = f"Erro sintático [linha {self.linha}, coluna {self.coluna}]: {self.mensagem}"
        if self.token_encontrado:
            msg += f" | Token: {self.token_encontrado}"
        return msg


# ============================================
# WRAPPER PARA LEXER
# ============================================

class MyLexer:
    def __init__(self, tokens: List[Token]):
        self.tokens = iter(tokens)

    def token(self) -> Optional[LexToken]:
        try:
            t = next(self.tokens)
            if t.tipo == TipoToken.FIM_ARQUIVO:
                return None
            ply_t = LexToken()
            ply_t.type = t.tipo.value
            ply_t.value = t.lexema
            ply_t.lineno = t.linha
            ply_t.lexpos = t.coluna
            return ply_t
        except StopIteration:
            return None


# ============================================
# ANALISADOR SINTÁTICO LALR COM PLY
# ============================================

class AnalisadorSintatico:
    tokens = (
        'IDENTIFICADOR', 'INTEIRO', 'FLUTUANTE', 'CADEIA', 'BOOLEANO',
        'SE', 'SENAO', 'PARA', 'FACA', 'ENQUANTO', 'ESCREVA', 'LEIA',
        'TIPO_INTEIRO', 'TIPO_FLUTUANTE', 'TIPO_LOGICO', 'TIPO_CADEIA',
        'INICIO_BLOCO', 'FIM_BLOCO',
        'ADICAO', 'SUBTRACAO', 'MULTIPLICACAO', 'DIVISAO',
        'PARENTESE_ESQ', 'PARENTESE_DIR', 'COLCHETE_ESQ', 'COLCHETE_DIR',
        'MAIOR', 'MENOR', 'MAIOR_IGUAL', 'MENOR_IGUAL',
        'ATRIBUICAO', 'CONCATENACAO', 'INCREMENTO', 'DECREMENTO',
        'PONTO_VIRGULA', 'VIRGULA',
        'IGUALDADE', 'DIFERENTE', 'NEGACAO', 'LOGICO_E', 'LOGICO_OU'
    )

    precedence = (
        ('left', 'LOGICO_OU'),
        ('left', 'LOGICO_E'),
        ('left', 'IGUALDADE', 'DIFERENTE'),
        ('left', 'MAIOR', 'MENOR', 'MAIOR_IGUAL', 'MENOR_IGUAL'),
        ('left', 'ADICAO', 'SUBTRACAO', 'CONCATENACAO'),
        ('left', 'MULTIPLICACAO', 'DIVISAO'),
        ('right', 'NEGACAO'),
    )

    def __init__(self):
        self.erros: List[ErroSintatico] = []
        self.parser = yacc.yacc(module=self, debug=False)

    # ==================== REGRAS DA GRAMÁTICA ====================

    def p_program(self, p):
        '''program : INICIO_BLOCO statement_list FIM_BLOCO
                   | statement_list'''
        if len(p) == 4:
            p[0] = Programa(p.lineno(1), p.lexpos(1), p[2])
        else:
            p[0] = Programa(1, 1, p[1])

    def p_statement_list(self, p):
        '''statement_list : statement statement_list
                          | empty'''
        if len(p) == 3:
            p[0] = [p[1]] + p[2]
        else:
            p[0] = []

    def p_statement(self, p):
        '''statement : declaration
                     | assignment
                     | if_stmt
                     | while_stmt
                     | for_stmt
                     | write_stmt
                     | read_stmt
                     | function_call
                     | function_decl'''
        p[0] = p[1]

    def p_block(self, p):
        '''block : INICIO_BLOCO statement_list FIM_BLOCO
                 | statement'''
        if len(p) == 4:
            p[0] = p[2]
        else:
            p[0] = [p[1]]

    def p_declaration(self, p):
        '''declaration : type IDENTIFICADOR
                       | type IDENTIFICADOR ATRIBUICAO expression
                       | type IDENTIFICADOR COLCHETE_ESQ INTEIRO COLCHETE_DIR'''
        tipo = p[1]
        nome = p[2]
        linha = p.lineno(1)
        coluna = p.lexpos(1)
        if len(p) == 3:
            p[0] = DeclaracaoVariavel(linha, coluna, tipo, nome)
        elif len(p) == 5 and p[3] == '=':
            p[0] = DeclaracaoVariavel(linha, coluna, tipo, nome, valor_inicial=p[4])
        else:
            tamanho = int(p[4])
            p[0] = DeclaracaoVariavel(linha, coluna, tipo, nome, tamanho_array=tamanho)

    def p_type(self, p):
        '''type : TIPO_INTEIRO
                | TIPO_FLUTUANTE
                | TIPO_LOGICO
                | TIPO_CADEIA'''
        p[0] = p[1]

    def p_assignment(self, p):
        'assignment : IDENTIFICADOR ATRIBUICAO expression'
        p[0] = Atribuicao(p.lineno(1), p.lexpos(1), p[1], p[3])

    def p_if_stmt(self, p):
        '''if_stmt : SE PARENTESE_ESQ expression PARENTESE_DIR FACA block SENAO block
                   | SE PARENTESE_ESQ expression PARENTESE_DIR FACA block'''
        linha = p.lineno(1)
        coluna = p.lexpos(1)
        cond = p[3]
        btrue = p[6]
        bfalse = p[8] if len(p) == 9 else None
        p[0] = ComandoSe(linha, coluna, cond, btrue, bfalse)

    def p_while_stmt(self, p):
        'while_stmt : ENQUANTO PARENTESE_ESQ expression PARENTESE_DIR FACA block'
        p[0] = ComandoEnquanto(p.lineno(1), p.lexpos(1), p[3], p[6])

    def p_for_stmt(self, p):
        'for_stmt : PARA PARENTESE_ESQ initialization PONTO_VIRGULA condition PONTO_VIRGULA increment PARENTESE_DIR FACA block'
        p[0] = ComandoPara(p.lineno(1), p.lexpos(1), p[3], p[5], p[7], p[10])

    def p_initialization(self, p):
        '''initialization : declaration
                          | assignment
                          | empty'''
        p[0] = p[1] if len(p) > 1 else None

    def p_condition(self, p):
        '''condition : expression
                     | empty'''
        p[0] = p[1] if len(p) > 1 else None

    def p_increment(self, p):
        '''increment : assignment
                     | INCREMENTO IDENTIFICADOR
                     | DECREMENTO IDENTIFICADOR
                     | IDENTIFICADOR INCREMENTO
                     | IDENTIFICADOR DECREMENTO
                     | empty'''
        if len(p) == 2:
            p[0] = None
        elif len(p) == 3:
            if p[1] in ['++', '--']:
                iden = Identificador(p.lineno(2), p.lexpos(2), p[2])
                p[0] = ExpressaoUnaria(p.lineno(1), p.lexpos(1), p[1], iden)
            else:
                iden = Identificador(p.lineno(1), p.lexpos(1), p[1])
                p[0] = ExpressaoUnaria(p.lineno(2), p.lexpos(2), p[2], iden)
        else:
            p[0] = p[1]

    def p_write_stmt(self, p):
        'write_stmt : ESCREVA PARENTESE_ESQ expression PARENTESE_DIR'
        p[0] = ComandoEscreva(p.lineno(1), p.lexpos(1), p[3])

    def p_read_stmt(self, p):
        'read_stmt : LEIA PARENTESE_ESQ IDENTIFICADOR PARENTESE_DIR'
        p[0] = ComandoLeia(p.lineno(1), p.lexpos(1), p[3])

    def p_function_decl(self, p):
        'function_decl : type IDENTIFICADOR PARENTESE_ESQ param_list PARENTESE_DIR block'
        p[0] = DeclaracaoFuncao(p.lineno(1), p.lexpos(1), p[1], p[2], p[4], p[6])

    def p_param_list(self, p):
        '''param_list : param VIRGULA param_list
                      | param
                      | empty'''
        if len(p) == 4:
            p[0] = [p[1]] + p[3]
        elif len(p) == 2:
            p[0] = [p[1]]
        else:
            p[0] = []

    def p_param(self, p):
        'param : type IDENTIFICADOR'
        p[0] = Parametro(p.lineno(1), p.lexpos(1), p[1], p[2])

    def p_function_call(self, p):
        'function_call : IDENTIFICADOR PARENTESE_ESQ arg_list PARENTESE_DIR'
        p[0] = ChamadaFuncao(p.lineno(1), p.lexpos(1), p[1], p[3])

    def p_arg_list(self, p):
        '''arg_list : expression VIRGULA arg_list
                    | expression
                    | empty'''
        if len(p) == 4:
            p[0] = [p[1]] + p[3]
        elif len(p) == 2:
            p[0] = [p[1]]
        else:
            p[0] = []

    def p_expression(self, p):
        'expression : logical_or'
        p[0] = p[1]

    def p_logical_or(self, p):
        '''logical_or : logical_or LOGICO_OU logical_and
                      | logical_and'''
        if len(p) == 4:
            p[0] = ExpressaoBinaria(p.lineno(2), p.lexpos(2), p[1], 'ou', p[3])
        else:
            p[0] = p[1]

    def p_logical_and(self, p):
        '''logical_and : logical_and LOGICO_E equality
                       | equality'''
        if len(p) == 4:
            p[0] = ExpressaoBinaria(p.lineno(2), p.lexpos(2), p[1], 'e', p[3])
        else:
            p[0] = p[1]

    def p_equality(self, p):
        '''equality : equality IGUALDADE relational
                    | equality DIFERENTE relational
                    | relational'''
        if len(p) == 4:
            p[0] = ExpressaoBinaria(p.lineno(2), p.lexpos(2), p[1], p[2], p[3])
        else:
            p[0] = p[1]

    def p_relational(self, p):
        '''relational : relational MAIOR additive
                      | relational MENOR additive
                      | relational MAIOR_IGUAL additive
                      | relational MENOR_IGUAL additive
                      | additive'''
        if len(p) == 4:
            p[0] = ExpressaoBinaria(p.lineno(2), p.lexpos(2), p[1], p[2], p[3])
        else:
            p[0] = p[1]

    def p_additive(self, p):
        '''additive : additive ADICAO multiplicative
                    | additive SUBTRACAO multiplicative
                    | additive CONCATENACAO multiplicative
                    | multiplicative'''
        if len(p) == 4:
            p[0] = ExpressaoBinaria(p.lineno(2), p.lexpos(2), p[1], p[2], p[3])
        else:
            p[0] = p[1]

    def p_multiplicative(self, p):
        '''multiplicative : multiplicative MULTIPLICACAO unary
                          | multiplicative DIVISAO unary
                          | unary'''
        if len(p) == 4:
            p[0] = ExpressaoBinaria(p.lineno(2), p.lexpos(2), p[1], p[2], p[3])
        else:
            p[0] = p[1]

    def p_unary(self, p):
        '''unary : NEGACAO unary
                 | SUBTRACAO unary
                 | INCREMENTO IDENTIFICADOR
                 | DECREMENTO IDENTIFICADOR
                 | IDENTIFICADOR INCREMENTO
                 | IDENTIFICADOR DECREMENTO
                 | primary'''
        if len(p) == 3:
            if p[1] in ['!', '-']:
                p[0] = ExpressaoUnaria(p.lineno(1), p.lexpos(1), p[1], p[2])
            elif p[1] in ['++', '--']:
                iden = Identificador(p.lineno(2), p.lexpos(2), p[2])
                p[0] = ExpressaoUnaria(p.lineno(1), p.lexpos(1), p[1], iden)
            else:
                iden = Identificador(p.lineno(1), p.lexpos(1), p[1])
                p[0] = ExpressaoUnaria(p.lineno(2), p.lexpos(2), p[2], iden)
        else:
            p[0] = p[1]

    def p_primary(self, p):
        '''primary : IDENTIFICADOR
                   | literal
                   | PARENTESE_ESQ expression PARENTESE_DIR
                   | function_call'''
        if len(p) == 2:
            if isinstance(p[1], str) and p.slice[1].type == 'IDENTIFICADOR':
                p[0] = Identificador(p.lineno(1), p.lexpos(1), p[1])
            else:
                p[0] = p[1]
        else:
            p[0] = p[2]

    def p_literal(self, p):
        '''literal : INTEIRO
                   | FLUTUANTE
                   | CADEIA
                   | BOOLEANO'''
        if p.slice[1].type == 'INTEIRO':
            valor = int(p[1])
            typ = "inteiro"
        elif p.slice[1].type == 'FLUTUANTE':
            valor = float(p[1])
            typ = "flutuante"
        elif p.slice[1].type == 'CADEIA':
            valor = p[1]
            typ = "cadeia"
        else:
            valor = p[1].lower() == "verdadeiro"
            typ = "logico"
        p[0] = Literal(p.lineno(1), p.lexpos(1), valor, typ)

    def p_empty(self, p):
        'empty :'
        pass

    def p_error(self, p):
        if p:
            self.erros.append(ErroSintatico(
                "Erro de sintaxe",
                p.lineno,
                p.lexpos,
                token_encontrado=p.value
            ))
        else:
            self.erros.append(ErroSintatico("Fim de arquivo inesperado", 0, 0))

    # ==================== MÉTODOS PÚBLICOS ====================

    def analisar(self, tokens: List[Token]) -> Programa:
        lexer = MyLexer(tokens)
        return self.parser.parse(lexer=lexer)

    def tem_erros(self) -> bool:
        return len(self.erros) > 0

    def obter_erros(self) -> List[ErroSintatico]:
        return self.erros

    def imprimir_erros(self):
        if self.tem_erros():
            print("\n=== ERROS SINTÁTICOS ENCONTRADOS ===")
            for e in self.erros:
                print(e)
                print()
        else:
            print("\n=== ANÁLISE SINTÁTICA CONCLUÍDA SEM ERROS ===")


# ============================================
# IMPRESSÃO BONITA DA AST + EXPORTAÇÃO JSON
# ============================================

def imprimir_ast(no: Optional[NoAST], nivel: int = 0):
    if no is None:
        return

    prefixo = "│   " * (nivel - 1) + ("├── " if nivel > 0 else "")
    print(f"{prefixo}{type(no).__name__}")

    filhos = []
    if isinstance(no, Programa):
        filhos = [(f"comando[{i}]", cmd) for i, cmd in enumerate(no.comandos)]
    elif isinstance(no, DeclaracaoVariavel):
        if no.valor_inicial:
            filhos = [("valor_inicial", no.valor_inicial)]
        print(f"{prefixo}    tipo: {no.tipo} | nome: {no.nome}" + (f" | array[{no.tamanho_array}]" if no.tamanho_array else ""))
    elif isinstance(no, DeclaracaoFuncao):
        filhos = [(f"param[{i}]", p) for i, p in enumerate(no.parametros)]
        filhos += [(f"corpo[{i}]", c) for i, c in enumerate(no.corpo)]
        print(f"{prefixo}    retorno: {no.tipo_retorno} | nome: {no.nome}")
    elif isinstance(no, Atribuicao):
        filhos = [("expressão", no.expressao)]
        print(f"{prefixo}    variável: {no.nome}")
    elif isinstance(no, ComandoSe):
        filhos = [("condição", no.condicao)]
        filhos += [(f"então[{i}]", c) for i, c in enumerate(no.bloco_verdadeiro)]
        if no.bloco_falso:
            filhos += [(f"senao[{i}]", c) for i, c in enumerate(no.bloco_falso)]
    elif isinstance(no, ComandoEnquanto):
        filhos = [("condição", no.condicao)] + [(f"bloco[{i}]", c) for i, c in enumerate(no.bloco)]
    elif isinstance(no, ComandoPara):
        if no.inicializacao: filhos.append(("inicialização", no.inicializacao))
        if no.condicao: filhos.append(("condição", no.condicao))
        if no.incremento: filhos.append(("incremento", no.incremento))
        filhos += [(f"bloco[{i}]", c) for i, c in enumerate(no.bloco)]
    elif isinstance(no, ComandoEscreva):
        filhos = [("expressão", no.expressao)]
    elif isinstance(no, ChamadaFuncao):
        filhos = [(f"arg[{i}]", a) for i, a in enumerate(no.argumentos)]
        print(f"{prefixo}    função: {no.nome}")
    elif isinstance(no, ExpressaoBinaria):
        filhos = [("esquerda", no.esquerda), ("direita", no.direita)]
        print(f"{prefixo}    operador: {no.operador}")
    elif isinstance(no, ExpressaoUnaria):
        filhos = [("expressão", no.expressao)]
        print(f"{prefixo}    operador: {no.operador}")
    elif isinstance(no, Literal):
        print(f"{prefixo}    valor: {no.valor} (tipo: {no.tipo})")
        return
    elif isinstance(no, Identificador):
        print(f"{prefixo}    nome: {no.nome}")
        return

    for nome, filho in filhos:
        print(f"{prefixo}│   {nome}:")
        imprimir_ast(filho, nivel + 1)


def ast_para_dict(no: Optional[NoAST]) -> Optional[dict]:
    if no is None:
        return None

    d = {"tipo": type(no).__name__, "linha": no.linha, "coluna": no.coluna}

    if isinstance(no, Programa):
        d["comandos"] = [ast_para_dict(c) for c in no.comandos]
    elif isinstance(no, DeclaracaoVariavel):
        d["tipo_var"] = no.tipo
        d["nome"] = no.nome
        d["tamanho_array"] = no.tamanho_array
        d["valor_inicial"] = ast_para_dict(no.valor_inicial)
    elif isinstance(no, DeclaracaoFuncao):
        d["tipo_retorno"] = no.tipo_retorno
        d["nome"] = no.nome
        d["parametros"] = [ast_para_dict(p) for p in no.parametros]
        d["corpo"] = [ast_para_dict(c) for c in no.corpo]
    elif isinstance(no, Atribuicao):
        d["nome"] = no.nome
        d["expressao"] = ast_para_dict(no.expressao)
    elif isinstance(no, ComandoSe):
        d["condicao"] = ast_para_dict(no.condicao)
        d["bloco_verdadeiro"] = [ast_para_dict(c) for c in no.bloco_verdadeiro]
        d["bloco_falso"] = [ast_para_dict(c) for c in no.bloco_falso] if no.bloco_falso else None
    elif isinstance(no, ComandoEnquanto):
        d["condicao"] = ast_para_dict(no.condicao)
        d["bloco"] = [ast_para_dict(c) for c in no.bloco]
    elif isinstance(no, ComandoPara):
        d["inicializacao"] = ast_para_dict(no.inicializacao)
        d["condicao"] = ast_para_dict(no.condicao)
        d["incremento"] = ast_para_dict(no.incremento)
        d["bloco"] = [ast_para_dict(c) for c in no.bloco]
    elif isinstance(no, ComandoEscreva):
        d["expressao"] = ast_para_dict(no.expressao)
    elif isinstance(no, ComandoLeia):
        d["variavel"] = no.variavel
    elif isinstance(no, ChamadaFuncao):
        d["nome"] = no.nome
        d["argumentos"] = [ast_para_dict(a) for a in no.argumentos]
    elif isinstance(no, ExpressaoBinaria):
        d["esquerda"] = ast_para_dict(no.esquerda)
        d["operador"] = no.operador
        d["direita"] = ast_para_dict(no.direita)
    elif isinstance(no, ExpressaoUnaria):
        d["operador"] = no.operador
        d["expressao"] = ast_para_dict(no.expressao)
    elif isinstance(no, Literal):
        d["valor"] = no.valor
        d["tipo"] = no.tipo
    elif isinstance(no, Identificador):
        d["nome"] = no.nome
    elif isinstance(no, Parametro):
        d["tipo"] = no.tipo
        d["nome"] = no.nome

    return d


# ============================================
# EXEMPLO DE USO
# ============================================

if __name__ == "__main__":
    codigo_exemplo = """
    inicio
        inteiro x = 10
        flutuante y = 3.14
        cadeia msg = "Olá"
        logico ativo = verdadeiro

        se (x > 15 e y != 0) faca
        inicio
            escreva("Maior")
        fim
        senao
            escreva("Menor")

        inteiro soma(inteiro a, inteiro b)
        inicio
            escreva(a + b)
        fim

        soma(5, 7)
    fim
    """

    print("="*60)
    print("ANÁLISE LÉXICA")
    print("="*60)

    lex = AnalisadorLexico(codigo_exemplo)
    tokens = lex.analisar()

    if lex.tem_erros():
        lex.imprimir_erros()
        exit(1)

    print(f"✅ Análise léxica concluída: {len(tokens)} tokens")

    print("\n" + "="*60)
    print("ANÁLISE SINTÁTICA")
    print("="*60)

    parser = AnalisadorSintatico()
    ast = parser.analisar(tokens)

    # Logo após: ast = parser.analisar(tokens) 
    print(f"\n=== DEBUG: Verificando AST ===")
    print(f"Tipo da AST: {type(ast)}")
    print(f"AST é None? {ast is None}")
    if ast:
        print(f"Número de comandos: {len(ast.comandos)}")
        print(f"Comandos: {[type(c).__name__ for c in ast.comandos]}")



    parser.imprimir_erros()

    if not parser.tem_erros():
        print("\n✅ Análise sintática concluída com sucesso!")

        print("\n" + "="*60)
        print("ÁRVORE SINTÁTICA ABSTRATA")
        print("="*60)
        imprimir_ast(ast)

        print("\n" + "="*60)
        print("EXPORTANDO PARA ast.json")
        print("="*60)
        with open("ast.json", "w", encoding="utf-8") as f:
            json.dump(ast_para_dict(ast), f, indent=2, ensure_ascii=False)
        print("✅ ast.json salvo com sucesso!")    
        
        
    from AnalisadorSemantico import AnalisadorSemantico
    # Após construir ast
    print("\n" + "="*60)
    print("ANÁLISE SEMÂNTICA")
    print("="*60)
    semantico = AnalisadorSemantico()
    semantico.analisar(ast)
    semantico.imprimir_erros()