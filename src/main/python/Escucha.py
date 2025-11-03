from compiladorParser import compiladorParser
from compiladorListener import compiladorListener
from TablaSimbolos import TablaSimbolos
from ID import Variable, Funcion


class Escucha(compiladorListener):
    def __init__(self):
        self.ts = TablaSimbolos()     # Singleton de tabla de s铆mbolos
        self.huboErrores = False      # Flag de error sem谩ntico
        self.indent = 0               # Nivel de indentaci贸n para prints

        # 馃斀 NUEVO: banderas para procesar declaraciones en orden inverso
        self.leyendoDeclaracion = False
        self.bufferDeclaracion = []

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

        # Imprime la tabla de s铆mbolos final si no hubo errores
        if self.huboErrores:
            print("[INFO]: No se puede generar tabla de s铆mbolos debido a errores")
        else:
            print("[INFO]: Tabla de s铆mbolos final:")
            self.ts.imprimirTS()
        print("[INFO]: Fin del parsing")

    # =============================================================
    # DECLARACIONES
    # =============================================================

    # 馃斀 NUEVO
    def enterDeclaracion(self, ctx: compiladorParser.DeclaracionContext):
        """
        Activa el modo de lectura de declaraci贸n inversa.
        Sirve para evitar errores de 'usado sin inicializar' en declaraciones m煤ltiples.
        """
        self.leyendoDeclaracion = True
        self.bufferDeclaracion = []

    def exitDeclaracion(self, ctx: compiladorParser.DeclaracionContext):
        tipo = ctx.tipo().getText()

        # Recolecta triples (nombre, tiene_inic, inic_ctx) del primer ID y de la lista recursiva
        vars_list = []
        # primer id
        nombre0 = ctx.ID().getText()
        inic0 = ctx.inic() if (ctx.inic() is not None and ctx.inic().getChildCount() > 0) else None
        vars_list.append((nombre0, inic0 is not None, inic0))

        # recursiva sobre listavar: cada nodo listavar tiene ID() e inic()
        def recolectar_listavar(lv, acumulador):
            if lv is None:
                return
            if lv.ID() is not None:
                inic_lv = lv.inic() if (lv.inic() is not None and lv.inic().getChildCount() > 0) else None
                acumulador.append((lv.ID().getText(), inic_lv is not None, inic_lv))
            # seguir la recursión
            if hasattr(lv, "listavar"):
                recolectar_listavar(lv.listavar(), acumulador)

        recolectar_listavar(ctx.listavar(), vars_list)

        # --------------------------------------------------
        # Procesar en orden NATURAL (izquierda -> derecha).
        # Esto permite que una variable anterior quede inicializada
        # antes de evaluar inicializadores que la usen.
        # --------------------------------------------------
        for nombre, tiene_inic, inic_ctx in vars_list:
            if self.ts.buscarSimboloContexto(nombre):
                self.registrarError("semantico", f"'{nombre}' ya declarado en contexto actual")
            else:
                var = Variable(nombre, tipo)
                var.advertencia_reportada = False  # si usás esa bandera
                # Agregar a tabla ANTES de evaluar inicializadores posteriores,
                # pero no marcar como inicializado todavía hasta que la inicialización sea validada.
                self.ts.addSimbolo(var)
                print(" " * self.indent + f"[INFO]: Variable '{nombre}' de tipo '{tipo}' agregada"
                                        + ( " (inicializada)" if tiene_inic else "" ))

                # Si tiene inicializador, evaluarlo y validar tipos
                if tiene_inic and inic_ctx is not None:
                    # intentamos obtener el contexto de la expresión dentro de inic
                    valor_ctx = None
                    # Muchos grammars usan inic().opal() o ini().exp(), probamos accesos comunes:
                    if hasattr(inic_ctx, "opal") and inic_ctx.opal() is not None:
                        valor_ctx = inic_ctx.opal()
                    elif inic_ctx.getChildCount() > 0:
                        # buscar el primer hijo que sea expresión (defensivo)
                        # nota: esto es general; ajustá si sabés la estructura exacta
                        for i in range(inic_ctx.getChildCount()):
                            ch = inic_ctx.getChild(i)
                            # asumimos que los nodos de expresión tienen getText y getChildCount
                            if hasattr(ch, "getText"):
                                valor_ctx = ch
                                break

                    # Evaluamos tipo del valor **con comprobaciones activas**.
                    # Como estamos en exitDeclaracion, ya agregamos las variables previas
                    # a la TS; además, para que se registren errores por uso sin inicializar,
                    # forzamos leyendoDeclaracion = False temporalmente.
                    prev_flag = self.leyendoDeclaracion
                    self.leyendoDeclaracion = False
                    try:
                        tipo_valor = self._tipoExp(valor_ctx) if valor_ctx is not None else None
                    finally:
                        # restaurar flag original
                        self.leyendoDeclaracion = prev_flag

                    # Comprobación de compatibilidad de tipos
                    if tipo_valor and tipo != tipo_valor:
                        # mismatch (ej: int y double)
                        self.registrarError("semantico",
                                            f"Inicialización incompatible: '{nombre}' es {tipo} y se intenta inicializar con {tipo_valor}")

                    # Si no hubo error, marcar inicializada
                    # (si hubo error igualmente la marca evita cascada de errores)
                    var.setInicializado(True)
        # Desactivar modo lectura de declaración
        self.leyendoDeclaracion = False
    # =============================================================
    # ASIGNACIONES
    # =============================================================
    def exitAsignacion(self, ctx: compiladorParser.AsignacionContext):
        exp_asig_ctx = ctx.expASIG()
        if exp_asig_ctx is None:
            return
        # Obtiene el nombre de la variable destino y la expresi贸n a asignar
        nombre = exp_asig_ctx.ID().getText()
        valor_ctx = exp_asig_ctx.opal()
        
        # Verifica que la variable exista
        simbolo = self._verificarExistenciaVariable(nombre)
        if simbolo is None:
            return
        
        # Obtiene tipo de la variable destino y tipo de la expresi贸n
        tipo_destino = simbolo.getTipoDato()
        tipo_valor = self._tipoExp(valor_ctx)
        
        # Compara el tipo de la variable destino con el tipo de la expresi贸n
        if tipo_valor and tipo_destino != tipo_valor:
            self.registrarError("semantico",
                                f"Asignaci贸n incompatible: '{nombre}' es {tipo_destino} y se intenta asignar {tipo_valor}")
       
        # Marca variable como inicializada y usada
        simbolo.setInicializado(True)
        simbolo.setUsado(True)
        print(" " * self.indent + f"[INFO]: Asignaci贸n realizada: '{nombre}' inicializado y usado")

    # =============================================================
    # USO DE VARIABLES EN EXPRESIONES
    # =============================================================
    def exitFactor(self, ctx: compiladorParser.FactorContext):
        if ctx.ID():
            nombre = ctx.ID().getText()
            simbolo = self._verificarExistenciaVariable(nombre)
            if simbolo is None:
                return

            # 馃斀 CAMBIO: durante una declaraci贸n, no reportar error de inicializaci贸n
            if self.leyendoDeclaracion:
                simbolo.setUsado(True)
                return

            # Si la variable estaba declarada, la marca como usada
            simbolo.setUsado(True)
            if not simbolo.getInicializado():
                # Para variables usadas pero sin inicializar
                self.registrarError("semantico", f"'{nombre}' usado sin inicializar")
            print(" " * self.indent + f"[INFO]: Uso de variable '{nombre}' detectado")

    # =============================================================
    # EVALUACI脫N DE TIPOS DE EXPRESIONES
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
            # ignorar 'no inicializado' si estamos evaluando declaracion
            if not self.leyendoDeclaracion:
                if not var.getInicializado():
                    self.registrarError("semantico", f"'{nombre}' usado sin inicializar")
            return var.getTipoDato()

            
        # Nodo NUM
        if hasattr(ctx, 'NUM') and ctx.NUM():
            return "int"
        
        # Verifica tipos de los hijos de la expresi贸n
        tipos = set()
        for i in range(ctx.getChildCount()):
            tipo_hijo = self._tipoExp(ctx.getChild(i))
            if tipo_hijo:
                tipos.add(tipo_hijo)
                
        # Si todos los hijos son del mismo tipo devuelve ese tipo
        if len(tipos) == 1:
            return tipos.pop()
        elif len(tipos) > 1:
            self.registrarError("semantico", "Tipos incompatibles en expresi贸n")
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

    # ---- Inicializaci贸n dentro del for ----
    def exitForInicializacion(self, ctx: compiladorParser.ForInicializacionContext):
        """
        Maneja la declaración dentro del encabezado de un bucle 'for'.
        Ejemplo: for (int i = 0, k, j = 2; i < 5; ++i)
        """
        if ctx.tipo() and ctx.ID():
            tipo = ctx.tipo().getText()

            # Lista para almacenar (nombre, tiene_inic, inic_ctx)
            vars_list = []

            # Primer ID
            nombre0 = ctx.ID().getText()
            inic0 = ctx.inic() if (ctx.inic() is not None and ctx.inic().getChildCount() > 0) else None
            vars_list.append((nombre0, inic0 is not None, inic0))

            # Función recursiva que recorre listavar
            def recolectar_listavar(lv, acumulador):
                if lv is None:
                    return
                if lv.ID() is not None:
                    tiene_inic = (lv.inic() is not None and lv.inic().getChildCount() > 0)
                    inic_lv = lv.inic() if tiene_inic else None
                    acumulador.append((lv.ID().getText(), tiene_inic, inic_lv))
                if hasattr(lv, "listavar"):
                    recolectar_listavar(lv.listavar(), acumulador)

            recolectar_listavar(ctx.listavar(), vars_list)

            # Procesar en orden natural (izq -> der) para mantener inicializaciones en cadena
            for nombre, inicializada, inic_ctx in vars_list:
                if self.ts.buscarSimboloContexto(nombre):
                    self.registrarError("semantico", f"'{nombre}' ya declarado en contexto actual (for)")
                else:
                    var = Variable(nombre, tipo)
                    # agregar antes de evaluar inicializadores posteriores
                    self.ts.addSimbolo(var)
                    print(" " * self.indent +
                        f"[INFO]: Variable '{nombre}' declarada dentro del for (tipo {tipo})"
                        + (" (inicializada)" if inicializada else ""))

                    if inicializada and inic_ctx is not None:
                        # obtener el ctx de la expresión de la misma forma defensiva
                        valor_ctx = None
                        if hasattr(inic_ctx, "opal") and inic_ctx.opal() is not None:
                            valor_ctx = inic_ctx.opal()
                        elif inic_ctx.getChildCount() > 0:
                            valor_ctx = inic_ctx.getChild(0)

                        prev_flag = self.leyendoDeclaracion
                        self.leyendoDeclaracion = False
                        try:
                            tipo_valor = self._tipoExp(valor_ctx) if valor_ctx is not None else None
                        finally:
                            self.leyendoDeclaracion = prev_flag

                        if tipo_valor and tipo != tipo_valor:
                            self.registrarError("semantico",
                                                f"Inicialización incompatible en for: '{nombre}' es {tipo} y se intenta inicializar con {tipo_valor}")

                        var.setInicializado(True)
    # ---- WHILE ----
    def enterIwhile(self, ctx):
        self.indent += 2
        print(" " * (self.indent - 2) + "[INFO]: Entrando a while")

    def exitIwhile(self, ctx):
        self._verificarVariablesNoUsadas()
        print(" " * (self.indent - 2) + "[INFO]: Saliendo de while")
        self.indent -= 2

    # =============================================================
    # M脡TODOS AUXILIARES
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
        simbolo = self.ts.buscarSimbolo(nombre)

        # Durante la lectura de la misma declaración múltiple NO hay error si no está inicializada
        if simbolo is None and not self.leyendoDeclaracion:
            self.registrarError("semantico", f"Variable '{nombre}' no reconocida o no declarada")
            return None

        return simbolo


    def registrarError(self, tipo, msj):
        """
        Registra un error sem谩ntico y marca el flag de errores.
        """
        self.huboErrores = True
        print(" " * self.indent + f"[ERROR {tipo.upper()}]: {msj}")