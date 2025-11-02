from antlr4 import TerminalNode, ErrorNode
from compiladorParser import compiladorParser
from compiladorListener import compiladorListener
from TablaSimbolos import TablaSimbolos
from ID import ID

class Escucha(compiladorListener):
    #clase que escucha los eventos del parser y construye la tabla de simbolos mientras detecta errores

    indent = 1 #para sangria al imprimir
    declaracion = 0 #cantidad de declaraciones detectadas
    numNodos = 0 #cantidad total de nodos
    huboErrores = False #flag para saber si hubo errores

    def __init__(self):
        super().__init__()
        self.ts = TablaSimbolos()  #instancia de la tabla de simbolos singleton
        self.erroresRegistrados = set() #set para evitar errores duplicados

    # ----------------------------
    # utilidad
    # ----------------------------

    def registrarError(self, tipo, msj):
        #registra un error semantico o sintactico y activa el flag de errores
        if msj not in self.erroresRegistrados:
            self.erroresRegistrados.add(msj)
            self.huboErrores = True
            print(f"ERROR {tipo}: {msj}")

    def _usarID(self, nombre):
        #verifica si un id fue declarado y si esta inicializado
        simbolo = self.ts.buscarSimbolo(nombre)
        if simbolo is None:
            self.registrarError("semantico", f"'{nombre}' no declarado")
        elif not simbolo.getInicializado():
            self.registrarError("semantico", f"'{nombre}' usado sin inicializar")

    # ----------------------------
    # contextos
    # ----------------------------

    def enterBloque(self, ctx:compiladorParser.BloqueContext):
        #agrega un contexto nuevo al entrar a un bloque
        self.ts.addContexto()

    def exitBloque(self, ctx:compiladorParser.BloqueContext):
        #elimina el contexto al salir del bloque
        self.ts.delContexto()

    def enterIfor(self, ctx:compiladorParser.IforContext):
        #los for crean un contexto especial para variables declaradas en init
        self.ts.addContexto()

    def exitIfor(self, ctx:compiladorParser.IforContext):
        self.ts.delContexto()

    # ----------------------------
    # declaraciones
    # ----------------------------

    def enterDeclaracion(self, ctx:compiladorParser.DeclaracionContext):
        self.declaracion += 1

    def exitDeclaracion(self, ctx:compiladorParser.DeclaracionContext):
        #procesa la declaracion principal y las variables adicionales
        tipo_dato = ctx.tipo().getText()
        #primera variable
        nombre_principal = ctx.ID().getText()
        inic_principal = ctx.inic()
        id_principal = ID(nombre_principal, tipo_dato)

        if inic_principal.getChildCount() > 0:
            id_principal.setInicializado(True)
        else:
            id_principal.setInicializado(False)

        #verifica doble declaracion
        try:
            self.ts.contextos[-1].addSimbolo(id_principal)
        except ValueError:
            self.registrarError("semantico", f"'{nombre_principal}' ya declarado en contexto actual")

        #variables adicionales de la lista
        lista = ctx.listavar()
        if lista is not None:
            self._procesarListaVar(lista, tipo_dato)

    def _procesarListaVar(self, ctx_listavar, tipo_dato):
        #procesa recursivamente las variables en listas de declaraciones
        if ctx_listavar.getChildCount() == 0:
            return

        nombre_var = ctx_listavar.ID().getText()
        inic = ctx_listavar.inic()
        nuevo_id = ID(nombre_var, tipo_dato)
        if inic.getChildCount() > 0:
            nuevo_id.setInicializado(True)
        else:
            nuevo_id.setInicializado(False)

        try:
            self.ts.contextos[-1].addSimbolo(nuevo_id)
        except ValueError:
            self.registrarError("semantico", f"'{nombre_var}' ya declarado en contexto actual")

        siguiente = ctx_listavar.listavar()
        if siguiente is not None:
            self._procesarListaVar(siguiente, tipo_dato)

    # ----------------------------
    # asignaciones y uso de IDs
    # ----------------------------

    def exitExpASIG(self, ctx):
        #marca la variable de la asignacion como inicializada
        nombre = ctx.ID().getText()
        simbolo = self.ts.buscarSimbolo(nombre)
        if simbolo is None:
            self.registrarError("semantico", f"'{nombre}' no declarado")
        else:
            simbolo.setInicializado(True)

        #verifica IDs usados en la expresion
        self._recorrerExp(ctx.opal())

    def _recorrerExp(self, ctx):
        #recorre recursivamente los nodos de expresion para detectar IDs
        if ctx is None:
            return
        #verificar si es ID
        if hasattr(ctx, 'ID') and ctx.ID() is not None:
            self._usarID(ctx.ID().getText())
        #recorrer hijos
        for child in ctx.getChildren() if hasattr(ctx, 'getChildren') else []:
            self._recorrerExp(child)

    # ----------------------------
    # errores de parsing
    # ----------------------------

    def visitErrorNode(self, node: ErrorNode):
        self.registrarError("sintactico", f"error en token '{node.getText()}'")

    def enterEveryRule(self, ctx):
        self.numNodos += 1

    # ----------------------------
    # impresion final
    # ----------------------------

    def exitPrograma(self, ctx):
        #si hubo errores, no imprimimos la tabla de simbolos
        if self.huboErrores:
            print("no se puede generar tabla de simbolos debido a errores")
        else:
            #verificar IDs declarados pero no usados
            for contexto in self.ts.contextos:
                for simbolo in contexto.simbolos.values():
                    if not simbolo.getUsado():
                        self.registrarError("semantico", f"'{simbolo.getNombre()}' declarado pero no usado")
            #si tras esto no hay errores, imprimimos la TS
            if not self.huboErrores:
                self.ts.imprimirTS()
