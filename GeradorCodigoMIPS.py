# Novo arquivo: GeradorCodigoMIPS.py
# Coloque isso no mesmo diretório dos outros arquivos (AnalisadorSLR.py, AST.py, etc.)
# Ele será chamado após a análise semântica no __main__ de AnalisadorSLR.py

from typing import List, Dict
from dataclasses import dataclass
from AST import (
    NoAST, Programa, DeclaracaoVariavel, DeclaracaoFuncao, Parametro,
    Atribuicao, ComandoSe, ComandoEnquanto, ComandoPara, ComandoEscreva,
    ComandoLeia, ChamadaFuncao, ExpressaoBinaria, ExpressaoUnaria,
    Literal, Identificador
)

class GeradorCodigoMIPS:
    def __init__(self):
        self.codigo = []  # Lista de linhas de assembly
        self.temp_count = 0  # Contador para registradores temporários
        self.label_count = 0  # Contador para labels (ex.: if, loops)
        self.var_map = {}  # Mapeia variáveis para endereços na .data
        self.var_count = 0  # Contador para alocação de memória
        self.func_map = {}  # Mapeia funções para labels
        
        # Registradores disponíveis (usamos $t0-$t9 para temps)
        self.regs = [f"$t{i}" for i in range(10)]
        
        # Seção .data inicial
        self.codigo.append(".data")
    
    def novo_temp(self) -> str:
        """Retorna um registrador temporário disponível"""
        reg = self.regs[self.temp_count % len(self.regs)]
        self.temp_count += 1
        return reg
    
    def nova_label(self) -> str:
        """Gera uma nova label única"""
        label = f"L{self.label_count}"
        self.label_count += 1
        return label
    
    def alocar_variavel(self, nome: str, tipo: str, é_array: bool = False):
        """Aloca espaço na .data para uma variável"""
        if é_array:
            # Para arrays, assumimos tamanho fixo, mas na AST é opcional; por simplicidade, usamos word para inteiros
            self.codigo.append(f"{nome}: .space 40")  # Exemplo: 10 inteiros * 4 bytes
        else:
            if tipo == 'inteiro' or tipo == 'logico':
                self.codigo.append(f"{nome}: .word 0")
            elif tipo == 'flutuante':
                self.codigo.append(f"{nome}: .float 0.0")
            elif tipo == 'cadeia':
                self.codigo.append(f"{nome}: .asciiz \"\"")
        self.var_map[nome] = nome  # Label é o endereço
    
    def gerar(self, ast: Programa) -> str:
        """Gera o código MIPS a partir da AST"""
        self.visitar(ast)
        self.codigo.append("\n.text")
        self.codigo.append("main:")
        # Código principal já está na lista; assumimos que o programa é o main
        # Adicionar exit no final
        self.codigo.append("li $v0, 10")
        self.codigo.append("syscall")
        return "\n".join(self.codigo)
    
    def visitar(self, no: NoAST):
        if isinstance(no, Programa):
            for cmd in no.comandos:
                self.visitar(cmd)
        
        elif isinstance(no, DeclaracaoVariavel):
            self.alocar_variavel(no.nome, no.tipo, no.tamanho_array is not None)
            if no.valor_inicial:
                reg = self.visitar(no.valor_inicial)
                addr = self.var_map[no.nome]
                if no.tipo in ['inteiro', 'logico']:
                    self.codigo.append(f"sw {reg}, {addr}")
                elif no.tipo == 'flutuante':
                    self.codigo.append(f"s.s {reg}, {addr}")
                # Para cadeia, mais complexo; ignorar por agora ou usar strcpy
        
        elif isinstance(no, Atribuicao):
            reg = self.visitar(no.expressao)
            addr = self.var_map[no.nome]
            # Assumir tipo inteiro por simplicidade; ajustar por tipo
            self.codigo.append(f"sw {reg}, {addr}")
        
        elif isinstance(no, Literal):
            reg = self.novo_temp()
            if no.tipo == 'inteiro':
                self.codigo.append(f"li {reg}, {no.valor}")
            elif no.tipo == 'flutuante':
                self.codigo.append(f"li.s {reg}, {no.valor}")
            # Para logico: 1/0
            elif no.tipo == 'logico':
                val = 1 if no.valor else 0
                self.codigo.append(f"li {reg}, {val}")
            # Cadeia: mais complexo, alocar e la
            return reg
        
        elif isinstance(no, Identificador):
            reg = self.novo_temp()
            addr = self.var_map[no.nome]
            self.codigo.append(f"lw {reg}, {addr}")
            return reg
        
        elif isinstance(no, ExpressaoBinaria):
            esq_reg = self.visitar(no.esquerda)
            dir_reg = self.visitar(no.direita)
            res_reg = self.novo_temp()
            op = no.operador
            if op == '+':
                self.codigo.append(f"add {res_reg}, {esq_reg}, {dir_reg}")
            elif op == '-':
                self.codigo.append(f"sub {res_reg}, {esq_reg}, {dir_reg}")
            elif op == '*':
                self.codigo.append(f"mul {res_reg}, {esq_reg}, {dir_reg}")
            elif op == '/':
                self.codigo.append(f"div {res_reg}, {esq_reg}, {dir_reg}")
            # Para comparações: usar slt, etc.
            elif op == '>':
                self.codigo.append(f"slt {res_reg}, {dir_reg}, {esq_reg}")  # Inverso para >
            # Adicionar mais ops
            return res_reg
        
        elif isinstance(no, ComandoSe):
            cond_reg = self.visitar(no.condicao)
            label_falso = self.nova_label()
            label_fim = self.nova_label()
            self.codigo.append(f"beq {cond_reg}, $zero, {label_falso}")
            for cmd in no.bloco_verdadeiro:
                self.visitar(cmd)
            self.codigo.append(f"j {label_fim}")
            self.codigo.append(f"{label_falso}:")
            if no.bloco_falso:
                for cmd in no.bloco_falso:
                    self.visitar(cmd)
            self.codigo.append(f"{label_fim}:")
        
        elif isinstance(no, ComandoEscreva):
            expr_reg = self.visitar(no.expressao)
            self.codigo.append("li $v0, 1")  # Print int
            self.codigo.append(f"move $a0, {expr_reg}")
            self.codigo.append("syscall")
            # Ajustar por tipo: 2 para float, 4 para string
        
        elif isinstance(no, ComandoLeia):
            self.codigo.append("li $v0, 5")  # Read int
            self.codigo.append("syscall")
            addr = self.var_map[no.variavel]
            self.codigo.append(f"sw $v0, {addr}")
            # Ajustar por tipo
        
        elif isinstance(no, DeclaracaoFuncao):
            label = no.nome
            self.func_map[no.nome] = label
            self.codigo.append("\n.text")  # Funções na .text
            self.codigo.append(f"{label}:")
            # Parâmetros: assumidos em $a0-$a3
            param_count = 0
            for p in no.parametros:
                self.alocar_variavel(p.nome, p.tipo)
                self.codigo.append(f"sw $a{param_count}, {self.var_map[p.nome]}")
                param_count += 1
            for cmd in no.corpo:
                self.visitar(cmd)
            self.codigo.append("jr $ra")
        
        elif isinstance(no, ChamadaFuncao):
            # Salvar $ra se necessário
            arg_count = 0
            for arg in no.argumentos:
                reg = self.visitar(arg)
                self.codigo.append(f"move $a{arg_count}, {reg}")
                arg_count += 1
            label = self.func_map[no.nome]
            self.codigo.append(f"jal {label}")
            reg = self.novo_temp()
            self.codigo.append(f"move {reg}, $v0")  # Assumir retorno em $v0
            return reg
        
        # Adicionar mais: Enquanto, Para, Unaria, etc.
        # Para Enquanto:
        # elif isinstance(no, ComandoEnquanto):
        #     label_inicio = self.nova_label()
        #     label_fim = self.nova_label()
        #     self.codigo.append(f"{label_inicio}:")
        #     cond_reg = self.visitar(no.condicao)
        #     self.codigo.append(f"beq {cond_reg}, $zero, {label_fim}")
        #     for cmd in no.bloco:
        #         self.visitar(cmd)
        #     self.codigo.append(f"j {label_inicio}")
        #     self.codigo.append(f"{label_fim}:")
        
        # Similar para Para, etc.

# Integração no AnalisadorSLR.py (adicione no __main__ após semantico.analisar(ast))
if not semantico.tem_erros():
    gerador = GeradorCodigoMIPS()
    codigo_mips = gerador.gerar(ast)
    print("\n=== CÓDIGO MIPS GERADO ===")
    print(codigo_mips)
    # Salvar em arquivo .asm
    with open("programa.asm", "w") as f:
        f.write(codigo_mips)
    print("Código salvo em programa.asm. Abra no MARS!")