from enum import Enum
from dataclasses import dataclass
from typing import List, Optional


class TipoToken(Enum):
    """Tipos de tokens reconhecidos pelo analisador"""
    # Identificadores e literais
    IDENTIFICADOR = "IDENTIFICADOR"
    INTEIRO = "INTEIRO"
    FLUTUANTE = "FLUTUANTE"
    CADEIA = "CADEIA"
    BOOLEANO = "BOOLEANO"
    
    # Palavras reservadas
    SE = "SE"
    SENAO = "SENAO"
    PARA = "PARA"
    FACA = "FACA"
    ENQUANTO = "ENQUANTO"
    ESCREVA = "ESCREVA"
    LEIA = "LEIA"
    TIPO_INTEIRO = "TIPO_INTEIRO"
    TIPO_FLUTUANTE = "TIPO_FLUTUANTE"
    TIPO_LOGICO = "TIPO_LOGICO"
    TIPO_CADEIA = "TIPO_CADEIA"
    INICIO_BLOCO = "INICIO_BLOCO"
    FIM_BLOCO = "FIM_BLOCO"
    LOGICO_E = "LOGICO_E"  # Novo: 'e' para AND lógico
    LOGICO_OU = "LOGICO_OU"  # Novo: 'ou' para OR lógico
    
    # Operadores
    ADICAO = "ADICAO"
    SUBTRACAO = "SUBTRACAO"
    MULTIPLICACAO = "MULTIPLICACAO"
    DIVISAO = "DIVISAO"
    PARENTESE_ESQ = "PARENTESE_ESQ"
    PARENTESE_DIR = "PARENTESE_DIR"
    COLCHETE_ESQ = "COLCHETE_ESQ"
    COLCHETE_DIR = "COLCHETE_DIR"
    MAIOR = "MAIOR"
    MENOR = "MENOR"
    MAIOR_IGUAL = "MAIOR_IGUAL"
    MENOR_IGUAL = "MENOR_IGUAL"
    ATRIBUICAO = "ATRIBUICAO"
    CONCATENACAO = "CONCATENACAO"
    INCREMENTO = "INCREMENTO"
    DECREMENTO = "DECREMENTO"
    PONTO_VIRGULA = "PONTO_VIRGULA"
    VIRGULA = "VIRGULA"
    IGUALDADE = "IGUALDADE"  # Novo: ==
    DIFERENTE = "DIFERENTE"  # Novo: !=
    NEGACAO = "NEGACAO"  # Novo: !
    
    # Especiais
    FIM_ARQUIVO = "FIM_ARQUIVO"


@dataclass
class Token:
    """Representa um token identificado"""
    tipo: TipoToken
    lexema: str
    linha: int
    coluna: int
    
    def __str__(self):
        return f"Token({self.tipo.value}, '{self.lexema}', linha={self.linha}, col={self.coluna})"


@dataclass
class Erro:
    """Representa um erro léxico"""
    mensagem: str
    linha: int
    coluna: int
    
    def __str__(self):
        return f"Erro léxico [linha {self.linha}, coluna {self.coluna}]: {self.mensagem}"


