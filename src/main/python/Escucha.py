from compiladorParser import compiladorParser
from compiladorListener import compiladorListener
from TablaSimbolos import TablaSimbolos
from ID import Variable, Funcion


class Escucha(compiladorListener):
    """
    Clase que implementa el Listener para el análisis semántico.
    Se encarga de construir la Tabla de Símbolos y detectar errores de contexto,
    declaración, inicialización, uso y compatibilidad de tipos.
    """
    def __init__(self):
        super().__init__()
        self.ts = TablaSimbolos()      #singleton de tabla de símbolos
        self.huboErrores = False       #flag para indicar si hubo errores semánticos
        self.indent = 0                #nivel de indentación para mensajes de consola

        #bandera especial para manejar dependencias en declaraciones múltiples
        self.leyendoDeclaracion = False
        self.bufferDeclaracion = []    #no usado en la lógica actual, pero mantenido

    # =============================================================
    # PROGRAMA PRINCIPAL
    # =============================================================
    def enterPrograma(self, ctx: compiladorParser.ProgramaContext):
        """Inicio del análisis."""
        print("Comienza el parsing\n")

    def exitPrograma(self, ctx: compiladorParser.ProgramaContext):
        """Fin del análisis y resumen de resultados."""
        
        #verifica variables declaradas pero no usadas en todos los contextos (global)
        hay_advertencias = False
        for contexto in self.ts.contextos:
            for nombre, var in contexto.simbolos.items():
                if isinstance(var, Variable) and not var.getUsado():
                    if not hay_advertencias:
                        print("\n--- ADVERTENCIA ---")
                        hay_advertencias = True
                    print(" " * self.indent + f"[ADVERTENCIA]: Variable '{nombre}' declarada pero no usada")

        #imprime la tabla de símbolos final si no hubo errores
        if self.huboErrores:
            print("[INFO]: No se puede generar tabla de símbolos debido a errores")
        else:
            print("[INFO]: Tabla de símbolos final:")
            self.ts.imprimirTS()
        print("[INFO]: Fin del parsing")

    # =============================================================
    # DECLARACIONES
    # =============================================================

    def enterDeclaracion(self, ctx: compiladorParser.DeclaracionContext):
        """
        Activa la bandera de lectura de declaración.
        Esto previene que se reporten errores de 'usado sin inicializar/declarar'
        para las variables que están siendo inicializadas por otras en la misma línea
        (ej: int a=1, b=a;).
        """
        self.leyendoDeclaracion = True
        self.bufferDeclaracion = [] #se limpia, aunque no se usa en el chequeo semántico

    def exitDeclaracion(self, ctx: compiladorParser.DeclaracionContext):
        """
        Maneja la declaración de variables. Se realiza en dos pasadas implícitas:
        1. Recolección e inserción de símbolos (para que estén disponibles).
        2. Chequeo de compatibilidad de tipos en la inicialización (donde se usan las variables).
        """
        tipo = ctx.tipo().getText()

        #recolecta triples (nombre, tiene_inic, inic_ctx) del primer ID y de la lista recursiva
        vars_list = []
        #primer ID
        nombre0 = ctx.ID().getText()
        inic0 = ctx.inic() if (ctx.inic() is not None and ctx.inic().getChildCount() > 0) else None
        vars_list.append((nombre0, inic0 is not None, inic0))

        #función recursiva sobre listavar (coma y ID siguiente)
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
        # FASE 1: Inserción de Símbolos (Orden de procesamiento: izquierda -> derecha)
        # --------------------------------------------------
        for nombre, tiene_inic, inic_ctx in vars_list:
            if self.ts.buscarSimboloContexto(nombre):
                self.registrarError("semantico", f"'{nombre}' ya declarado en contexto actual")
            else:
                var = Variable(nombre, tipo)
                #agregar a tabla ANTES de evaluar inicializadores posteriores
                self.ts.addSimbolo(var)
                print(" " * self.indent + f"[INFO]: Variable '{nombre}' de tipo '{tipo}' agregada"
                                         + ( " (inicializada)" if tiene_inic else "" ))

        # --------------------------------------------------
        # FASE 2: Chequeo de Inicialización y Tipos
        # --------------------------------------------------
        for nombre, tiene_inic, inic_ctx in vars_list:
            #obtener el símbolo recién insertado
            var = self.ts.buscarSimboloContexto(nombre)
            
            if var and tiene_inic and inic_ctx is not None:
                #intentamos obtener el contexto de la expresión dentro de inic
                valor_ctx = None
                
                #acceso defensivo a la expresión (asumiendo opal() o el primer hijo)
                if hasattr(inic_ctx, "opal") and inic_ctx.opal() is not None:
                    valor_ctx = inic_ctx.opal()
                elif inic_ctx.getChildCount() > 0:
                    # buscar el primer hijo que sea la expresión de valor
                    for i in range(inic_ctx.getChildCount()):
                        ch = inic_ctx.getChild(i)
                        if hasattr(ch, "getText"):
                            valor_ctx = ch
                            break

                #evaluamos tipo del valor con chequeo de uso habilitado (leyendoDeclaracion=False)
                prev_flag = self.leyendoDeclaracion
                self.leyendoDeclaracion = False # Temporalmente desactivado para chequear uso
                try:
                    tipo_valor = self._tipoExp(valor_ctx) if valor_ctx is not None else None
                finally:
                    # restaurar flag original
                    self.leyendoDeclaracion = prev_flag

                #comprobación de compatibilidad de tipos (Ej: int = float)
                if tipo_valor and tipo != tipo_valor:
                    self.registrarError("semantico",
                                        f"Inicialización incompatible: '{nombre}' es {tipo} y se intenta inicializar con {tipo_valor}")

                #si no hubo error de tipo (o si hubo, para evitar errores en cascada), marcamos inicializada
                var.setInicializado(True)
                
        #desactivar modo lectura de declaración
        self.leyendoDeclaracion = False

    # =============================================================
    # ASIGNACIONES
    # =============================================================
    def exitAsignacion(self, ctx: compiladorParser.AsignacionContext):
        """Verifica que la variable destino exista y que la asignación sea compatible en tipos."""
        exp_asig_ctx = ctx.expASIG()
        if exp_asig_ctx is None:
            return
            
        #obtiene el nombre de la variable destino y la expresión a asignar
        nombre = exp_asig_ctx.ID().getText()
        valor_ctx = exp_asig_ctx.opal()
        
        #verifica que la variable exista y obtén el simbolo
        simbolo = self._verificarExistenciaVariable(nombre)
        if simbolo is None:
            return
            
        #obtiene tipo de la variable destino y tipo de la expresión
        tipo_destino = simbolo.getTipoDato()
        tipo_valor = self._tipoExp(valor_ctx)
        
        #compara el tipo de la variable destino con el tipo de la expresión
        if tipo_valor and tipo_destino != tipo_valor:
            self.registrarError("semantico",
                                f"Asignación incompatible: '{nombre}' es {tipo_destino} y se intenta asignar {tipo_valor}")
        
        #marca variable como inicializada y usada
        simbolo.setInicializado(True)
        simbolo.setUsado(True)
        print(" " * self.indent + f"[INFO]: Asignación realizada: '{nombre}' inicializado y usado")

    # =============================================================
    # USO DE VARIABLES EN EXPRESIONES
    # =============================================================
    def exitFactor(self, ctx: compiladorParser.FactorContext):
        """
        Detecta el uso de variables dentro de expresiones (factores).
        Aquí se chequea si la variable fue usada sin inicializar.
        """
        if ctx.ID():
            nombre = ctx.ID().getText()
            simbolo = self._verificarExistenciaVariable(nombre)
            if simbolo is None:
                return

            # Si estamos dentro de una declaración, la marca como usada pero NO reporta error
            # de 'no inicializada', ya que la inicialización se chequea después.
            if self.leyendoDeclaracion:
                simbolo.setUsado(True)
                return

            # Si la variable estaba declarada, la marca como usada
            simbolo.setUsado(True)
            if not simbolo.getInicializado():
                # Para variables usadas pero sin inicializar (fuera de una declaración)
                self.registrarError("semantico", f"'{nombre}' usado sin inicializar")
                
            print(" " * self.indent + f"[INFO]: Uso de variable '{nombre}' detectado")

    # =============================================================
    # EVALUACIÓN DE TIPOS DE EXPRESIONES (Recursiva)
    # =============================================================
    def _tipoExp(self, ctx):
        """Función auxiliar para determinar el tipo de dato resultante de una expresión (recursiva)."""
        if ctx is None:
            return None
            
        # Nodo ID: Se usa una variable
        if hasattr(ctx, 'ID') and ctx.ID():
            nombre = ctx.ID().getText()
            var = self._verificarExistenciaVariable(nombre)
            if var is None:
                return None
            #si NO estamos leyendo una declaración, reportar error de 'no inicializado'
            if not self.leyendoDeclaracion:
                if not var.getInicializado():
                    self.registrarError("semantico", f"'{nombre}' usado sin inicializar")
            
            #la variable se marca como usada al ser parte de una expresión
            var.setUsado(True) 
            return var.getTipoDato()
            
            
        # Nodo NUM: Literal entero
        if hasattr(ctx, 'NUM') and ctx.NUM():
            # Aquí podrías distinguir entre int y float si tu gramática lo soporta
            return "int"
            
        #verifica tipos de los hijos de la expresión (operadores)
        tipos = set()
        for i in range(ctx.getChildCount()):
            # Llamada recursiva a la expresión hija
            tipo_hijo = self._tipoExp(ctx.getChild(i))
            if tipo_hijo:
                tipos.add(tipo_hijo)
                
        #si todos los hijos son del mismo tipo devuelve ese tipo (Ej: int + int = int)
        if len(tipos) == 1:
            return tipos.pop()
        elif len(tipos) > 1:
            #tipos incompatibles en operación (Ej: int + float)
            self.registrarError("semantico", "Tipos incompatibles en expresión")
            return None
        else:
            return None

    # =============================================================
    # CONTEXTOS DE BLOQUES (if, else, for, while)
    # =============================================================
    
    # ---- BLOQUE GENERAL ----
    def enterBloque(self, ctx):
        """Abre un nuevo contexto (ámbito) en la Tabla de Símbolos."""
        self.ts.addContexto()
        #self.indent += 2
        #print(" " * (self.indent - 2) + "[INFO]: Entrando a bloque")

    def exitBloque(self, ctx):
        """Cierra el contexto actual y verifica variables no usadas localmente."""
        self._verificarVariablesNoUsadasLocal() # Nota: función renombrada para mayor claridad
        #print(" " * (self.indent - 2) + "[INFO]: Saliendo de bloque")
        self.ts.delContexto()
        #self.indent -= 2
        
    
    # # ---- IF ----
    # def enterIif(self, ctx):
    #     # La gestión del contexto se hace en enter/exitBloque si Iif envuelve a Bloque
    #     self.indent += 2
    #     print(" " * (self.indent - 2) + "[INFO]: Entrando a if")

    # def exitIif(self, ctx):
    #     # La verificación de uso se hace en exitBloque si la gramática está anidada
    #     self.indent -= 2
    #     print(" " * self.indent + "[INFO]: Saliendo de if")

    # # ---- ELSE ----
    # def enterIelse(self, ctx):
    #     self.indent += 2
    #     print(" " * (self.indent - 2) + "[INFO]: Entrando a else")

    # def exitIelse(self, ctx):
    #     self.indent -= 2
    #     print(" " * self.indent + "[INFO]: Saliendo de else")

    # ---- FOR ----
    def enterIfor(self, ctx):
        #self.indent += 2
        #print(" " * (self.indent - 2) + "[INFO]: Entrando a for")
        # El contexto del for (para 'i') DEBE abrirse en enterIfor si la gramática no tiene un bloque.
        # Si la gramática es for (...) instruccion, el ámbito de 'i' está en la instrucción/bloque.
        # Para simplificar, asumimos que el contexto se abre en enterIfor para la inicialización.
        self.ts.addContexto() 
        #self.indent += 2 # Añadir indentación para el cuerpo del for

    def exitIfor(self, ctx):
        # Verifica las variables declaradas en el encabezado del for (como 'i')
        self._verificarVariablesNoUsadasLocal()
        self.ts.delContexto() # Cierra el contexto del for (donde se declaró 'i')
        #self.indent -= 2
        #print(" " * self.indent + "[INFO]: Saliendo de for")
        #self.indent -= 2

    # ---- Inicialización dentro del for (Ej: for (int i = 0; ...)) ----
    def exitForInicializacion(self, ctx: compiladorParser.ForInicializacionContext):
        """
        Maneja la declaración de variables dentro del encabezado de un bucle 'for'.
        Se usa la misma lógica de dos fases que en exitDeclaracion.
        """
        if ctx.tipo() and ctx.ID():
            tipo = ctx.tipo().getText()

            # --- FASE 1: Recolección e Inserción de Símbolos ---
            vars_list = []
            # Primer ID
            nombre0 = ctx.ID().getText()
            inic0 = ctx.inic() if (ctx.inic() is not None and ctx.inic().getChildCount() > 0) else None
            vars_list.append((nombre0, inic0 is not None, inic0))

            #función recursiva que recorre listavar
            def recolectar_listavar(lv, acumulador):
                if lv is None: return
                if lv.ID() is not None:
                    tiene_inic = (lv.inic() is not None and lv.inic().getChildCount() > 0)
                    inic_lv = lv.inic() if tiene_inic else None
                    acumulador.append((lv.ID().getText(), tiene_inic, inic_lv))
                if hasattr(lv, "listavar"):
                    recolectar_listavar(lv.listavar(), acumulador)

            recolectar_listavar(ctx.listavar(), vars_list)

            #inserción de simbolos
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

            # --- FASE 2: Chequeo de Inicialización y Tipos ---
            for nombre, inicializada, inic_ctx in vars_list:
                var = self.ts.buscarSimboloContexto(nombre)
                if var and inicializada and inic_ctx is not None:
                    # obtener el ctx de la expresión de la misma forma defensiva
                    valor_ctx = None
                    if hasattr(inic_ctx, "opal") and inic_ctx.opal() is not None:
                        valor_ctx = inic_ctx.opal()
                    elif inic_ctx.getChildCount() > 0:
                        valor_ctx = inic_ctx.getChild(0)

                    #evaluación temporal con leyendoDeclaracion=False
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

    # # ---- WHILE ----
    # def enterIwhile(self, ctx):
    #     self.indent += 2
    #     print(" " * (self.indent - 2) + "[INFO]: Entrando a while")

    # def exitIwhile(self, ctx):
    #     self.indent -= 2
    #     print(" " * self.indent + "[INFO]: Saliendo de while")

    # =============================================================
    # MÉTODOS AUXILIARES
    # =============================================================
    def _verificarVariablesNoUsadasLocal(self):
        """
        Recorre el contexto actual y muestra advertencias para variables
        que fueron declaradas pero nunca usadas en ese ámbito.
        """
        contexto_actual = self.ts.contextos[-1]
        for nombre, var in contexto_actual.simbolos.items():
            if isinstance(var, Variable) and not var.getUsado():
                print(" " * self.indent + f"[ADVERTENCIA]: Variable '{nombre}' declarada pero no usada en contexto local")

    def _verificarExistenciaVariable(self, nombre):
        """
        Busca un símbolo en la TS. Si no existe y NO estamos en una declaración,
        lanza error de 'no declarada'.
        """
        simbolo = self.ts.buscarSimbolo(nombre)

        #si el símbolo NO existe y NO estamos leyendo una declaración
        if simbolo is None and not self.leyendoDeclaracion:
            self.registrarError("semantico", f"Variable '{nombre}' no reconocida o no declarada")
            return None

        return simbolo


    def registrarError(self, tipo, msj):
        """
        Registra un error semántico y marca el flag de errores.
        El error es impreso con el nivel de indentación actual.
        """
        self.huboErrores = True
        print(" " * self.indent + f"[ERROR {tipo.upper()}]: {msj}")