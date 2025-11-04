import sys
from antlr4 import *
from Caminante import Caminante
from compiladorLexer import compiladorLexer
from compiladorParser import compiladorParser
from Escucha import Escucha
from EscuchaSintactico import EscuchaSintactico

def main(argv):
    #archivo = "Practicos/Practico2/input/entradaConErrores.txt"
    archivo = "Practicos/Practico2/input/entradaSinErrores.txt"
    if len(argv) > 1 :
        archivo = argv[1]
    input = FileStream(archivo)
    lexer = compiladorLexer(input)
    stream = CommonTokenStream(lexer)
    parser = compiladorParser(stream)
    
    #se elimina el ErrorListener default
    parser.removeErrorListeners()
    errorSintactico = EscuchaSintactico()
    parser.addErrorListener(errorSintactico)
    
    escucha = Escucha()

    parser.addParseListener(escucha)
    tree = parser.programa()
    
    #visitante = Caminante()
    #visitante.visitPrograma(tree)
    print(escucha)
    # print(tree.toStringTree(recog=parser))

if __name__ == '__main__':
    main(sys.argv)