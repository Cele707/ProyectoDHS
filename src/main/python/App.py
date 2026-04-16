import sys
from antlr4 import *
from Caminante import Caminante
from compiladorLexer import compiladorLexer
from compiladorParser import compiladorParser
from Escucha import Escucha
from EscuchaSintactico import EscuchaSintactico
from TablaSimbolos import TablaSimbolos
from Optimizador import Optimizador

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
    errorSintactico = EscuchaSintactico()
    parser.removeErrorListeners()
    parser.addErrorListener(errorSintactico)
    
    #manejo de errores semanticos
    escucha = Escucha(errorSintactico)
    parser.addParseListener(escucha)
    tree = parser.programa()
    
    #solo generamos archivos si no hubo errores 
    if not escucha.huboErrores and not errorSintactico.errores:
        print("Compilación exitosa. Generando archivos de salida...")
        
        #la generacion del codigo intermedio tambien se hace solo en el caso de que no haya errores
        visitante = Caminante()
        visitante.visitPrograma(tree)
        
        with open("output/CodigoIntermedio.txt", "w") as f:
            for linea in visitante.codigo:
                f.write(linea + "\n")
        print("Archivo generado: CodigoIntermedio.txt")

        ts = TablaSimbolos() 
        ts.generarArchivo("output/TablaDeSimbolos.txt")
        print("Archivo generado: TablaDeSimbolos.txt")
        
        opt = Optimizador("output/CodigoIntermedio.txt", "output/CodigoOptimizado.txt")
        opt.ejecutar()
        
    else:
        print("\n HUBO ERRORES EN LA COMPILACION, NO SE GENERARON LOS ARCHIVOS")
        #para eliminar contenido de ejecuciones anteriores
        with open("output/CodigoIntermedio.txt", "w") as f:
            pass
        with open("output/TablaDeSimbolos.txt", "w") as f:
            pass
        with open("output/CodigoOptimizado.txt", "w") as f:
            pass
    
    #print(escucha)
    #print(tree.toStringTree(recog=parser))

if __name__ == '__main__':
    main(sys.argv)