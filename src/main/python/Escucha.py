from compiladorParser import compiladorParser
from compiladorListener import compiladorListener
from TablaSimbolos import TablaSimbolos
from ID import Variable, Funcion


class Escucha(compiladorListener):
    def __init__(self):
        self.ts = TablaSimbolos()  #singleton
        self.huboErrores = False #flag para saber si hubo errores
        self.indent = 0  #nivel de sangría para los prints

    # -----------------------------
    # contextos
    # -----------------------------
    def enterPrograma(self, ctx: compiladorParser.ProgramaContext):
        print("Comienza el parsing\n")

    def exitPrograma(self, ctx: compiladorParser.ProgramaContext):
        #verifica variables declaradas pero no utilizadas en todos los contextos
        hay_advertencias = False
        for contexto in self.ts.contextos:
            for nombre, var in contexto.simbolos.items():
                #isinstance verifica que sea un objeto de la clase Variable
                if isinstance(var, Variable) and not var.getUsado():
                    if not hay_advertencias:
                        print("\n--- ADVERTENCIA ---")
                        hay_advertencias = True
                    print(" " * self.indent + f"[ADVERTENCIA]: Variable '{nombre}' declarada pero no usada")
        #si hubo errores no se imprime la tabla
        if self.huboErrores:
            print("[INFO]: No se puede generar tabla de símbolos debido a errores")
        else:
            print("[INFO]: Tabla de símbolos final:")
            self.ts.imprimirTS()
        print("[INFO]: Fin del parsing")

    # -----------------------------
    # declaraciones
    # -----------------------------
    def exitDeclaracion(self, ctx: compiladorParser.DeclaracionContext):
        #obtiene tipo de dato y el primer Id
        tipo = ctx.tipo().getText()
        ids = [ctx.ID().getText()]

        def recolectar_listavar(lv, acumulador):
            #funcion recursiva para recolectar todos los IDs en una lista de variables
            #lv: contexto listavar de la gramatica
            #acumulador: lista de nombres de variables
            if lv is not None and lv.ID() is not None:
                acumulador.append(lv.ID().getText())
                recolectar_listavar(lv.listavar(), acumulador)

        recolectar_listavar(ctx.listavar(), ids)
        #procesa cada variable
        for nombre in ids:
            #busca si el ID ya esta declarado en el contexto actual
            if self.ts.buscarSimboloContexto(nombre):
                #si ya esta declarada en el contexto actual es un error
                self.registrarError("semantico", f"'{nombre}' ya declarado en contexto actual")
            else:
                var = Variable(nombre, tipo)
                #la marca como inicializada si tiene un valor
                if ctx.inic() and ctx.inic().getChildCount() > 0:
                    var.setInicializado(True)
                #se agrega la variable a la tabla de simbolos
                self.ts.addSimbolo(var)
                print(" " * self.indent + f"[INFO]: Se agregó la variable '{nombre}' de tipo '{tipo}'")

    # -----------------------------
    # Asignaciones
    # -----------------------------
    def exitAsignacion(self, ctx: compiladorParser.AsignacionContext):
        exp_asig_ctx = ctx.expASIG()
        if exp_asig_ctx is None:
            return

        #obtiene el nombre de la variable destino y la expresion a asignar
        nombre = exp_asig_ctx.ID().getText()
        valor_ctx = exp_asig_ctx.opal()

        #busca la variable en los contextos de la tabla de simbolos
        simbolo = self.ts.buscarSimbolo(nombre)
        if simbolo is None:
            #error si la variable no fue declarada
            self.registrarError("semantico", f"'{nombre}' usado sin declarar")
            return

        #obtiene tipo de la variable destino y tipo de la expresion
        tipo_destino = simbolo.getTipoDato()
        tipo_valor = self._tipoExp(valor_ctx)

        #compara el tipo de la variable destino con el tipo de la expresion
        if tipo_valor and tipo_destino != tipo_valor:
            self.registrarError("semantico",
                            f"Asignación incompatible: '{nombre}' es {tipo_destino} y se intenta asignar {tipo_valor}")

        #marca variable como inicializada y usada
        simbolo.setInicializado(True)
        simbolo.setUsado(True)
        print(" " * self.indent + f"[INFO]: Asignación realizada: '{nombre}' inicializado y usado")

    # -----------------------------
    # uso de variables en expresiones
    # -----------------------------
    def exitFactor(self, ctx: compiladorParser.FactorContext):
        if ctx.ID():
            nombre = ctx.ID().getText()
            simbolo = self.ts.buscarSimbolo(nombre)
            if simbolo is None:
                #para variables usadas pero sin declarar
                self.registrarError("semantico", f"'{nombre}' usado sin declarar")
            else:
                #si la var estaba declarada, la marca como usada
                simbolo.setUsado(True)
                if not simbolo.getInicializado():
                    #para variables usadas pero sin inicializar
                    self.registrarError("semantico", f"'{nombre}' usado sin inicializar")
                print(" " * self.indent + f"[INFO]: Uso de variable '{nombre}' detectado")

    # -----------------------------
    # evaluacion de tipos de expresiones
    # -----------------------------
    def _tipoExp(self, ctx):
        if ctx is None:
            return None

        #hasattr verifica si el objeto ctx tiene un atributo llamado ID
        #sirve para distinguir entre nodos terminales ID y otros tipos
        if hasattr(ctx, 'ID') and ctx.ID():
            nombre = ctx.ID().getText()
            var = self.ts.buscarSimbolo(nombre)
            if var:
                var.setUsado(True)
                if not var.getInicializado():
                    self.registrarError("semantico", f"'{nombre}' usado sin inicializar")
                return var.getTipoDato()
            else:
                self.registrarError("semantico", f"'{nombre}' usado sin declarar")
                return None

        #si es un numero literal
        if hasattr(ctx, 'NUM') and ctx.NUM():
            return "int"

        #verifica tipos de los hijos de la expresion
        tipos = set()
        for i in range(ctx.getChildCount()):
            tipo_hijo = self._tipoExp(ctx.getChild(i))
            if tipo_hijo:
                tipos.add(tipo_hijo)

        #si todos los hijos son del mismo tipo devuelve ese tipo
        if len(tipos) == 1:
            return tipos.pop()
        elif len(tipos) > 1:
            #si hay tipos distintos
            self.registrarError("semantico", "Tipos incompatibles en expresión")
            return None
        else:
            return None

    # -----------------------------
    # contexto de bloques (if, else, for, while)
    # -----------------------------
    def enterBloque(self, ctx):
        self.ts.addContexto()
        self.indent += 2
        print(" " * (self.indent - 2) + "[INFO]: Entrando a bloque")

    def exitBloque(self, ctx):
        self._verificarVariablesNoUsadas()
        print(" " * (self.indent - 2) + "[INFO]: Saliendo de bloque")
        self.ts.delContexto()
        self.indent -= 2

    def enterIif(self, ctx):
        self.ts.addContexto()
        self.indent += 2
        print(" " * (self.indent - 2) + "[INFO]: Entrando a if")

    def exitIif(self, ctx):
        self._verificarVariablesNoUsadas()
        print(" " * (self.indent - 2) + "[INFO]: Saliendo de if")
        self.ts.delContexto()
        self.indent -= 2

    def enterIelse(self, ctx):
        self.ts.addContexto()
        self.indent += 2
        print(" " * (self.indent - 2) + "[INFO]: Entrando a else")

    def exitIelse(self, ctx):
        self._verificarVariablesNoUsadas()
        print(" " * (self.indent - 2) + "[INFO]: Saliendo de else")
        self.ts.delContexto()
        self.indent -= 2

    def enterIfor(self, ctx):
        self.ts.addContexto()
        self.indent += 2
        print(" " * (self.indent - 2) + "[INFO]: Entrando a for")

    def exitIfor(self, ctx):
        self._verificarVariablesNoUsadas()
        print(" " * (self.indent - 2) + "[INFO]: Saliendo de for")
        self.ts.delContexto()
        self.indent -= 2

    def enterIwhile(self, ctx):
        self.ts.addContexto()
        self.indent += 2
        print(" " * (self.indent - 2) + "[INFO]: Entrando a while")

    def exitIwhile(self, ctx):
        self._verificarVariablesNoUsadas()
        print(" " * (self.indent - 2) + "[INFO]: Saliendo de while")
        self.ts.delContexto()
        self.indent -= 2

    # -----------------------------
    # metodo privado: verificar variables no usadas 
    # -----------------------------
    def _verificarVariablesNoUsadas(self):
        contexto_actual = self.ts.contextos[-1]
        for nombre, var in contexto_actual.simbolos.items():
            if isinstance(var, Variable) and not var.getUsado():
                print(" " * self.indent + f"[ADVERTENCIA]: Variable '{nombre}' declarada pero no usada en contexto local")

    # -----------------------------
    # errores
    # -----------------------------
    def registrarError(self, tipo, msj):
        #marca flag y muestra mensaje
        self.huboErrores = True
        print(" " * self.indent + f"[ERROR {tipo.upper()}]: {msj}")
