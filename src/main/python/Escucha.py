from antlr4 import TerminalNode
from antlr4 import ErrorNode
from compiladorParser import compiladorParser
from compiladorListener import compiladorListener
from TablaSimbolos import TablaSimbolos
from ID import ID

class Escucha (compiladorListener):
    def _procesarListaVar(self, ctx_listavar, tipo_dato):
        contexto_actual = len(self.ts.contextos) - 1
        indent_str = "  " * self.indent

        if ctx_listavar.getChildCount() == 0:
            return

        nombre_var = ctx_listavar.ID().getText()
        inic = ctx_listavar.inic()

        nuevo_id = ID(nombre_var, tipo_dato)

        if inic.getChildCount() > 0:
            nuevo_id.setInicializado(True)
            print(f"{indent_str}Variable adicional: {nombre_var} (inicializada)")
        else:
            print(f"{indent_str}Variable adicional: {nombre_var} (sin inicializar)")

        try:
            self.ts.contextos[-1].addSimbolo(nuevo_id)
            print(f"{indent_str}'{nombre_var}' agregado al contexto {contexto_actual}")
        except ValueError:
            print(f"{indent_str}Error: variable '{nombre_var}' ya declarada en contexto {contexto_actual}")

        siguiente = ctx_listavar.listavar()
        if siguiente is not None:
            self._procesarListaVar(siguiente, tipo_dato)

    indent = 1
    declaracion = 0
    profundidad = 0
    numNodos = 0
    
    def __init__(self):
        super().__init__()
        self.ts = TablaSimbolos()  # instancia singleton
    
    
    #=========
    #Contextos
    #=========
    def enterBloque(self, ctx:compiladorParser.BloqueContext):
        print("  "*self.indent + "Nuevo bloque, se crea contexto")
        self.indent += 1
        self.ts.addContexto()

    def exitBloque(self, ctx:compiladorParser.BloqueContext):
        self.indent -= 1
        print("  "*self.indent + "Fin bloque, se elimina contexto")
        self.ts.delContexto()
    
    
    #=============
    #Declaraciones
    #=============
    def enterDeclaracion(self, ctx:compiladorParser.DeclaracionContext):
        self.declaracion += 1
    
    def exitDeclaracion(self, ctx:compiladorParser.DeclaracionContext):
        tipo_dato = ctx.tipo().getText()
        contexto_actual = len(self.ts.contextos) - 1
        indent_str = "  " * self.indent

        print(f"{indent_str}Declaracion detectada de tipo {tipo_dato} en contexto {contexto_actual}")
        
        # Variable principal (la primera que de declara en una lista de declaraciones) int A, b, c , d
        nombre_principal = ctx.ID().getText()
        inic_principal = ctx.inic()
        
        id_principal = ID(nombre_principal, tipo_dato)
        
        if inic_principal.getChildCount() > 0:
            id_principal.setInicializado(True)
            print(f"{indent_str}Variable principal: {nombre_principal} (inicializada)")
        else:
            print(f"{indent_str}Variable principal: {nombre_principal} (sin inicializar)")

        try:
            self.ts.contextos[-1].addSimbolo(id_principal)
            print(f"{indent_str}'{nombre_principal}' agregado al contexto {contexto_actual}")
        except ValueError:
            print(f"{indent_str}Error: variable '{nombre_principal}' ya declarada en contexto {contexto_actual}")

        # Variables adicionales (las otras despues de la primera que se declara) int a, B, C, D
        lista = ctx.listavar()
        if lista is not None:
            self._procesarListaVar(lista, tipo_dato)
    
    
    #===================
    # Estructuras de control
    #===================
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
        self.indent += 1

    def exitIif(self, ctx:compiladorParser.IifContext):
        self.indent -= 1
        print("  "*self.indent + "Fin if")

    
    #==============
    # ListaVar debug
    #==============
    def enterListavar(self, ctx:compiladorParser.ListavarContext):
        self.profundidad += 1

    def exitListavar(self, ctx:compiladorParser.ListavarContext):
        indent_str = "  " * self.indent
        print(f"{indent_str}-- ListaVar({self.profundidad}) Cant. hijos = {ctx.getChildCount()}")
        self.profundidad -= 1
        if ctx.getChildCount() == 4:
            print(f"{indent_str}  hoja ID --> |{ctx.getChild(1).getText()}|")

    def visitErrorNode(self, node: ErrorNode):
        print(" ---> ERROR")
        
    def enterEveryRule(self, ctx):
        self.numNodos += 1
    
    def __str__(self):
        return f"Se hicieron {self.declaracion} declaraciones\nSe visitaron {self.numNodos} nodos"