class AnalisadorLexico:
    """Analisador léxico para a linguagem especificada"""
    
    # Palavras reservadas da linguagem
    PALAVRAS_RESERVADAS = {
        'se': TipoToken.SE,
        'senao': TipoToken.SENAO,
        'para': TipoToken.PARA,
        'faca': TipoToken.FACA,
        'enquanto': TipoToken.ENQUANTO,
        'escreva': TipoToken.ESCREVA,
        'leia': TipoToken.LEIA,
        'inteiro': TipoToken.TIPO_INTEIRO,
        'flutuante': TipoToken.TIPO_FLUTUANTE,
        'logico': TipoToken.TIPO_LOGICO,
        'cadeia': TipoToken.TIPO_CADEIA,
        'inicio': TipoToken.INICIO_BLOCO,
        'fim': TipoToken.FIM_BLOCO,
        'verdadeiro': TipoToken.BOOLEANO,
        'falso': TipoToken.BOOLEANO,
        'e': TipoToken.LOGICO_E,  # Novo
        'ou': TipoToken.LOGICO_OU,  # Novo
    }
    
    def __init__(self, codigo_fonte: str):
        """
        Inicializa o analisador léxico
        
        Args:
            codigo_fonte: String contendo o código fonte a ser analisado
        """
        self.codigo = codigo_fonte
        self.posicao = 0
        self.linha = 1
        self.coluna = 1
        self.tokens: List[Token] = []
        self.erros: List[Erro] = []
    
    def caractere_atual(self) -> Optional[str]:
        """Retorna o caractere na posição atual ou None se fim do arquivo"""
        if self.posicao >= len(self.codigo):
            return None
        return self.codigo[self.posicao]
    
    def proximo_caractere(self) -> Optional[str]:
        """Retorna o próximo caractere sem avançar a posição"""
        if self.posicao + 1 >= len(self.codigo):
            return None
        return self.codigo[self.posicao + 1]
    
    def avancar(self):
        """Avança para o próximo caractere"""
        if self.posicao < len(self.codigo):
            if self.codigo[self.posicao] == '\n':
                self.linha += 1
                self.coluna = 1
            else:
                self.coluna += 1
            self.posicao += 1
    
    def pular_espacos(self):
        """Pula espaços em branco e tabulações"""
        while self.caractere_atual() and self.caractere_atual() in ' \t\n\r':
            self.avancar()
    
    def pular_comentario(self):
        """Pula comentários (// até fim da linha ou /* */ multilinha)"""
        char = self.caractere_atual()
        prox = self.proximo_caractere()
        
        # Comentário de linha única: //
        if char == '/' and prox == '/':
            self.avancar()  # pula primeiro /
            self.avancar()  # pula segundo /
            while self.caractere_atual() and self.caractere_atual() != '\n':
                self.avancar()
            return True
        
        # Comentário multilinha: /* */
        if char == '/' and prox == '*':
            linha_inicio = self.linha
            col_inicio = self.coluna
            self.avancar()  # pula /
            self.avancar()  # pula *
            
            while self.caractere_atual():
                if self.caractere_atual() == '*' and self.proximo_caractere() == '/':
                    self.avancar()  # pula *
                    self.avancar()  # pula /
                    return True
                self.avancar()
            
            # Comentário não fechado
            self.erros.append(Erro(
                "Comentário multilinha não fechado",
                linha_inicio,
                col_inicio
            ))
            return True
        
        return False
    
    def ler_numero(self) -> Token:
        """Lê um número inteiro ou flutuante"""
        linha_inicio = self.linha
        col_inicio = self.coluna
        lexema = ""
        eh_flutuante = False
        
        # Lê dígitos
        while self.caractere_atual() and self.caractere_atual().isdigit():
            lexema += self.caractere_atual()
            self.avancar()
        
        # Verifica se é um número flutuante
        if self.caractere_atual() == '.' and self.proximo_caractere() and self.proximo_caractere().isdigit():
            eh_flutuante = True
            lexema += self.caractere_atual()
            self.avancar()
            
            while self.caractere_atual() and self.caractere_atual().isdigit():
                lexema += self.caractere_atual()
                self.avancar()
        
        tipo = TipoToken.FLUTUANTE if eh_flutuante else TipoToken.INTEIRO
        return Token(tipo, lexema, linha_inicio, col_inicio)
    
    def ler_cadeia(self) -> Optional[Token]:
        """Lê uma cadeia de caracteres delimitada por aspas duplas"""
        linha_inicio = self.linha
        col_inicio = self.coluna
        lexema = ""
        
        # Pula a aspa inicial
        self.avancar()
        
        while self.caractere_atual() and self.caractere_atual() != '"':
            if self.caractere_atual() == '\\' and self.proximo_caractere():
                # Suporta caracteres de escape
                self.avancar()
                char_escape = self.caractere_atual()
                if char_escape == 'n':
                    lexema += '\n'
                elif char_escape == 't':
                    lexema += '\t'
                elif char_escape == '\\':
                    lexema += '\\'
                elif char_escape == '"':
                    lexema += '"'
                else:
                    lexema += char_escape
                self.avancar()
            elif self.caractere_atual() == '\n':
                self.erros.append(Erro(
                    "Cadeia de caracteres não fechada antes do fim da linha",
                    linha_inicio,
                    col_inicio
                ))
                return None
            else:
                lexema += self.caractere_atual()
                self.avancar()
        
        if not self.caractere_atual():
            self.erros.append(Erro(
                "Cadeia de caracteres não fechada antes do fim do arquivo",
                linha_inicio,
                col_inicio
            ))
            return None
        
        # Pula a aspa final
        self.avancar()
        
        return Token(TipoToken.CADEIA, lexema, linha_inicio, col_inicio)
    
    def ler_identificador(self) -> Token:
        """Lê um identificador ou palavra reservada"""
        linha_inicio = self.linha
        col_inicio = self.coluna
        lexema = ""
        
        # Identificadores começam com letra ou underscore
        while self.caractere_atual() and (self.caractere_atual().isalnum() or self.caractere_atual() == '_'):
            lexema += self.caractere_atual()
            self.avancar()
        
        # Verifica se é palavra reservada
        lexema_lower = lexema.lower()
        if lexema_lower in self.PALAVRAS_RESERVADAS:
            tipo = self.PALAVRAS_RESERVADAS[lexema_lower]
        else:
            tipo = TipoToken.IDENTIFICADOR
        
        return Token(tipo, lexema, linha_inicio, col_inicio)
    
    def ler_operador(self) -> Optional[Token]:
        """Lê operadores e delimitadores"""
        linha_inicio = self.linha
        col_inicio = self.coluna
        char = self.caractere_atual()
        prox = self.proximo_caractere()
        
        # Novos operadores
        if char == '=' and prox == '=':
            self.avancar()
            self.avancar()
            return Token(TipoToken.IGUALDADE, '==', linha_inicio, col_inicio)
        
        if char == '!' and prox == '=':
            self.avancar()
            self.avancar()
            return Token(TipoToken.DIFERENTE, '!=', linha_inicio, col_inicio)
        
        if char == '!':
            self.avancar()
            return Token(TipoToken.NEGACAO, '!', linha_inicio, col_inicio)
        
        # Operadores de dois caracteres existentes
        if char == '+' and prox == '+':
            self.avancar()
            self.avancar()
            return Token(TipoToken.INCREMENTO, '++', linha_inicio, col_inicio)
        
        if char == '-' and prox == '-':
            self.avancar()
            self.avancar()
            return Token(TipoToken.DECREMENTO, '--', linha_inicio, col_inicio)
        
        if char == '>' and prox == '=':
            self.avancar()
            self.avancar()
            return Token(TipoToken.MAIOR_IGUAL, '>=', linha_inicio, col_inicio)
        
        if char == '<' and prox == '=':
            self.avancar()
            self.avancar()
            return Token(TipoToken.MENOR_IGUAL, '<=', linha_inicio, col_inicio)
        
        if char == '&' and prox == '&':
            self.avancar()
            self.avancar()
            return Token(TipoToken.CONCATENACAO, '&&', linha_inicio, col_inicio)
        
        # Operadores de um caractere
        operadores_simples = {
            '+': TipoToken.ADICAO,
            '-': TipoToken.SUBTRACAO,
            '*': TipoToken.MULTIPLICACAO,
            '/': TipoToken.DIVISAO,
            '(': TipoToken.PARENTESE_ESQ,
            ')': TipoToken.PARENTESE_DIR,
            '[': TipoToken.COLCHETE_ESQ,
            ']': TipoToken.COLCHETE_DIR,
            '>': TipoToken.MAIOR,
            '<': TipoToken.MENOR,
            '=': TipoToken.ATRIBUICAO,
            ';': TipoToken.PONTO_VIRGULA,
            ',': TipoToken.VIRGULA,
        }
        
        if char in operadores_simples:
            self.avancar()
            return Token(operadores_simples[char], char, linha_inicio, col_inicio)
        
        return None
    
    def proximo_token(self) -> Optional[Token]:
        """Obtém o próximo token do código fonte"""
        while True:
            # Pula espaços em branco
            self.pular_espacos()
            
            # Verifica fim do arquivo
            if not self.caractere_atual():
                return None
            
            # Pula comentários
            if self.pular_comentario():
                continue
            
            break
        
        char = self.caractere_atual()
        linha_inicio = self.linha
        col_inicio = self.coluna
        
        # Números
        if char.isdigit():
            return self.ler_numero()
        
        # Cadeias de caracteres
        if char == '"':
            token = self.ler_cadeia()
            if token:
                return token
            # Se houver erro, continua para próximo token
            return self.proximo_token()
        
        # Identificadores e palavras reservadas
        if char.isalpha() or char == '_':
            return self.ler_identificador()
        
        # Operadores e delimitadores
        token = self.ler_operador()
        if token:
            return token
        
        # Caractere desconhecido
        self.erros.append(Erro(
            f"Caractere inválido: '{char}'",
            linha_inicio,
            col_inicio
        ))
        self.avancar()
        return self.proximo_token()
    
    def analisar(self) -> List[Token]:
        """
        Realiza a análise léxica completa do código fonte
        
        Returns:
            Lista de tokens identificados
        """
        self.tokens = []
        self.erros = []
        
        while True:
            token = self.proximo_token()
            if token is None:
                break
            self.tokens.append(token)
        
        # Adiciona token de fim de arquivo
        self.tokens.append(Token(
            TipoToken.FIM_ARQUIVO,
            "",
            self.linha,
            self.coluna
        ))
        
        return self.tokens
    
    def obter_erros(self) -> List[Erro]:
        """Retorna a lista de erros encontrados"""
        return self.erros
    
    def tem_erros(self) -> bool:
        """Verifica se há erros"""
        return len(self.erros) > 0
    
    def imprimir_tokens(self):
        """Imprime todos os tokens encontrados"""
        print("\n=== TOKENS ENCONTRADOS ===")
        for token in self.tokens:
            print(token)
    
    def imprimir_erros(self):
        """Imprime todos os erros encontrados"""
        if self.tem_erros():
            print("\n=== ERROS ENCONTRADOS ===")
            for erro in self.erros:
                print(erro)
        else:
            print("\n=== NENHUM ERRO ENCONTRADO ===")


