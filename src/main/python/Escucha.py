from antlr4 import TerminalNode, ErrorNode
from compiladorParser import compiladorParser
from compiladorListener import compiladorListener
from TablaSimbolos import TablaSimbolos
from ID import ID

class Escucha(compiladorListener):
    # Clase que escucha los eventos del parser y construye la tabla de simbolos mientras detecta errores

    indent = 1
    declaracion = 0
    numNodos = 0
    huboErrores = False

    def __init__(self):
        super().__init__()
        self.ts = TablaSimbolos()  # instancia de la tabla de simbolos singleton
        self.erroresRegistrados = set()  # set para evitar errores duplicados

    # ----------------------------
    # Utilidad
    # ----------------------------
    def registrarError(self, tipo, msj):
        if msj not in self.erroresRegistrados:
            self.erroresRegistrados.add(msj)
            self.huboErrores = True
            print(f"ERROR {tipo}: {msj}")

    def _usarID(self, nombre):
        simbolo = None
        for contexto in reversed(self.ts.contextos):
            if nombre in contexto.simbolos:
                simbolo = contexto.simbolos[nombre]
                break

        if simbolo is None:
            self.registrarError("semantico", f"'{nombre}' no declarado")
        else:
            simbolo.setUsado(True)
            if not simbolo.getInicializado():
                self.registrarError("semantico", f"'{nombre}' usado sin inicializar")

    # ----------------------------
    # Contextos
    # ----------------------------
    def enterBloque(self, ctx: compiladorParser.BloqueContext):
        self.ts.addContexto()

    def exitBloque(self, ctx: compiladorParser.BloqueContext):
        self.ts.delContexto()

    # ----------------------------
    # Declaraciones
    # ----------------------------
    def enterDeclaracion(self, ctx: compiladorParser.DeclaracionContext):
        self.declaracion += 1

    def exitDeclaracion(self, ctx: compiladorParser.DeclaracionContext):
        tipo_dato = ctx.tipo().getText()
        nombre_principal = ctx.ID().getText()
        inic_principal = ctx.inic()
        id_principal = ID(nombre_principal, tipo_dato)

        if inic_principal.getChildCount() > 0:
            id_principal.setInicializado(True)
            self._recorrerExp(inic_principal.opal())
        else:
            id_principal.setInicializado(False)

        try:
            self.ts.contextos[-1].addSimbolo(id_principal)
        except ValueError:
            self.registrarError("semantico", f"'{nombre_principal}' ya declarado en contexto actual")

        lista = ctx.listavar()
        if lista is not None:
            self._procesarListaVar(lista, tipo_dato)

    def _procesarListaVar(self, ctx_listavar, tipo_dato):
        if ctx_listavar.getChildCount() == 0:
            return

        nombre_var = ctx_listavar.ID().getText()
        inic = ctx_listavar.inic()
        nuevo_id = ID(nombre_var, tipo_dato)
        nuevo_id.setInicializado(inic.getChildCount() > 0)

        try:
            self.ts.contextos[-1].addSimbolo(nuevo_id)
        except ValueError:
            self.registrarError("semantico", f"'{nombre_var}' ya declarado en contexto actual")

        siguiente = ctx_listavar.listavar()
        if siguiente is not None:
            self._procesarListaVar(siguiente, tipo_dato)

    # ----------------------------
    # Asignaciones y uso de IDs
    # ----------------------------
    def exitExpASIG(self, ctx):
        nombre = ctx.ID().getText()
        simbolo = self.ts.buscarSimbolo(nombre)
        if simbolo is None:
            self.registrarError("semantico", f"'{nombre}' no declarado")
        else:
            simbolo.setInicializado(True)
            simbolo.setUsado(True)

        self._recorrerExp(ctx.opal())

    def _recorrerExp(self, ctx):
        if ctx is None:
            return

        #si es un nodo terminal (leaf) y es un ID
        if isinstance(ctx, TerminalNode) and ctx.getSymbol().type == compiladorParser.ID:
            nombre = ctx.getText()
            self._usarID(nombre)
            return

        #si no es terminal, recorrer hijos
        for i in range(ctx.getChildCount()):
            child = ctx.getChild(i)
            self._recorrerExp(child)

    # ----------------------------
    # Estructuras de control
    # ----------------------------
    def enterIwhile(self, ctx: compiladorParser.IwhileContext):
        self.ts.addContexto()
        #analizar la condición
        if hasattr(ctx, "opal") and ctx.opal() is not None:
            self._recorrerExp(ctx.opal())

    def exitIwhile(self, ctx: compiladorParser.IwhileContext):
        self.ts.delContexto()

    def enterIif(self, ctx: compiladorParser.IifContext):
        self.ts.addContexto() 
        if hasattr(ctx, "opal") and ctx.opal() is not None:
            self._recorrerExp(ctx.opal())

    def exitIif(self, ctx: compiladorParser.IifContext):
        self.ts.delContexto()

    def enterIelse(self, ctx: compiladorParser.IelseContext):
        self.ts.addContexto()

    def exitIelse(self, ctx: compiladorParser.IelseContext):
        self.ts.delContexto()

    def enterIfor(self, ctx: compiladorParser.IforContext):
        self.ts.addContexto()

        if hasattr(ctx, "forInicializacion") and ctx.forInicializacion() is not None:
            self._recorrerExp(ctx.forInicializacion())
        if hasattr(ctx, "forCond") and ctx.forCond() is not None:
            self._recorrerExp(ctx.forCond())
        if hasattr(ctx, "forActualizacion") and ctx.forActualizacion() is not None:
            self._recorrerExp(ctx.forActualizacion())


    def exitIfor(self, ctx: compiladorParser.IforContext):
        self.ts.delContexto()

    # ----------------------------
    # Errores de parsing
    # ----------------------------
    def visitErrorNode(self, node: ErrorNode):
        self.registrarError("sintactico", f"error en token '{node.getText()}'")

    def enterEveryRule(self, ctx):
        self.numNodos += 1

    # ----------------------------
    # Impresion final
    # ----------------------------
    def exitPrograma(self, ctx):
        simbolos_vistos = set()

        #recorrer contextos de dentro hacia afuera (como en _usarID)
        for contexto in reversed(self.ts.contextos):
            for nombre, simbolo in contexto.simbolos.items():
                if nombre not in simbolos_vistos:
                    simbolos_vistos.add(nombre)
                    if not simbolo.getUsado():
                        self.registrarError("semantico", f"'{nombre}' declarado pero no usado")

        if self.huboErrores:
            print("no se puede generar tabla de simbolos debido a errores")
        else:
            self.ts.imprimirTS()
