from compiladorParser import compiladorParser
from compiladorListener import compiladorListener
from TablaSimbolos import TablaSimbolos
from ID import Variable, Funcion


class Escucha(compiladorListener):
    def __init__(self):
        self.ts = TablaSimbolos()     # Singleton de tabla de símbolos
        self.huboErrores = False      # Flag de error semántico
        self.indent = 0               # Nivel de indentación para prints

    # =============================================================
    # PROGRAMA PRINCIPAL
    # =============================================================
    def enterPrograma(self, ctx: compiladorParser.ProgramaContext):
        print("Comienza el parsing\n")

    def exitPrograma(self, ctx: compiladorParser.ProgramaContext):
        # Verifica variables declaradas pero no usadas en todos los contextos
        hay_advertencias = False
        for contexto in self.ts.contextos:
            for nombre, var in contexto.simbolos.items():
                if isinstance(var, Variable) and not var.getUsado():
                    if not hay_advertencias:
                        print("\n--- ADVERTENCIA ---")
                        hay_advertencias = True
                    print(" " * self.indent + f"[ADVERTENCIA]: Variable '{nombre}' declarada pero no usada")

        # Imprime la tabla de símbolos final si no hubo errores
        if self.huboErrores:
            print("[INFO]: No se puede generar tabla de símbolos debido a errores")
        else:
            print("[INFO]: Tabla de símbolos final:")
            self.ts.imprimirTS()
        print("[INFO]: Fin del parsing")

    # =============================================================
    # DECLARACIONES
    # =============================================================
    def exitDeclaracion(self, ctx: compiladorParser.DeclaracionContext):
        tipo = ctx.tipo().getText()

        # Recolecta pares (nombre, tiene_inic) del primer ID y de la lista recursiva
        vars_list = []
        # primer id
        nombre0 = ctx.ID().getText()
        tiene_inic0 = (ctx.inic() is not None and ctx.inic().getChildCount() > 0)
        vars_list.append((nombre0, tiene_inic0))

        # recursiva sobre listavar: cada nodo listavar tiene ID() e inic()
        def recolectar_listavar(lv, acumulador):
            if lv is None:
                return
            if lv.ID() is not None:
                acumulador.append((lv.ID().getText(), (lv.inic() is not None and lv.inic().getChildCount() > 0)))
            # seguir la recursión
            if hasattr(lv, "listavar"):
                recolectar_listavar(lv.listavar(), acumulador)

        recolectar_listavar(ctx.listavar(), vars_list)

        # Procesa cada variable con su información de inicialización correcta
        for nombre, tiene_inic in vars_list:
            if self.ts.buscarSimboloContexto(nombre):
                self.registrarError("semantico", f"'{nombre}' ya declarado en contexto actual")
            else:
                var = Variable(nombre, tipo)
                var.advertencia_reportada = False  # si usás esa bandera
                if tiene_inic:
                    var.setInicializado(True)
                self.ts.addSimbolo(var)
                print(" " * self.indent + f"[INFO]: Variable '{nombre}' de tipo '{tipo}' agregada"
                                        + ( " (inicializada)" if tiene_inic else "" ))

    # =============================================================
    # ASIGNACIONES
    # =============================================================
    def exitAsignacion(self, ctx: compiladorParser.AsignacionContext):
        exp_asig_ctx = ctx.expASIG()
        if exp_asig_ctx is None:
            return
        # Obtiene el nombre de la variable destino y la expresión a asignar
        nombre = exp_asig_ctx.ID().getText()
        valor_ctx = exp_asig_ctx.opal()
        
        # Verifica que la variable exista
        simbolo = self._verificarExistenciaVariable(nombre)
        if simbolo is None:
            return
        
        # Obtiene tipo de la variable destino y tipo de la expresión
        tipo_destino = simbolo.getTipoDato()
        tipo_valor = self._tipoExp(valor_ctx)
        
        # Compara el tipo de la variable destino con el tipo de la expresión
        if tipo_valor and tipo_destino != tipo_valor:
            self.registrarError("semantico",
                                f"Asignación incompatible: '{nombre}' es {tipo_destino} y se intenta asignar {tipo_valor}")
       
        # Marca variable como inicializada y usada
        simbolo.setInicializado(True)
        simbolo.setUsado(True)
        print(" " * self.indent + f"[INFO]: Asignación realizada: '{nombre}' inicializado y usado")

    # =============================================================
    # USO DE VARIABLES EN EXPRESIONES
    # =============================================================
    def exitFactor(self, ctx: compiladorParser.FactorContext):
        if ctx.ID():
            nombre = ctx.ID().getText()
            simbolo = self._verificarExistenciaVariable(nombre)
            if simbolo is None:
                return
            # Si la variable estaba declarada, la marca como usada
            simbolo.setUsado(True)
            if not simbolo.getInicializado():
                # Para variables usadas pero sin inicializar
                self.registrarError("semantico", f"'{nombre}' usado sin inicializar")
            print(" " * self.indent + f"[INFO]: Uso de variable '{nombre}' detectado")

    # =============================================================
    # EVALUACIÓN DE TIPOS DE EXPRESIONES
    # =============================================================
    def _tipoExp(self, ctx):
        if ctx is None:
            return None
        
        # Nodo ID
        if hasattr(ctx, 'ID') and ctx.ID():
            nombre = ctx.ID().getText()
            var = self._verificarExistenciaVariable(nombre)
            if var is None:
                return None
            var.setUsado(True)
            if not var.getInicializado():
                self.registrarError("semantico", f"'{nombre}' usado sin inicializar")
            return var.getTipoDato()
            
        # Nodo NUM
        if hasattr(ctx, 'NUM') and ctx.NUM():
            return "int"
        
        # Verifica tipos de los hijos de la expresión
        tipos = set()
        for i in range(ctx.getChildCount()):
            tipo_hijo = self._tipoExp(ctx.getChild(i))
            if tipo_hijo:
                tipos.add(tipo_hijo)
                
        # Si todos los hijos son del mismo tipo devuelve ese tipo
        if len(tipos) == 1:
            return tipos.pop()
        elif len(tipos) > 1:
            self.registrarError("semantico", "Tipos incompatibles en expresión")
            return None
        else:
            return None

    # =============================================================
    # CONTEXTOS DE BLOQUES (if, else, for, while)
    # =============================================================
    def enterBloque(self, ctx):
        self.ts.addContexto()
        self.indent += 2
        print(" " * (self.indent - 2) + "[INFO]: Entrando a bloque")

    def exitBloque(self, ctx):
        self._verificarVariablesNoUsadas()
        print(" " * (self.indent - 2) + "[INFO]: Saliendo de bloque")
        self.ts.delContexto()
        self.indent -= 2

    # ---- IF ----
    def enterIif(self, ctx):
        self.indent += 2
        print(" " * (self.indent - 2) + "[INFO]: Entrando a if")

    def exitIif(self, ctx):
        self._verificarVariablesNoUsadas()
        print(" " * (self.indent - 2) + "[INFO]: Saliendo de if")
        self.indent -= 2

    # ---- ELSE ----
    def enterIelse(self, ctx):
        self.indent += 2
        print(" " * (self.indent - 2) + "[INFO]: Entrando a else")

    def exitIelse(self, ctx):
        self._verificarVariablesNoUsadas()
        print(" " * (self.indent - 2) + "[INFO]: Saliendo de else")
        self.indent -= 2

    # ---- FOR ----
    def enterIfor(self, ctx):
        self.indent += 2
        print(" " * (self.indent - 2) + "[INFO]: Entrando a for")

    def exitIfor(self, ctx):
        self._verificarVariablesNoUsadas()
        print(" " * (self.indent - 2) + "[INFO]: Saliendo de for")
        self.indent -= 2

    # ---- Inicialización dentro del for ----
    def exitForInicializacion(self, ctx: compiladorParser.ForInicializacionContext):
        """
        Maneja la declaración dentro del encabezado de un bucle 'for'.
        Ejemplo: for (int i = 0, k, j = 2; i < 5; ++i)
        """

        if ctx.tipo() and ctx.ID():
            tipo = ctx.tipo().getText()

            # Lista para almacenar (nombre, inicializada?)
            vars_list = []

            # Primer ID
            nombre0 = ctx.ID().getText()
            inic0 = (ctx.inic() is not None and ctx.inic().getChildCount() > 0)
            vars_list.append((nombre0, inic0))

            # Función recursiva que recorre listavar
            def recolectar_listavar(lv, acumulador):
                if lv is None:
                    return
                if lv.ID() is not None:
                    tiene_inic = (lv.inic() is not None and lv.inic().getChildCount() > 0)
                    acumulador.append((lv.ID().getText(), tiene_inic))
                if hasattr(lv, "listavar"):
                    recolectar_listavar(lv.listavar(), acumulador)

            # Recolectar todas las variables del for
            recolectar_listavar(ctx.listavar(), vars_list)

            # Procesar cada variable
            for nombre, inicializada in vars_list:
                if self.ts.buscarSimboloContexto(nombre):
                    self.registrarError("semantico", f"'{nombre}' ya declarado en contexto actual (for)")
                else:
                    var = Variable(nombre, tipo)
                    if inicializada:
                        var.setInicializado(True)
                    self.ts.addSimbolo(var)
                    print(" " * self.indent +
                        f"[INFO]: Variable '{nombre}' declarada dentro del for (tipo {tipo})"
                        + (" (inicializada)" if inicializada else ""))

    # ---- WHILE ----
    def enterIwhile(self, ctx):
        self.indent += 2
        print(" " * (self.indent - 2) + "[INFO]: Entrando a while")

    def exitIwhile(self, ctx):
        self._verificarVariablesNoUsadas()
        print(" " * (self.indent - 2) + "[INFO]: Saliendo de while")
        self.indent -= 2

    # =============================================================
    # MÉTODOS AUXILIARES
    # =============================================================
    def _verificarVariablesNoUsadas(self):
        """
        Recorre el contexto actual y muestra advertencias para variables
        que fueron declaradas pero nunca usadas.
        """
        contexto_actual = self.ts.contextos[-1]
        for nombre, var in contexto_actual.simbolos.items():
            if isinstance(var, Variable) and not var.getUsado():
                print(" " * self.indent + f"[ADVERTENCIA]: Variable '{nombre}' declarada pero no usada en contexto local")

    def _verificarExistenciaVariable(self, nombre):
        """
        Verifica si una variable fue declarada antes de su uso.
        Si no fue declarada, registra un error semántico.
        Devuelve el símbolo si existe, o None si no existe.
        """
        simbolo = self.ts.buscarSimbolo(nombre)
        if simbolo is None:
            self.registrarError("semantico", f"Variable '{nombre}' no reconocida o no declarada")
            return None
        return simbolo

    def registrarError(self, tipo, msj):
        """
        Registra un error semántico y marca el flag de errores.
        """
        self.huboErrores = True
        print(" " * self.indent + f"[ERROR {tipo.upper()}]: {msj}")