# ============================================
# EXEMPLO DE USO
# ============================================

if __name__ == "__main__":
    # Exemplo de código fonte para análise
    codigo_exemplo = """
    // Este é um comentário de linha
    inicio
        inteiro x = 10
        flutuante y = 3.14
        cadeia mensagem = "Olá, mundo!"
        logico ativo = verdadeiro
        
        /* Este é um
           comentário multilinha */
        
        se (x > 5) faca
            escreva("X é maior que 5")
        senao
            escreva("X é menor ou igual a 5")
        fim
        
        para (inteiro i = 0; i < 10; i++) faca
            escreva(i)
        fim
        
        enquanto (x >= 0) faca
            x--
        fim
        
        // Operações matemáticas
        inteiro resultado = (x + y) * 2 / 3 - 1
        cadeia nome = "João" && " Silva"
        
        // Arrays
        inteiro[10] numeros
        
        leia(x)
    fim
    """
    
    # Cria o analisador
    analisador = AnalisadorLexico(codigo_exemplo)
    
    # Realiza a análise
    tokens = analisador.analisar()
    
    # Exibe resultados
    analisador.imprimir_tokens()
    analisador.imprimir_erros()
    
    # Estatísticas
    print(f"\n=== ESTATÍSTICAS ===")
    print(f"Total de tokens: {len(tokens)}")
    print(f"Total de erros: {len(analisador.obter_erros())}")
    
    # Exemplo com erros
    print("\n\n" + "="*50)
    print("TESTANDO CÓDIGO COM ERROS")
    print("="*50)
    
    codigo_com_erros = """
    inteiro x = 10
    cadeia texto = "teste não fechado
    inteiro y = @#$  // caracteres inválidos
    /* comentário não fechado
    """
    
    analisador2 = AnalisadorLexico(codigo_com_erros)
    tokens2 = analisador2.analisar()
    analisador2.imprimir_tokens()
    analisador2.imprimir_erros()