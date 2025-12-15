# Geração de código assembly MIPS compatível com o simulador MARS

from typing import List, Optional
from AST import (
    NoAST, Programa, DeclaracaoVariavel, DeclaracaoFuncao, Parametro,
    Atribuicao, ComandoSe, ComandoEnquanto, ComandoPara, ComandoEscreva,
    ComandoLeia, ChamadaFuncao, ExpressaoBinaria, ExpressaoUnaria,
    Literal, Identificador
)

class GeradorCodigoMIPS:
    def __init__(self):
        self.codigo: List[str] = []
        self.temp_count = 0          # Para gerar $t0, $t1, ...
        self.label_count = 0         # Para gerar labels L0, L1, ...
        self.var_map: dict = {}      # nome_da_var -> label_na_memoria
        self.func_map: dict = {}     # nome_da_funcao -> label

        # Começa com a seção .data
        self.codigo.append(".data")
        self.codigo.append("")  # linha em branco

    def novo_temp(self) -> str:
        """Gera um novo registrador temporário ($t0 até $t9)"""
        reg = f"$t{self.temp_count % 10}"
        self.temp_count += 1
        return reg

    def nova_label(self) -> str:
        """Gera uma label única (L0, L1, ...)"""
        label = f"L{self.label_count}"
        self.label_count += 1
        return label

    def alocar_variavel(self, nome: str, tipo: str, é_array: bool = False):
        """Aloca espaço na .data para uma variável"""
        if nome in self.var_map:
            return  # já alocada (ex: parâmetros de função)

        label = nome
        self.var_map[nome] = label

        if é_array:
            # Array simples: reservamos 40 bytes (10 inteiros, por exemplo)
            self.codigo.append(f"{label}: .space 40")
        else:
            if tipo in ['inteiro', 'logico']:
                self.codigo.append(f"{label}: .word 0")
            elif tipo == 'flutuante':
                self.codigo.append(f"{label}: .float 0.0")
            elif tipo == 'cadeia':
                self.codigo.append(f"{label}: .asciiz \"\"")
            else:
                self.codigo.append(f"{label}: .word 0")  # fallback

    def gerar(self, ast: Programa) -> str:
        """Gera o código MIPS completo a partir da AST"""
        self.visitar(ast)

        # Adiciona a seção .text e o ponto de entrada
        self.codigo.append("")
        self.codigo.append(".text")
        self.codigo.append("main:")
        
        # O código do programa principal já foi gerado dentro de visitar(Programa)
        # Só adicionamos a saída do programa
        self.codigo.append("    li $v0, 10")
        self.codigo.append("    syscall")

        return "\n".join(self.codigo)

    def visitar(self, no: Optional[NoAST]):
        if no is None:
            return None

        # Programa
        if isinstance(no, Programa):
            for cmd in no.comandos:
                self.visitar(cmd)

        # Declaração de variável
        elif isinstance(no, DeclaracaoVariavel):
            self.alocar_variavel(no.nome, no.tipo, no.tamanho_array is not None)
            if no.valor_inicial:
                reg = self.visitar(no.valor_inicial)
                label = self.var_map[no.nome]
                if no.tipo in ['inteiro', 'logico']:
                    self.codigo.append(f"    sw {reg}, {label}")
                elif no.tipo == 'flutuante':
                    self.codigo.append(f"    s.s {reg}, {label}")
                # cadeia ignorada por simplicidade

        # Atribuição
        elif isinstance(no, Atribuicao):
            reg = self.visitar(no.expressao)
            label = self.var_map[no.nome]
            self.codigo.append(f"    sw {reg}, {label}")  # assume inteiro

        # Literal
        elif isinstance(no, Literal):
            reg = self.novo_temp()
            if no.tipo == 'inteiro':
                self.codigo.append(f"    li {reg}, {no.valor}")
            elif no.tipo == 'flutuante':
                self.codigo.append(f"    li.s {reg}, {no.valor}")
            elif no.tipo == 'logico':
                val = 1 if no.valor else 0
                self.codigo.append(f"    li {reg}, {val}")
            elif no.tipo == 'cadeia':
                # Simplificado: não gera load de string aqui
                self.codigo.append(f"    la {reg}, {no.valor}")  # precisa alocar string antes
            return reg

        # Identificador (leitura de variável)
        elif isinstance(no, Identificador):
            reg = self.novo_temp()
            label = self.var_map[no.nome]
            self.codigo.append(f"    lw {reg}, {label}")
            return reg

        # Expressão binária
        elif isinstance(no, ExpressaoBinaria):
            reg_esq = self.visitar(no.esquerda)
            reg_dir = self.visitar(no.direita)
            reg_res = self.novo_temp()

            op = no.operador
            if op == '+':
                self.codigo.append(f"    add {reg_res}, {reg_esq}, {reg_dir}")
            elif op == '-':
                self.codigo.append(f"    sub {reg_res}, {reg_esq}, {reg_dir}")
            elif op == '*':
                self.codigo.append(f"    mul {reg_res}, {reg_esq}, {reg_dir}")
            elif op == '/':
                self.codigo.append(f"    div {reg_res}, {reg_esq}, {reg_dir}")
            elif op == '>':
                self.codigo.append(f"    slt {reg_res}, {reg_dir}, {reg_esq}")  # dir < esq → res=1
            elif op == '<':
                self.codigo.append(f"    slt {reg_res}, {reg_esq}, {reg_dir}")
            elif op == '>=':
                self.codigo.append(f"    slt {reg_res}, {reg_esq}, {reg_dir}")  # inverte e nega
                self.codigo.append(f"    xori {reg_res}, {reg_res}, 1")
            elif op == '<=':
                self.codigo.append(f"    slt {reg_res}, {reg_dir}, {reg_esq}")
                self.codigo.append(f"    xori {reg_res}, {reg_res}, 1")
            elif op == '==':
                self.codigo.append(f"    seq {reg_res}, {reg_esq}, {reg_dir}")
            elif op == '!=':
                self.codigo.append(f"    sne {reg_res}, {reg_esq}, {reg_dir}")
            elif op == 'e':
                self.codigo.append(f"    and {reg_res}, {reg_esq}, {reg_dir}")
            elif op == 'ou':
                self.codigo.append(f"    or {reg_res}, {reg_esq}, {reg_dir}")
            elif op == '&&':
                # Concatenação de strings: simplificado (não implementado completamente)
                pass

            return reg_res

        # Expressão unária
        elif isinstance(no, ExpressaoUnaria):
            reg_expr = self.visitar(no.expressao)
            reg_res = self.novo_temp()

            if no.operador == '!':
                self.codigo.append(f"    li {reg_res}, 1")
                self.codigo.append(f"    xor {reg_res}, {reg_expr}, {reg_res}")
            elif no.operador == '-':
                self.codigo.append(f"    neg {reg_res}, {reg_expr}")
            elif no.operador in ['++', '--']:
                # Assume que a expressão é um Identificador
                nome_var = no.expressao.nome
                label = self.var_map[nome_var]
                self.codigo.append(f"    lw {reg_res}, {label}")
                if no.operador == '++':
                    self.codigo.append(f"    addi {reg_res}, {reg_res}, 1")
                else:
                    self.codigo.append(f"    addi {reg_res}, {reg_res}, -1")
                self.codigo.append(f"    sw {reg_res}, {label}")

            return reg_res

        # Comando se
        elif isinstance(no, ComandoSe):
            reg_cond = self.visitar(no.condicao)
            label_falso = self.nova_label()
            label_fim = self.nova_label()

            self.codigo.append(f"    beq {reg_cond}, $zero, {label_falso}")

            for cmd in no.bloco_verdadeiro:
                self.visitar(cmd)

            self.codigo.append(f"    j {label_fim}")
            self.codigo.append(f"{label_falso}:")

            if no.bloco_falso:
                for cmd in no.bloco_falso:
                    self.visitar(cmd)

            self.codigo.append(f"{label_fim}:")

        # Comando enquanto
        elif isinstance(no, ComandoEnquanto):
            label_inicio = self.nova_label()
            label_fim = self.nova_label()

            self.codigo.append(f"{label_inicio}:")
            reg_cond = self.visitar(no.condicao)
            self.codigo.append(f"    beq {reg_cond}, $zero, {label_fim}")

            for cmd in no.bloco:
                self.visitar(cmd)

            self.codigo.append(f"    j {label_inicio}")
            self.codigo.append(f"{label_fim}:")

        # Comando para
        elif isinstance(no, ComandoPara):
            label_inicio = self.nova_label()
            label_incremento = self.nova_label()
            label_fim = self.nova_label()

            # Inicialização
            if no.inicializacao:
                self.visitar(no.inicializacao)

            self.codigo.append(f"{label_inicio}:")
            # Condição
            if no.condicao:
                reg_cond = self.visitar(no.condicao)
                self.codigo.append(f"    beq {reg_cond}, $zero, {label_fim}")

            # Bloco
            for cmd in no.bloco:
                self.visitar(cmd)

            self.codigo.append(f"{label_incremento}:")
            # Incremento
            if no.incremento:
                self.visitar(no.incremento)

            self.codigo.append(f"    j {label_inicio}")
            self.codigo.append(f"{label_fim}:")

        # Escreva
        elif isinstance(no, ComandoEscreva):
            reg = self.visitar(no.expressao)
            self.codigo.append("    li $v0, 1")        # print_int
            self.codigo.append(f"    move $a0, {reg}")
            self.codigo.append("    syscall")
            
            # Quebra de linha
            self.codigo.append("    li $v0, 11")       # print_char
            self.codigo.append("    li $a0, 10")        # código ASCII do \n
            self.codigo.append("    syscall")

        # Leia
        elif isinstance(no, ComandoLeia):
            self.codigo.append("    li $v0, 5")        # read_int
            self.codigo.append("    syscall")
            label = self.var_map[no.variavel]
            self.codigo.append(f"    sw $v0, {label}")

        # Declaração de função
        elif isinstance(no, DeclaracaoFuncao):
            label = no.nome
            self.func_map[no.nome] = label
            self.codigo.append("")
            self.codigo.append(f"{label}:")
            
            # Salva parâmetros nos argumentos $a0-$a3 (máx 4)
            for i, param in enumerate(no.parametros[:4]):
                self.alocar_variavel(param.nome, param.tipo)
                self.codigo.append(f"    sw $a{i}, {self.var_map[param.nome]}")

            # Corpo da função
            for cmd in no.corpo:
                self.visitar(cmd)

            # Retorno (simples: jr $ra)
            self.codigo.append("    jr $ra")

        # Chamada de função
        elif isinstance(no, ChamadaFuncao):
            # Passa argumentos (máx 4)
            for i, arg in enumerate(no.argumentos[:4]):
                reg = self.visitar(arg)
                self.codigo.append(f"    move $a{i}, {reg}")

            label = self.func_map[no.nome]
            self.codigo.append(f"    jal {label}")

            # Valor de retorno vem em $v0
            reg_res = self.novo_temp()
            self.codigo.append(f"    move {reg_res}, $v0")
            return reg_res

        # Caso não tratado (evita erro silencioso)
        else:
            self.codigo.append(f"    # Nó não tratado: {type(no).__name__}")
