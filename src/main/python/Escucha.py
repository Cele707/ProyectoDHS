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
        
        #variables para manejo de funciones
        self.argumentos_funcion_actual = []
        self.lectura_argumentos = False
        self.en_funcion = False       #para evitar la creacion de dobles contextos

        #bandera especial para manejar dependencias en declaraciones múltiples
        self.leyendoDeclaracion = False

    # =============================================================
    # 1. PROGRAMA PRINCIPAL Y BLOQUES
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

        #para marcar main como usada
        for contexto in self.ts.historialCTX:
            for id in contexto.simbolos.values():
                if isinstance(id, Funcion) and id.nombre == "main":
                    id.setUsado()
                    break

        #imprime la tabla de símbolos final si no hubo errores
        if self.huboErrores:
            print("[INFO]: No se puede generar tabla de símbolos debido a errores")
        else:
            print("[INFO]: Tabla de símbolos final:")
            self.ts.imprimirTS()
        print("[INFO]: Fin del parsing")
    
    def enterBloque(self, ctx):
        """Abre un nuevo contexto en la Tabla de Símbolos."""
        #solo creamos contexto si no estamos en funcion, porque funcion crea su propio contexto
        if self.en_funcion:
            return
        self.ts.addContexto()
        #self.indent += 2
        #print(" " * (self.indent - 2) + "[INFO]: Entrando a bloque")

    def exitBloque(self, ctx):
        """Cierra el contexto actual y verifica variables no usadas localmente."""
        self._verificarVariablesNoUsadasLocal()
        if self.en_funcion:
            return
        self.ts.delContexto()
        #print(" " * (self.indent - 2) + "[INFO]: Saliendo de bloque")
        #self.indent -= 2

    # =============================================================
    # GESTION DE VARIABLES (Declaracion, Asignacion, Uso)
    # =============================================================
    # *************
    # Declaraciones
    # *************
    def enterDeclaracion(self, ctx: compiladorParser.DeclaracionContext):
        """
        Activa la bandera de lectura de declaración.
        Esto previene que se reporten errores de 'usado sin inicializar/declarar'
        para las variables que están siendo inicializadas por otras en la misma línea
        (ej: int a=1, b=a;).
        """
        self.leyendoDeclaracion = True

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

    # ************
    # Asignaciones
    # ************
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

    # *******************************
    # Uso de Variables en Expresiones
    # *******************************
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
    # GESTION DE FUNCIONES (Prototipo, Declaracion,Parametros, Llamada)
    # =============================================================
    
    # *********
    # Prototipo
    # *********
    def exitPrototipo(self, ctx):
        if not ctx.ID(): return
        
        tipo_retorno = ctx.tipo().getText() if ctx.tipo() else "void"
        nombre_funcion = ctx.ID().getText()
        
        # 1. Extraer los argumentos que hay en el prototipo de la funcion
        argumentos = []
        if ctx.prototipoparametros():
            argumentos = self.extraer_argumentos(ctx.prototipoparametros())
            
        # 2. Verificar si ya existe en la tabla de simbolos
        simbolo_existente = self.ts.buscarSimbolo(nombre_funcion)
    
        if simbolo_existente is None:
            #si no existe, lo creamos
            nueva_funcion = Funcion(nombre_funcion, tipo_retorno)

            nueva_funcion.prototipado = True
            nueva_funcion.setArgs(argumentos) #se cargan los argumentos extraidos
            self.ts.addSimbolo(nueva_funcion) #se agrega a la tabla
    
            #formateamos la lista para que se vea como "(int a, int b)"
            args_str = "(" + ", ".join(f"{arg['tipo']} {arg['nombre']}" for arg in argumentos) + ")"
            
            #impresion para verificar que si se definió el prototipo
            print(" " * self.indent + f"[INFO]: Prototipo definido: {tipo_retorno} {nombre_funcion} {args_str};")

        else:
            #si ya existe, se marca como error
            self.registrarError("semantico", f"'{nombre_funcion}' ya declarada en contexto actual")

    # ************************
    # Declaracion de funciones
    # ************************
    
    def enterFuncion(self, ctx: compiladorParser.FuncionContext):
        self.ts.addContexto()
        self.en_funcion = True
        
        #inicializar variables de funcion
        self.argumentos_funcion_actual = []
        self.lectura_argumentos = True
           
    def exitFuncion(self, ctx: compiladorParser.FuncionContext):
        #obtener informacion de la funcion
        if ctx.ID():
            nombre_funcion = ctx.ID().getText()
        else:
            nombre_funcion = "None"

        if ctx.tipo():
            tipo_retorno = ctx.tipo().getText()
        else:
            tipo_retorno = ""
        #procesar argumentos extraidos
        if ctx.parametros():
            self.argumentos_funcion_actual = self.extraer_argumentos(ctx.parametros())
        
        #buscamos si la funcion ya existia en la tabla (el prototipo)
        funcion_previa = self.ts.buscarSimbolo(nombre_funcion)
        
        if funcion_previa and isinstance(funcion_previa, Funcion):
            #Caso A: existe el prototipo y no ha sido implementada
            if funcion_previa.prototipado and not funcion_previa.inicializado:
                #verificar que los argumentos del prototipo y de la funcion coincidan
                if not self.verificar_correspondencia_parametros(funcion_previa.args, self.argumentos_funcion_actual):
                    self.registrarError("semantico", f"La definición de '{nombre_funcion}' no coincide con su prototipo")
                else:
                    funcion_previa.inicializado = True
                    funcion_previa.setArgs(self.argumentos_funcion_actual)
                    print(f"[INFO]: Definición de función '{nombre_funcion}' completada.")
            
            elif funcion_previa.inicializado:
                #Caso B: ya estaba inicializada (error de redefinicion)
                self.registrarError("semantico", f"'{nombre_funcion}' ya fue definida previamente")
        else: 
            #Caso C: No existia el prototipo (es una funcion nueva sin prototipo, puede pasar)
            nueva_funcion = Funcion(
                nombre_funcion,
                tipo_retorno,
                inicializado=True,
                usado=False,
                declarado=True,
                args=self.argumentos_funcion_actual
            )
            if len(self.ts.contextos) > 1:
                self.ts.contextos[-2].addSimbolo(nueva_funcion)
            else:
                self.ts.addSimbolo(nueva_funcion)    
            print(f"[INFO]: Función '{nombre_funcion}' creada y guardada.")
            
        #limpiar variables de función
        self.argumentos_funcion_actual = []
        self.lectura_argumentos = False
                
        self.en_funcion = False
        self.ts.delContexto()
        
    # ***********************
    # Parametros de funciones
    # ***********************
    def enterParametros(self, ctx: compiladorParser.ParametrosContext):
        self.lectura_argumentos = True
    def exitP(self, ctx: compiladorParser.PContext):
        #para procesar cada parametro individual
        if self.lectura_argumentos and ctx.tipo() and ctx.ID():
            tipo = ctx.tipo().getText()
            identificador = ctx.ID().getText()
            
            #agregar a la lista de argumentos
            argumento_dict = {'tipo': tipo, 'nombre': identificador}
            self.argumentos_funcion_actual.append(argumento_dict)
            
            #registrar como variable
            if self.ts.buscarSimboloContexto(identificador) is None:
                #creamos el objeto Variable
                var_arg = Variable(identificador, tipo, inicializado=True, declarado=True)
                self.ts.addSimbolo(var_arg) 

                print(f"[INFO]: Argumento '{identificador}' registrado en contexto local")
            else:
                self.registrarError("semantico", f"El argumento '{identificador}' ya existe en el contexto")
                pass
    def exitParametros(self, ctx: compiladorParser.ParametrosContext):
        self.lectura_argumentos = False
        if self.ts.contextos:
            contexto_actual = self.ts.contextos[-1]
    
    # *******
    # Llamada
    # *******
    def exitLlamada(self, ctx: compiladorParser.LlamadaContext):
        nombre_funcion = ctx.ID().getText()
        simbolo_funcion = self.ts.buscarSimbolo(nombre_funcion)
        
        #verificar existencia
        if not simbolo_funcion:
            self.registrarError("semantico", f"La funcion '{nombre_funcion}' no ha sido declarada")
            return
        
        #si existe, verificar que sea una funcion y no una variable con el mismo nombre
        if not isinstance(simbolo_funcion, Funcion):
            self.registrarError("semantico", f"'{nombre_funcion}' se está llamando como funcion pero es una variable")
            return
        
        #existe y es funcion
        simbolo_funcion.setUsado(True)
        print(f"[INFO]: Llamada de función '{nombre_funcion}' detectada.")
    
    # =============================================================
    # CONTEXTOS DE BLOQUES (if, else, for, while)
    # =============================================================
    # Tanto para if, else y while, la gestion del contexto se hace en enter/exitBloque
        
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

    # =============================================================
    # MÉTODOS AUXILIARES
    # =============================================================
    #aca juntamos metodos que utilizan los enter/exit que ayudan a que quede un poco mas prolijo el codigo
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
        
    def extraer_argumentos(self, ctx):
        """
        Recorre recursivamente la estructura de listaParametros o prototipoparametros
        y devuelve una lista de diccionarios [{'tipo': 'int', 'nombre': 'a'}, ...]
        """
        args = []
        nodo_actual = ctx

        while nodo_actual:
            # --- CASO 1: Definición de Función (usa la regla 'p') ---
            #gramatica: parametros: p COMA parametros | p | ;
            if hasattr(nodo_actual, 'p') and nodo_actual.p():
                tipo = nodo_actual.p().tipo().getText()
                nombre = nodo_actual.p().ID().getText()
                args.append({'tipo': tipo, 'nombre': nombre})
                
                #avanzamos recursivamente
                nodo_actual = nodo_actual.parametros()

            # --- CASO 2: Prototipo (usa tipo ID directamente) ---
            #gramatica: prototipoparametros: tipo ID COMA prototipoparametros | tipo ID | ;
            elif hasattr(nodo_actual, 'tipo') and nodo_actual.tipo():
                tipo = nodo_actual.tipo().getText()
                nombre = nodo_actual.ID().getText()
                args.append({'tipo': tipo, 'nombre': nombre})
                
                #avanzamos recursivamente
                nodo_actual = nodo_actual.prototipoparametros()
            
            # --- CASO 3: Fin de la recursión (cadena vacía) ---
            else:
                nodo_actual = None
        return args
    
    def verificar_correspondencia_parametros(self, args_prototipo, args_definicion):
        """
        Funcion para comparar los parametros escritos en el prototipo con los parametros
        que se encuentran en la definicion de la funcion.
        """
        # 1. Verificar cantidad de argumentos
        if len(args_prototipo) != len(args_definicion):
            return False
            
        # 2. Verificar tipos ordenadamente
        for arg_proto, arg_def in zip(args_prototipo, args_definicion):
            tipo_proto = arg_proto['tipo']
            tipo_def = arg_def['tipo']
            if tipo_proto != tipo_def:
                return False
          
        return True

    