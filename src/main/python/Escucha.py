from compiladorParser import compiladorParser
from compiladorListener import compiladorListener
from TablaSimbolos import TablaSimbolos
from ID import Variable, Funcion


class Escucha(compiladorListener):
    """
    Clase que implementa el Listener para el análisis semántico.
    Se encarga de construir la Tabla de Símbolos y detectar errores de contexto,
    declaración, inicialización, uso y compatibilidad de tipos.
    También verifica consistencia entre funciones y prototipos
    """
    def __init__(self, escucha_sintactico=None):
        super().__init__()
        self.ts = TablaSimbolos()      #singleton de tabla de símbolos
        self.huboErrores = False       #flag para indicar si hubo errores semánticos
        self.indent = 0                #nivel de indentación para mensajes de consola
        self.errores = []              #lista de errores semánticos para el reporte final
        
        self.sintactico = escucha_sintactico #referencia al otro listener
        
        #variables para manejo de funciones
        self.argumentos_funcion_actual = []
        self.lectura_argumentos = False
        self.en_funcion = False       #para evitar la creacion de dobles contextos

        #bandera especial para manejar dependencias en declaraciones múltiples
        self.leyendoDeclaracion = False

        # Mantiene el contexto de la función actual mientras se analiza el cuerpo.
        # Esto permite validar el tipo del return contra la firma de la función.
        self.funcion_actual = None
        self.tipo_funcion_actual = None

        # Bandera para registrar si la función actual ya tuvo al menos un return.
        # Esto se usa para exigir que las funciones no void devuelvan algo.
        self.tiene_return_en_funcion = False

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

        self._verificarFuncionesNoUsadas()

        #para marcar main como usada
        for contexto in self.ts.historialCTX:
            for id in contexto.simbolos.values():
                if isinstance(id, Funcion) and id.nombre == "main":
                    id.setUsado()
                    break
        errores_sintacticos = False
        if self.sintactico and len(self.sintactico.errores) > 0:
            errores_sintacticos = True
            
        #imprime la tabla de símbolos final si no hubo errores
        if self.huboErrores or errores_sintacticos:
            print("[INFO]: No se puede generar tabla de símbolos debido a errores")
        else:
            print("[INFO]: Tabla de símbolos final:")
            self.ts.imprimirTS()
        print("[INFO]: Fin del parsing")
    
    def enterBloque(self, ctx):
        """Abre un nuevo contexto en la Tabla de Símbolos. Excepto que estemos en una funcion"""
        #if self.en_funcion:
        #    return
        self.ts.addContexto()

    def exitBloque(self, ctx):
        """Cierra el contexto actual y verifica variables no usadas localmente."""
        self._verificarVariablesNoUsadasLocal()
        #if self.en_funcion:
        #    return
        self.ts.delContexto()

    # =============================================================
    # GESTION DE VARIABLES (Declaracion, Asignacion, Uso)
    # =============================================================
    def enterDeclaracion(self, ctx: compiladorParser.DeclaracionContext):
        """
        Activa la bandera de lectura de declaración.
        Esto previene que se reporten errores de 'usado sin inicializar/declarar'
        para las variables que están siendo inicializadas por otras en la misma línea
        (ej: int a=1, b=a;).
        """
        self.leyendoDeclaracion = True

    def exitDeclaracion(self, ctx: compiladorParser.DeclaracionContext):
        """Procesa una línea de declaración (ej: int a=1, b=a;)."""
        tipo = ctx.tipo().getText()
        self._procesarDeclaraciones(tipo, ctx.ID(), ctx.inic(), ctx.listavar())
        self.leyendoDeclaracion = False

    def exitForInicializacion(self, ctx: compiladorParser.ForInicializacionContext):
        """Procesa declaraciones dentro del header de un for (ej: for(int i=0;...))."""
        if ctx.tipo() and ctx.ID():
            tipo = ctx.tipo().getText()
            self._procesarDeclaraciones(tipo, ctx.ID(), ctx.inic(), ctx.listavar())

    def _procesarDeclaraciones(self, tipo, primer_id, primer_inic, lista_var):
        """
        Método para procesar listas de variables tanto en exitDeclaracion como en exitForInicializacion.
        1. Recolecta todas las variables de la línea.
        2. Las inserta en la TS.
        3. Valida tipos de inicialización.
        """
        vars_list = []
        
        # 1. Agregar el primer elemento
        nombre0 = primer_id.getText()
        tiene_inic0 = (primer_inic is not None and primer_inic.getChildCount() > 0)
        vars_list.append((nombre0, tiene_inic0, primer_inic))

        # 2. Recolectar recursivamente el resto (listavar)
        def recolectar(lv, acc):
            if lv is None: return
            if lv.ID():
                inic_lv = lv.inic()
                tiene_inic = (inic_lv is not None and inic_lv.getChildCount() > 0)
                acc.append((lv.ID().getText(), tiene_inic, inic_lv))
            if hasattr(lv, "listavar"):
                recolectar(lv.listavar(), acc)

        recolectar(lista_var, vars_list)

        # 3. Insercion en Tabla de Símbolos
        for nombre, tiene_inic, _ in vars_list:
            if self.ts.buscarSimboloContexto(nombre):
                self.registrarError("semantico", f"'{nombre}' ya declarado en contexto actual")
            else:
                var = Variable(nombre, tipo)
                self.ts.addSimbolo(var)
                msg_inic = " (inicializada)" if tiene_inic else ""
                print(" " * self.indent + f"[INFO]: Variable '{nombre}' ({tipo}) agregada{msg_inic}")

        # 4. Validacion de Tipos (Inicialización)
        for nombre, tiene_inic, inic_ctx in vars_list:
            var = self.ts.buscarSimboloContexto(nombre)
            
            if var and tiene_inic:
                #extraer expresion de valor
                valor_ctx = None
                if hasattr(inic_ctx, "opal") and inic_ctx.opal():
                    valor_ctx = inic_ctx.opal()
                elif inic_ctx.getChildCount() > 0:
                    valor_ctx = inic_ctx.getChild(0)

                #evaluar tipo (desactivando flag para permitir uso de otras vars)
                prev_flag = self.leyendoDeclaracion
                self.leyendoDeclaracion = False
                try:
                    tipo_valor = self._tipoExp(valor_ctx)
                finally:
                    self.leyendoDeclaracion = prev_flag

                #chequeo de compatibilidad
                if tipo_valor and tipo != tipo_valor:
                    #float = int es valido
                    if not (tipo == "float" and tipo_valor == "int"):
                        self.registrarError("semantico", 
                            f"Inicialización incompatible: '{nombre}' es {tipo}, valor es {tipo_valor}")

                var.setInicializado(True)

    def exitAsignacion(self, ctx: compiladorParser.AsignacionContext):
        """Verifica que la variable destino exista y que la asignación sea compatible en tipos."""
        exp_asig_ctx = ctx.expASIG()
        if exp_asig_ctx is None:
            return
            
        #obtiene el nombre de la variable destino y la expresión a asignar
        nombre = exp_asig_ctx.ID().getText()
        valor_ctx = exp_asig_ctx.opal()
        
        #verifica que la variable exista y obtiene el simbolo
        simbolo = self._verificarExistenciaVariable(nombre)
        if simbolo is None:
            return
            
        #obtiene tipo de la variable destino y tipo de la expresión
        tipo_destino = simbolo.getTipoDato()
        tipo_valor = self._tipoExp(valor_ctx)
        
        #compara el tipo de la variable destino con el tipo de la expresión
        if tipo_valor and tipo_destino != tipo_valor:
            self.registrarError("semantico",f"Asignación incompatible: '{nombre}' es {tipo_destino} y se intenta asignar {tipo_valor}")
        
        #marca variable como inicializada y usada
        simbolo.setInicializado(True)
        simbolo.setUsado(True)
        print(" " * self.indent + f"[INFO]: Asignación realizada: '{nombre}' inicializado y usado")
    
    def exitFactor(self, ctx: compiladorParser.FactorContext):
        """
        Detecta el uso de variables dentro de expresiones (factores).
        Aquí se chequea si la variable fue usada sin inicializar.
        """
        if ctx.ID():
            nombre = ctx.ID().getText()
            if nombre in ("TRUE", "FALSE"):
                return

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
   
    def exitPrototipo(self, ctx):
        if not ctx.ID(): return
        
        tipo_retorno = ctx.tipo().getText() if ctx.tipo() else "void"
        nombre_funcion = ctx.ID().getText()
        
        #extraer los argumentos
        argumentos = []
        if ctx.prototipoparametros():
            argumentos = self.extraer_argumentos(ctx.prototipoparametros())
            
        #verificar si ya existe en la ts
        if not self.ts.buscarSimbolo(nombre_funcion):
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
    
    def enterFuncion(self, ctx: compiladorParser.FuncionContext):
        """Abre contexto de la funcion"""
        self.ts.addContexto()
        self.en_funcion = True
        self.argumentos_funcion_actual = []
        self.lectura_argumentos = True

        # En el enterFuncion NO es seguro leer ctx.ID() / ctx.tipo() porque el
        # contexto de la regla todavía está en fase de apertura y esos tokens
        # no quedan resueltos de forma estable para el listener. Por eso, para
        # validar el return, vamos a resolver la función desde el contexto
        # del ancestro cuando realmente llegue el nodo return.
        self.funcion_actual = None
        self.tipo_funcion_actual = None

        # Cada nueva función arranca con la bandera de return en False.
        # Si luego aparece un return, se marca en True y se valida al cierre.
        self.tiene_return_en_funcion = False
           
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
            
        # Al cerrar la función, verificamos si una función que no es void
        # realmente devolvió algo. Si no apareció ninguna sentencia return,
        # registramos un error semántico.
        if tipo_retorno and tipo_retorno != "void" and not self.tiene_return_en_funcion:
            self.registrarError(
                "semantico",
                f"La función '{nombre_funcion}' debe retornar un valor de tipo '{tipo_retorno}'"
            )

        #limpiar variables de función
        self.argumentos_funcion_actual = []
        self.lectura_argumentos = False

        # Cuando termina la función, volvemos al estado neutral para no mezclar
        # el tipo de retorno de una función con la siguiente.
        self.funcion_actual = None
        self.tipo_funcion_actual = None
        self.tiene_return_en_funcion = False
                
        self.en_funcion = False
        self.ts.delContexto()
        
    # ***********************
    # Parametros de funciones
    # ***********************
    def enterParametros(self, ctx: compiladorParser.ParametrosContext):
        self.lectura_argumentos = True
    def exitP(self, ctx: compiladorParser.PContext):
        """Procesa un parametro individual dentro de la definicion de la funcion"""
        if self.lectura_argumentos and ctx.tipo() and ctx.ID():
            tipo = ctx.tipo().getText()
            identificador = ctx.ID().getText()
            
            #agregar a la lista de argumentos
            argumento_dict = {'tipo': tipo, 'nombre': identificador}
            self.argumentos_funcion_actual.append(argumento_dict)
            
            #registrar como variable
            if not self.ts.buscarSimboloContexto(identificador):
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
    
    def _obtenerFuncionDesdeContexto(self, ctx):
        """
        Recorre el árbol ascendente para encontrar la función contenedora.
        En ANTLR4 para Python, el puntero del padre se expone como `parentCtx`.
        Esto permite detectar la función que contiene la sentencia return sin
        depender de otra estructura auxiliar.
        """
        nodo_actual = ctx
        while nodo_actual is not None:
            if isinstance(nodo_actual, compiladorParser.FuncionContext):
                nombre = nodo_actual.ID().getText() if nodo_actual.ID() else None
                tipo = nodo_actual.tipo().getText() if nodo_actual.tipo() else "void"
                return nombre, tipo
            nodo_actual = getattr(nodo_actual, 'parentCtx', None)

        return None, None

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

        # Validamos cantidad y tipos de argumentos contra la firma guardada de la función.
        argumentos_llamada = self.extraer_tipos_argumentos_llamada(ctx.argumento())
        if not self.verificar_argumentos_llamada(simbolo_funcion, argumentos_llamada):
            return
        
        #existe y es funcion
        simbolo_funcion.setUsado(True)
        print(f"[INFO]: Llamada de función '{nombre_funcion}' detectada.")

    def exitIreturn(self, ctx: compiladorParser.IreturnContext):
        """
        Valida el return de una función con su tipo de retorno.

        La regla de compatibilidad es simple:
        - si la función es void, el return no debe devolver una expresión
        - si la función devuelve algo, el return debe devolver ese mismo tipo
          o un tipo compatible por coerción (por ejemplo int -> float)
        """
        # Recorremos hacia arriba en el árbol hasta encontrar la función que
        # contiene esta sentencia return. Así evitamos depender de un contexto
        # que todavía no quedó estable en enterFuncion.
        self.funcion_actual, self.tipo_funcion_actual = self._obtenerFuncionDesdeContexto(ctx)

        # Si no estamos dentro de ninguna función, no hay nada que validar.
        if not self.funcion_actual or not self.tipo_funcion_actual:
            return

        # Si aparece un return dentro de la función actual, marcamos esa bandera.
        # Esto permite luego exigir que una función no void retorne algo al cierre.
        self.tiene_return_en_funcion = True

        # La gramática actual exige una expresión en return, pero dejamos el
        # chequeo robusto para cualquier caso en el que la expresión no exista.
        valor_ctx = ctx.opal() if ctx.opal() else None

        # Si la función es void, cualquier expresión en return es inválida.
        if self.tipo_funcion_actual == "void":
            if valor_ctx is not None:
                self.registrarError(
                    "semantico",
                    f"La función '{self.funcion_actual}' es void y no puede retornar un valor"
                )
            return

        # Si la función devuelve un tipo y el return no tiene valor, hay error.
        if valor_ctx is None:
            self.registrarError(
                "semantico",
                f"La función '{self.funcion_actual}' debe retornar un valor de tipo '{self.tipo_funcion_actual}'"
            )
            return

        tipo_valor = self._tipoExp(valor_ctx)
        if tipo_valor is None:
            self.registrarError(
                "semantico",
                f"No se pudo determinar el tipo de la expresión retornada en '{self.funcion_actual}'"
            )
            return

        # Permitimos coerción int -> float, igual que en otras verificaciones del
        # compilador, pero cualquier otro tipo distinto debe reportarse.
        if self.tipo_funcion_actual == tipo_valor:
            return

        if self.tipo_funcion_actual == "float" and tipo_valor == "int":
            return

        self.registrarError(
            "semantico",
            f"Return incompatible: la función '{self.funcion_actual}' devuelve '{self.tipo_funcion_actual}' pero se intenta retornar '{tipo_valor}'"
        )
    
    # =============================================================
    # CONTEXTOS DE BLOQUES (if, else, for, while)
    # =============================================================
    # Tanto para if, else y while, la gestion del contexto se hace en enter/exitBloque
        
    def enterIfor(self, ctx):
        # El contexto del for (para 'i') DEBE abrirse en enterIfor si la gramática no tiene un bloque.
        # Si la gramática es for (...) instruccion, el ámbito de 'i' está en la instrucción/bloque.
        # Para simplificar, asumimos que el contexto se abre en enterIfor para la inicialización.
        self.ts.addContexto() 

    def exitIfor(self, ctx):
        # Verifica las variables declaradas en el encabezado del for (como 'i')
        self._verificarVariablesNoUsadasLocal()
        self.ts.delContexto() # Cierra el contexto del for (donde se declaró 'i')

    # =============================================================
    # MÉTODOS AUXILIARES
    # =============================================================
    #aca juntamos metodos que utilizan los enter/exit que ayudan a que quede un poco mas prolijo el codigo
    def _tipoExp(self, ctx):
        """Función auxiliar para determinar el tipo de dato resultante de una expresión (recursiva)."""

        # Importante: las literales booleanas TRUE/FALSE deben seguir tratándose
        # como tokens reservados en el lexer. Si el lexer las devuelve como ID,
        # luego el análisis semántico las interpreta como variables y se pierde el
        # contexto correcto del tipo booleano.
        if ctx is None:
            return None

        texto = ctx.getText() if hasattr(ctx, 'getText') else None
        if texto in ("TRUE", "FALSE"):
            return "bool"
        
        #esto de aca está para arreglar el erro de que si tenemos
        #int x = 10, y = 20
        #bool z = x < y
        #marca error de que a un bool no se le puede asignar un int, pero al tener < el resultado
        #de la operacion deberia ser bool
        nombre_clase = ctx.__class__.__name__

        if "LlamadaContext" in nombre_clase:
            nombre_funcion = ctx.ID().getText()
            simbolo_funcion = self.ts.buscarSimbolo(nombre_funcion)
            if isinstance(simbolo_funcion, Funcion):
                return simbolo_funcion.getTipoDato()
            return None
        
        
        if "ExpORContext" in nombre_clase: #OR      expOR : expAND o ;
            #solo devolvemos bool si la parte derecha 'o' tiene contenido real
            if ctx.o() and ctx.o().getChildCount() > 0: return "bool"
        elif "ExpANDContext" in nombre_clase:
            if ctx.a() and ctx.a().getChildCount() > 0: return "bool"
        elif "ExpIGUALContext" in nombre_clase:
            if ctx.i() and ctx.i().getChildCount() > 0: return "bool"
        elif "ExpCOMPContext" in nombre_clase:
            if ctx.c() and ctx.c().getChildCount() > 0: return "bool"
        
        #Reglas para factores    
        #Numeros enteros y flotantes
        if hasattr(ctx, 'NUMERO') and ctx.NUMERO(): return "int" 
        if hasattr(ctx, 'DECIMAL') and ctx.DECIMAL(): return "float"
        #Booleanos literales
        if hasattr(ctx, 'TRUE') and ctx.TRUE(): return "bool"
        if hasattr(ctx, 'FALSE') and ctx.FALSE(): return "bool"

        # Nodo ID: Se usa una variable
        if hasattr(ctx, 'ID') and ctx.ID():
            nombre = ctx.ID().getText()
            if nombre in ("TRUE", "FALSE"):
                return "bool"

            var = self._verificarExistenciaVariable(nombre)
            if var is None:
                return None
            #si NO estamos leyendo una declaración, reportar error de 'no inicializado'
            if isinstance(var, Variable) and not self.leyendoDeclaracion:
                if not var.getInicializado():
                    self.registrarError("semantico", f"'{nombre}' usado sin inicializar")
            
            #la variable se marca como usada al ser parte de una expresión
            var.setUsado(True) 
            return var.getTipoDato()
        
        #si es un paréntesis, reiniciamos la evaluación en la expresión interna
        if hasattr(ctx, 'opal') and ctx.opal():
            return self._tipoExp(ctx.opal())
            
        #verifica tipos de los hijos de la expresión (operadores)
        tipos = set()
        for i in range(ctx.getChildCount()):
            child = ctx.getChild(i)
            #ignoramos tokens terminales que no aportan tipo (como +, -, *)
            if hasattr(child, 'getSymbol'): 
                continue
            #llamada recursiva a la expresión hija
            tipo_hijo = self._tipoExp(ctx.getChild(i))
            if tipo_hijo:
                tipos.add(tipo_hijo)
                
        #si todos los hijos son del mismo tipo devuelve ese tipo (Ej: int + int = int)
        if len(tipos) == 1:
            return tipos.pop()
        elif len(tipos) > 1:
            #tipos incompatibles en operación (Ej: int + float)
            if "float" in tipos and "int" in tipos and "bool" not in tipos:
                return "float"
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

    def _verificarFuncionesNoUsadas(self):
        """
        Recorre la tabla de símbolos y muestra advertencias para funciones
        declaradas pero nunca llamadas.
        """
        hay_advertencias_funciones = False
        for contexto in self.ts.contextos:
            for nombre, simbolo in contexto.simbolos.items():
                if isinstance(simbolo, Funcion) and not simbolo.getUsado() and nombre != "main":
                    if not hay_advertencias_funciones:
                        print("\n--- ADVERTENCIA ---")
                        hay_advertencias_funciones = True
                    print(" " * self.indent + f"[ADVERTENCIA]: Función '{nombre}' declarada pero no usada")

    def _verificarExistenciaVariable(self, nombre):
        """
        Busca un símbolo en la TS. Si no existe y NO estamos en una declaración,
        lanza error de 'no declarada'.
        """
        if nombre in ("TRUE", "FALSE"):
            return Variable(nombre, "bool", inicializado=True, declarado=True)

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
        mensaje = " " * self.indent + f"[ERROR {tipo.upper()}]: {msj}"

        if mensaje in self.errores:
            return

        self.huboErrores = True
        self.errores.append(mensaje)
        print(mensaje)
        
    def extraer_argumentos(self, ctx):
        """
        Convierte la estructura recursiva de parametros en una lista plana
        """
        args = []
        nodo_actual = ctx

        while nodo_actual:
            #CASO definicion (p)
            #gramatica: parametros: p COMA parametros | p | ;
            if hasattr(nodo_actual, 'p') and nodo_actual.p():
                tipo = nodo_actual.p().tipo().getText()
                nombre = nodo_actual.p().ID().getText()
                args.append({'tipo': tipo, 'nombre': nombre})
                nodo_actual = nodo_actual.parametros()#avanzamos recursivamente

            #CASO prototipo (tipo ID)
            #gramatica: prototipoparametros: tipo ID COMA prototipoparametros | tipo ID | ;
            elif hasattr(nodo_actual, 'tipo') and nodo_actual.tipo():
                tipo = nodo_actual.tipo().getText()
                nombre = nodo_actual.ID().getText()
                args.append({'tipo': tipo, 'nombre': nombre})
                nodo_actual = nodo_actual.prototipoparametros()#avanzamos recursivamente
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

    def extraer_tipos_argumentos_llamada(self, ctx):
        """
        Convierte la lista recursiva de argumentos de una llamada en sus tipos.
        """
        tipos = []
        if ctx is None or ctx.getChildCount() == 0:
            return tipos

        if ctx.opal():
            tipos.append(self._tipoExp(ctx.opal()))

        if ctx.argumento():
            tipos.extend(self.extraer_tipos_argumentos_llamada(ctx.argumento()))

        return tipos

    def verificar_argumentos_llamada(self, funcion, tipos_argumentos):
        """
        Verifica cantidad y tipos de argumentos de una llamada.

        La idea es reportar todos los problemas observables en la llamada en lugar
        de cortar la validación al primer conflicto. Así se obtiene un diagnóstico
        más completo para el usuario y el compilador no deja de chequeando el resto.
        """
        args_funcion = funcion.getListaArgs()
        hubo_error = False

        # Si la cantidad no coincide, registramos el problema principal y seguimos
        # revisando los argumentos que sí pudieron inferirse para reportar los
        # fallos de tipo que aún sean visibles.
        if len(args_funcion) != len(tipos_argumentos):
            self.registrarError(
                "semantico",
                f"La llamada a '{funcion.nombre}' recibe {len(tipos_argumentos)} argumento(s) pero esperaba {len(args_funcion)}"
            )
            hubo_error = True

        # Recorremos la firma de la función y, si hay un argumento presente en la
        # llamada, verificamos su tipo sin cancelar el análisis del resto.
        for indice, arg_funcion in enumerate(args_funcion, start=1):
            if indice > len(tipos_argumentos):
                break

            tipo_llamada = tipos_argumentos[indice - 1]
            if tipo_llamada is None:
                self.registrarError(
                    "semantico",
                    f"No se pudo determinar el tipo del argumento {indice} en la llamada a '{funcion.nombre}'"
                )
                hubo_error = True
                continue

            if arg_funcion['tipo'] != tipo_llamada:
                self.registrarError(
                    "semantico",
                    f"El argumento {indice} de '{funcion.nombre}' debe ser '{arg_funcion['tipo']}' y se recibió '{tipo_llamada}'"
                )
                hubo_error = True

        # El valor de retorno sigue siendo una señal de consistencia para que la
        # llamada no se marque como válida si hubo al menos un conflicto.
        return not hubo_error

    