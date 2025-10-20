from antlr4 import TerminalNode
from antlr4 import ErrorNode
from compiladorParser import compiladorParser
from compiladorListener import compiladorListener
from TablaSimbolos import TablaSimbolos
from ID import ID

class Escucha (compiladorListener) :
    indent = 1
    declaracion = 0
    profundidad = 0
    numNodos = 0
    
    def __init__(self):
        super().__init__()
        self.ts = TablaSimbolos() #instacia singleton
        #el constructor de TablaSimbolos crea el contexto 0
    
    
    #=========
    #Contextos
    #=========
    def enterBloque(self, ctx:compiladorParser.BloqueContext):
        print("  "*self.indent + "Nuevo bloque, se crea contexto")
        self.indent += 1
        self.ts.addContexto() #agrega un nuevo contexto
    def exitBloque(self, ctx:compiladorParser.BloqueContext):
        self.indent -= 1
        print("  "*self.indent + "Fin bloque, se elimina contexto")
        self.ts.delContexto() #elimina el contexto actual
    
    
    #=============
    #Declaraciones INCOMPLETO
    #=============
    def enterDeclaracion(self, ctx:compiladorParser.DeclaracionContext):
        self.declaracion += 1
        print("Declaracion ENTER -> |" + ctx.getText() + "|")
        print("  -- Cant. hijos = " + str(ctx.getChildCount()))
    
    def exitDeclaracion(self, ctx:compiladorParser.DeclaracionContext):
        print("Declaracion EXIT  -> |" + ctx.getText() + "|")
        print("  -- Cant. hijos = " + str(ctx.getChildCount()))
    
    
    


    #mensajes cuando entra a distintas cosas para mayor claridad
    def enterPrograma(self, ctx:compiladorParser.ProgramaContext):
        print("Comienza el parsing")

    def exitPrograma(self, ctx:compiladorParser.ProgramaContext):
        print("Fin del parsing")

    def enterIwhile(self, ctx:compiladorParser.IwhileContext):
        print("  "*self.indent + "Comienza while")
        self.indent += 1

    def exitIwhile(self, ctx:compiladorParser.IwhileContext):
        self.indent -= 1
        print("  "*self.indent + "Fin while")
        
    def enterIif(self, ctx:compiladorParser.IifContext):
        print("  "*self.indent + "Comienza if")
        self.indentr += 1

    def exitIif(self, ctx:compiladorParser.IifContext):
        self.indent -= 1
        print("  "*self.indent + "Fin if")
        


    
    def enterListavar(self, ctx:compiladorParser.ListavarContext):
        self.profundidad += 1

    def exitListavar(self, ctx:compiladorParser.ListavarContext):
        print("  -- ListaVar(%d) Cant. hijos  = %d" % (self.profundidad, ctx.getChildCount()))
        self.profundidad -= 1
        if ctx.getChildCount() == 4 :
            print("      hoja ID --> |%s|" % ctx.getChild(1).getText())

    # def visitTerminal(self, node: TerminalNode):
    #     print(" ---> Token: " + node.getText())
        # self.numTokens += 1
    
    def visitErrorNode(self, node: ErrorNode):
        print(" ---> ERROR")
        
    def enterEveryRule(self, ctx):
        self.numNodos += 1
    
    def __str__(self):
        return "Se hicieron " + str(self.declaracion) + " declaraciones\n" + \
                "Se visitaron " + str(self.numNodos) + " nodos"