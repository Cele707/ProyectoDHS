from compiladorParser import compiladorParser
from compiladorListener import compiladorListener
from TablaSimbolos import TablaSimbolos
from ID import Variable, Funcion


class Escucha(compiladorListener):
    def __init__(self):
        self.ts = TablaSimbolos()  # Singleton
        self.huboErrores = False
        self.indent = 0  # Nivel de sangría para los prints

    # -----------------------------
    # Contextos
    # -----------------------------
    def enterPrograma(self, ctx: compiladorParser.ProgramaContext):
        self.ts.addContexto()
        print("Comienza el parsing\n--- ANALISIS SEMANTICO ---")

    def exitPrograma(self, ctx: compiladorParser.ProgramaContext):
        hay_advertencias = False
        for contexto in self.ts.contextos:
            for nombre, var in contexto.simbolos.items():
                if isinstance(var, Variable) and not var.getUsado():
                    if not hay_advertencias:
                        print("\n--- ADVERTENCIA ---")
                        hay_advertencias = True
                    print(" " * self.indent + f"[ADVERTENCIA]: Variable '{nombre}' declarada pero no usada")
        if self.huboErrores:
            print("[INFO]: No se puede generar tabla de símbolos debido a errores")
        else:
            print("[INFO]: Tabla de símbolos final:")
            self.ts.imprimirTS()
        print("[INFO]: Fin del parsing")

    # -----------------------------
    # Declaraciones
    # -----------------------------
    def exitDeclaracion(self, ctx: compiladorParser.DeclaracionContext):
        tipo = ctx.tipo().getText()
        ids = [ctx.ID().getText()]

        def recolectar_listavar(lv, acumulador):
            if lv is not None and lv.ID() is not None:
                acumulador.append(lv.ID().getText())
                recolectar_listavar(lv.listavar(), acumulador)

        recolectar_listavar(ctx.listavar(), ids)

        for nombre in ids:
            if self.ts.buscarSimboloContexto(nombre):
                self.registrarError("semantico", f"'{nombre}' ya declarado en contexto actual")
            else:
                var = Variable(nombre, tipo)
                if ctx.inic() and ctx.inic().getChildCount() > 0:
                    var.setInicializado(True)
                self.ts.addSimbolo(var)
                print(" " * self.indent + f"[INFO]: Se agregó la variable '{nombre}' de tipo '{tipo}'")

    # -----------------------------
    # Asignaciones
    # -----------------------------
    def exitAsignacion(self, ctx: compiladorParser.AsignacionContext):
        exp_asig_ctx = ctx.expASIG()
        if exp_asig_ctx is None:
            return

        nombre = exp_asig_ctx.ID().getText()
        valor_ctx = exp_asig_ctx.opal()

        simbolo = self.ts.buscarSimbolo(nombre)
        if simbolo is None:
            self.registrarError("semantico", f"'{nombre}' usado sin declarar")
            return

        tipo_destino = simbolo.getTipoDato()
        tipo_valor = self._tipoExp(valor_ctx)

        if tipo_valor and tipo_destino != tipo_valor:
            self.registrarError("semantico",
                            f"Asignación incompatible: '{nombre}' es {tipo_destino} y se intenta asignar {tipo_valor}")

        simbolo.setInicializado(True)
        simbolo.setUsado(True)
        print(" " * self.indent + f"[INFO]: Asignación realizada: '{nombre}' inicializado y usado")

    # -----------------------------
    # Uso de variables en expresiones
    # -----------------------------
    def exitFactor(self, ctx: compiladorParser.FactorContext):
        if ctx.ID():
            nombre = ctx.ID().getText()
            simbolo = self.ts.buscarSimbolo(nombre)
            if simbolo is None:
                self.registrarError("semantico", f"'{nombre}' usado sin declarar")
            else:
                simbolo.setUsado(True)
                if not simbolo.getInicializado():
                    self.registrarError("semantico", f"'{nombre}' usado sin inicializar")
                print(" " * self.indent + f"[INFO]: Uso de variable '{nombre}' detectado")

    # -----------------------------
    # Evaluación de tipos de expresiones
    # -----------------------------
    def _tipoExp(self, ctx):
        if ctx is None:
            return None

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

        if hasattr(ctx, 'NUM') and ctx.NUM():
            return "int"

        tipos = set()
        for i in range(ctx.getChildCount()):
            tipo_hijo = self._tipoExp(ctx.getChild(i))
            if tipo_hijo:
                tipos.add(tipo_hijo)

        if len(tipos) == 1:
            return tipos.pop()
        elif len(tipos) > 1:
            self.registrarError("semantico", "Tipos incompatibles en expresión")
            return None
        else:
            return None

    # -----------------------------
    # Contexto de bloques (if, else, for, while)
    # -----------------------------
        # -----------------------------
# Contexto de bloques (if, else, for, while)
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
# Método privado: verificar variables no usadas
# -----------------------------
    def _verificarVariablesNoUsadas(self):
        contexto_actual = self.ts.contextos[-1]
        for nombre, var in contexto_actual.simbolos.items():
            if isinstance(var, Variable) and not var.getUsado():
                print(" " * self.indent + f"[ADVERTENCIA]: Variable '{nombre}' declarada pero no usada en contexto local")

    # -----------------------------
    # Errores
    # -----------------------------
    def registrarError(self, tipo, msj):
        self.huboErrores = True
        print(" " * self.indent + f"[ERROR {tipo.upper()}]: {msj}")
