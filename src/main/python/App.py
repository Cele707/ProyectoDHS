import sys
from antlr4 import *
from Caminante import Caminante
from compiladorLexer import compiladorLexer
from compiladorParser import compiladorParser
from Escucha import Escucha
from EscuchaSintactico import EscuchaSintactico

def main(argv):
    #archivo = "input/entradaConErrores.txt"
    archivo = "input/entradaSinErrores.txt"
    if len(argv) > 1 :
        archivo = argv[1]
    input = FileStream(archivo)
    lexer = compiladorLexer(input)
    stream = CommonTokenStream(lexer)
    parser = compiladorParser(stream)
    
    #se elimina el ErrorListener default
    #manejo de errores sintacticos
    parser.removeErrorListeners()
    errorSintactico = EscuchaSintactico()
    parser.addErrorListener(errorSintactico)
    
    #manejo de errores semanticos
    escucha = Escucha()
    parser.addParseListener(escucha)
    tree = parser.programa()
    
    #solo se activa la generacion de codigo intermedio si no hay errores
    if not escucha.huboErrores:
        visitante = Caminante()
        visitante.visitPrograma(tree)
        
        
        
    #print(escucha)
    #print(tree.toStringTree(recog=parser))

if __name__ == '__main__':
    main(sys.argv)