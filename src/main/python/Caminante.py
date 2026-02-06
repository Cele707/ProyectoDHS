from compiladorVisitor import compiladorVisitor
from compiladorParser import compiladorParser
from TablaSimbolos import TablaSimbolos

# ===============================================
# METODOS AUXILIARES
# ===============================================

class Temporales:
    """ Se encarga de gestionar los nombres de variables temporales (t0, t1,..)
    """
    def __init__(self):
        self.counter = 0
        self.tipos = {} #mapea t ('t0', 'int')
    
    def next_temporal(self, tipo="int"):
        """Genera t0, t1,... y guarda su tipo"""
        temporal = f't{self.counter}'
        self.tipos[temporal] = tipo
        self.counter += 1
        return temporal

    def next_temporal_con_tipo(self, op1, op2, operacion):
        """Genera un temporal infiriendo el tipo basado en la operacion y los operandos
        Util para saber el tipo de resultado
        """
        tipo_resultado = "int" #por defecto
        #si es una operacion logica, es tipo bool
        if operacion in ['&&', '||', '==', '!=', '<', '>', '<=', '>=']:
            tipo_resultado = "bool"
        #si es una operacion aritmetica y si hay un . asumimos que es float
        elif '.' in str(op1) or '.' in str(op2):
            tipo_resultado= "float"
        
        return self.next_temporal(tipo_resultado)
    
    def get_tipo(self,temporal):
        """Obtener el tipo de un temporal"""
        return self.tipos.get(temporal, "int")
    
class Etiquetas:
    """Gerera las etiquetas L0, L1,.. para el control de flujo"""
    def __init__(self):
        self.counter = 0
        self.funciones = dict()
        
    def next_etiqueta(self):
        """Genera L0, L1,.. para whiles e ifs"""
        etiqueta = f'L{self.counter}'
        self.counter += 1
        return etiqueta
    
    def etiqueta_funcion(self, identificador: str):
        """Retorna el nombre de la funcion como etiqueta"""
        if identificador not in self.funciones:
            self.funciones[identificador] = identificador
            return identificador
        
class Caminante(compiladorVisitor):
    def __init__(self):
        self.ts = TablaSimbolos()#para acceso a tipo de funcion y de variable
        self.temps = Temporales()
        self.labels = Etiquetas()
        
        self.codigo = [] #buffer de salida
        
    def imprimirCodigo(self):
        """Imprime todo el codigo generado en la consola"""
        print("\n" + "="*30)
        print("   CÓDIGO INTERMEDIO GENERADO")
        print("="*30)
        
        for linea in self.codigo:
            print(linea)
        print("="*30 + "\n")
        
    # ====================================
    # UTILIDADES
    # ====================================
        
    def visitPrograma(self, ctx:compiladorParser.ProgramaContext):
        """Inicio y recorrido del arbol"""
        #visitamos todos los hijos
        self.visitChildren(ctx)
        
        #al terminar de recorrer todo el arbol, imprimimos el resultado
        if len(self.codigo) > 0:
            self.imprimirCodigo()
        else:
            print("[ADVERTENCIA]: No se generó codigo, programa vacio")
        
        return self.codigo
    # ======================================
    # DISPATCHER DE INSTRUCCIONES
    # ======================================
    def visitInstrucciones(self, ctx:compiladorParser.InstruccionesContext):
        """instrucciones : instruccion instrucciones"""
        #visitChildren recorre la lista automaticamente
        return self.visitChildren(ctx)
    def visitInstruccion(self, ctx: compiladorParser.InstruccionContext):
        """Decide que metodo llamar dependiendo lo que hay en la instrucción actual"""
        
        #tuve que agregar esto para los casos en los que INC y DEC estan solos sin asignacion
        #ej i++; en vez de x = i++;
        if ctx.INC():
            nombre = ctx.ID().getText()
            self.codigo.append(f"{nombre} = {nombre} + 1")
            return None
            
        elif ctx.DEC():
            nombre = ctx.ID().getText()
            self.codigo.append(f"{nombre} = {nombre} - 1")
            return None
        
        
        #verificamos que el hijo exista y visitamos ese nodo
        if ctx.asignacion():    return self.visit(ctx.asignacion())
        elif ctx.declaracion(): return self.visit(ctx.declaracion())
        elif ctx.iif():         return self.visit(ctx.iif())
        elif ctx.iwhile():      return self.visit(ctx.iwhile())
        elif ctx.ifor():        return self.visit(ctx.ifor())
        elif ctx.ireturn():     return self.visit(ctx.ireturn())
        elif ctx.bloque():      return self.visit(ctx.bloque())
        elif ctx.prototipo():   return self.visit(ctx.prototipo())
        elif ctx.funcion():     return self.visit(ctx.funcion())
        elif ctx.llamada():     return self.visit(ctx.llamada())
        return None
    
     # =====================================
    # CONTROL DE FLUJO
    # =====================================
    def visitBloque(self, ctx:compiladorParser.BloqueContext):
        #un bloque es una lista de instrucciones encerrada en {}
        return self.visitChildren(ctx)

    def visitIif(self, ctx: compiladorParser.IifContext):
        """
        Genera codigo para IF y IF-ELSE usando logica de salto si falso.
        Estructura:
           evaluar condicion
           ifnot condicion jmp L_FALSE
           bloque true
           jmp L_END
           label L_FALSE
           bloque else
           label L_END
        """
        condicion = self.visit(ctx.opal())
        etiqueta_false = self.labels.next_etiqueta()
        
        #buscamos si el hijo ielse tiene el token ELSE dentro
        nodo_else = ctx.ielse()
        tiene_else = nodo_else.ELSE() is not None
        
        if tiene_else:
            etiqueta_salida = self.labels.next_etiqueta()
        
            self.codigo.append(f"ifnot {condicion} jmp {etiqueta_false}")
            self.visit(ctx.instruccion())# bloque true
            self.codigo.append(f"jmp {etiqueta_salida}") #salto a la salida
            
            #aca comienza el else
            self.codigo.append(f"label {etiqueta_false}")
            self.visit(nodo_else.instruccion())#bloque FALSE
            self.codigo.append(f"label {etiqueta_salida}")#fin el if
            
        else:
            #caso solo if, sin else
            self.codigo.append(f"ifnot {condicion} jmp {etiqueta_false}")
            self.visit(ctx.instruccion()) #bloque true
            self.codigo.append(f"label {etiqueta_false}")
            
        return None
    
    def visitIwhile(self, ctx: compiladorParser.IwhileContext):
        """Genera codigo para while"""
        #debe generar una etiqueta de inicio para hacer el ciclo
        label_inicio = self.labels.next_etiqueta()
        label_fin = self.labels.next_etiqueta()
        
        self.codigo.append(f"label {label_inicio}")#punto de retorno
        
        condicion = self.visit(ctx.opal())
        self.codigo.append(f"ifnot {condicion} jmp {label_fin}")#salida
        
        self.visit(ctx.instruccion())#cuerpo del ciclo
        
        self.codigo.append(f"jmp {label_inicio}")#vueltta al inicio
        self.codigo.append(f"label {label_fin}")#salida
        return None

    def visitIfor(self, ctx: compiladorParser.IforContext):
        """Genera codigo para for"""
        # for (init; cond; iter) instruccion
        
        self.visit(ctx.forInicializacion()) #parte de inicializacion, puede ser declaracion o asignacion
        
        label_inicio = self.labels.next_etiqueta()
        label_fin = self.labels.next_etiqueta()
        
        self.codigo.append(f"label {label_inicio}")
        
        if ctx.forCond(): #condicion
            condicion = self.visit(ctx.forCond())
            self.codigo.append(f"ifnot {condicion} jmp {label_fin}")
            
        self.visit(ctx.instruccion()) #cuerpo
        
        if ctx.forActualizacion(): #iteracion
            self.visit(ctx.forActualizacion())
            
        self.codigo.append(f"jmp {label_inicio}")
        self.codigo.append(f"label {label_fin}")
        return None
    
    def visitForInicializacion(self, ctx: compiladorParser.ForInicializacionContext):
        """
        Maneja la inicializacion del for
        1. declaraciones: tipo ID inic listavar           ej: int i=0, k=10)
        2. asignaciones: expASIG listaExpASIG             ej: i=0, k=10)
        """
        # CASO 1: declaracion 
        if ctx.tipo():
            #procesamos la primera variable
            if ctx.inic() and ctx.inic().getChildCount() > 0:
                nombre = ctx.ID().getText()
                val = self.visit(ctx.inic().opal())
                self.codigo.append(f"{nombre} = {val}")
            
            #procesamos el resto de la lista
            if ctx.listavar():
                self.visit(ctx.listavar())

        # CASO 2: asignaciones de variables existentes
        elif ctx.expASIG():
            self.visit(ctx.expASIG()) #primera asignación
            
            #resto de asignaciones
            if ctx.listaExpASIG():
                self.visit(ctx.listaExpASIG())
                
        return None

    def visitListavar(self, ctx: compiladorParser.ListavarContext):
        """
        Maneja la recursividad de variables en una declaracion, ej int x = 5, z = 6...
        """
        #si tiene hijos, procesamos
        if ctx.getChildCount() > 0:
            nombre = ctx.ID().getText()
            
            #si hay inicializacion
            if ctx.inic() and ctx.inic().getChildCount() > 0:
                val = self.visit(ctx.inic().opal())
                self.codigo.append(f"{nombre} = {val}")
            
            #recusrividad para visitar los siguientes nodos
            if ctx.listavar():
                self.visit(ctx.listavar())
        return None

    def visitListaExpASIG(self, ctx: compiladorParser.ListaExpASIGContext):
        """
        Maneja la recursividad de variables en variables ya definidas, ej for (i = 5, z = 6,..)
        """
        if ctx.expASIG():
            self.visit(ctx.expASIG())
            
            # Recursividad
            if ctx.listaExpASIG():
                self.visit(ctx.listaExpASIG())
        return None
    # ===============================================
    # FUNCIONES
    # ===============================================

    def visitFuncion(self, ctx: compiladorParser.FuncionContext):
        """Genera la etiqueta de entrada de la funcion y procesa su contenido"""
        nombre = ctx.ID().getText()
        self.codigo.append(f"\nlabel {nombre}")
        self.visit(ctx.bloque()) #cuerpo
        return None

    def visitIreturn(self, ctx: compiladorParser.IreturnContext):
        """Maneja el retorno de valores"""
        # return expresion;
        if ctx.opal():
            valor = self.visit(ctx.opal())
            self.codigo.append(f"return {valor}")
        else:
            self.codigo.append("return")
        return None
    
    #Nota: visitPrototipo no es necesario porque los prototipos no generan codigos ejecutables
    def visitLlamada(self, ctx: compiladorParser.LlamadaContext):
        """Maneja la invocacion de funciones
            1. Prepara los argumentos (param x)
            2. Verifica en la TS si retorna valor
            3. Genera call o t0 = call segun corresponda
        """
        nombre_func = ctx.ID().getText()
        #recopilación de argumentos
        args = []
        if ctx.argumento():
            self.recopilarArgumentos(ctx.argumento(), args)
            
        #generar params
        for arg in args:
            self.codigo.append(f"param {arg}")
            
        #buscar el tipo de retorno en la ts
        simbolo = self.ts.buscarSimbolo(nombre_func)
        tipo_retorno = simbolo.tipoDato if simbolo else "int"

        #generar el call
        #si la funcion es VOID, no generamos "t1 = call", solo "call" porque generaria un temporal sin sentido
        if tipo_retorno == "void":
            self.codigo.append(f"call {nombre_func}, {len(args)}")
            return None
        else:
            #si retorna algun tipo aparte pedimos un temporal de ese tipo
            temp = self.temps.next_temporal(tipo_retorno)
            self.codigo.append(f"{temp} = call {nombre_func}, {len(args)}")
            return temp

    def recopilarArgumentos(self, ctx, lista):
        """Funcion auxiliar para desenrollar la lista recursiva de argumentos"""
        #argumento : opal | opal COMA argumento
        if ctx.opal():
            val = self.visit(ctx.opal())
            lista.append(val)
        if ctx.argumento():
            self.recopilarArgumentos(ctx.argumento(), lista)
    
    # ===========================================
    # EXPRESIONES Y ASIGNACIONES
    # ===========================================
    def visitDeclaracion(self, ctx: compiladorParser.DeclaracionContext):
        # 1. Primera variable
        #verificamos si tiene inicializacio
        if ctx.inic() and ctx.inic().getChildCount() > 0:
            nombre = ctx.ID().getText()
            #visitamos opal para obtener el valor o temporal
            val = self.visit(ctx.inic().opal())
            self.codigo.append(f"{nombre} = {val}")

        # 2. Resto de variables en la misma linea
        #aprovechamos que ya implementamos visitListavar para el FOR
        if ctx.listavar():
            self.visit(ctx.listavar())
            
        return None
    def visitAsignacion(self, ctx:compiladorParser.AsignacionContext):
        #asignacion solo es un "envoltorio" de expASIG que le agrega PYC
        return self.visit(ctx.expASIG())

    def visitExpASIG(self, ctx: compiladorParser.ExpASIGContext):
        """Maneja asignaciones tanto aritmeticas como logicas.
           Resuelve toda la expresion derecha antes de asignar
        """
        nombre_variable = ctx.ID().getText()
        resultado = self.visit(ctx.opal()) #calcula el valor, visitOpal se encarga de devolver lo necesario
        self.codigo.append(f"{nombre_variable} = {resultado}")
        return nombre_variable
    
    # *********************
    # CADENA DE PRECEDENCIA en las expresiones
    # *********************
    def visitOpal(self, ctx: compiladorParser.OpalContext):
        """Entrada a expresiones logicas"""
        # opal solo envuelve a expOR
        return self.visit(ctx.expOR())

    #OR
    def visitExpOR(self, ctx: compiladorParser.ExpORContext):
        left = self.visit(ctx.expAND())
        if ctx.o():
            return self.visitO(ctx.o(), left)
        return left

    def visitO(self, ctx: compiladorParser.OContext, left=None):
        #si no hay más OR, devolvemos lo que traemos
        if ctx.getChildCount() == 0:
            return left
        # o : OR expAND o
        if ctx.OR():
            right = self.visit(ctx.expAND())
            temp = self.temps.next_temporal_con_tipo(left, right, '||')
            self.codigo.append(f'{temp} = {left} || {right}')
            #recursividad por la derecha
            if ctx.o():
                return self.visitO(ctx.o(), temp)
            return temp
        return left

    #AND
    def visitExpAND(self, ctx: compiladorParser.ExpANDContext):
        left = self.visit(ctx.expIGUAL())
        if ctx.a():
            return self.visitA(ctx.a(), left)
        return left

    def visitA(self, ctx: compiladorParser.AContext, left=None):
        if ctx.getChildCount() == 0:
            return left
        # a : AND expIGUAL a
        if ctx.AND():
            right = self.visit(ctx.expIGUAL())
            temp = self.temps.next_temporal_con_tipo(left, right, '&&')
            self.codigo.append(f'{temp} = {left} && {right}')
            
            if ctx.a():
                return self.visitA(ctx.a(), temp)
            return temp
        return left

    # IGUALDAD
    def visitExpIGUAL(self, ctx: compiladorParser.ExpIGUALContext):
        left = self.visit(ctx.expCOMP())
        if ctx.i():
            return self.visitI(ctx.i(), left)
        return left

    def visitI(self, ctx: compiladorParser.IContext, left=None):
        if ctx.getChildCount() == 0:
            return left
        op = None
        if ctx.IGUAL(): op = '=='
        elif ctx.DISTINTO(): op = '!='
        if op:
            right = self.visit(ctx.expCOMP())
            temp = self.temps.next_temporal_con_tipo(left, right, op)
            self.codigo.append(f'{temp} = {left} {op} {right}')
            if ctx.i():
                return self.visitI(ctx.i(), temp)
            return temp
        return left

    #COMPARACIÓN
    def visitExpCOMP(self, ctx: compiladorParser.ExpCOMPContext):
        left = self.visit(ctx.exp())
        if ctx.c():
            return self.visitC(ctx.c(), left)
        return left

    def visitC(self, ctx: compiladorParser.CContext, left=None):
        if ctx.getChildCount() == 0:
            return left
        op = None
        if ctx.MENOR(): op = '<'
        elif ctx.MAYOR(): op = '>'
        elif ctx.MENORIG(): op = '<='
        elif ctx.MAYORIG(): op = '>='
        if op:
            right = self.visit(ctx.exp()) #llamamos a exp()
            temp = self.temps.next_temporal_con_tipo(left, right, op)
            self.codigo.append(f'{temp} = {left} {op} {right}')
            
            if ctx.c():
                return self.visitC(ctx.c(), temp)
            return temp
        return left
    #ARITMETICA (Suma y Resta)
    def visitExp(self, ctx: compiladorParser.ExpContext):
        left = self.visit(ctx.term()) #obtener el primer termino

        #si hay operaciones siguientes visitE se encarga
        if ctx.e():
            return self.visitE(ctx.e(), left)
        #si no, devolvemos el valor limpio
        return left

    def visitE(self, ctx: compiladorParser.EContext, left=None):
        if ctx.getChildCount() == 0:
            return left
        op = None
        if ctx.SUMA(): op = '+'
        elif ctx.RESTA(): op = '-'

        if op:
            right = self.visit(ctx.term()) #obtener derecha
            temp = self.temps.next_temporal_con_tipo(left, right, op) #generar temporal
            self.codigo.append(f'{temp} = {left} {op} {right}')
            #recursividad (por si hay 5 + 5 + 5)
            if ctx.e():
                return self.visitE(ctx.e(), temp)
            
            return temp
        return left

    # TERMINOS (Multiplicación, División, Mod)
    def visitTerm(self, ctx: compiladorParser.TermContext):
        left = self.visit(ctx.factor())
        if ctx.t():
            return self.visitT(ctx.t(), left)
        return left

    def visitT(self, ctx: compiladorParser.TContext, left=None):
        if ctx.getChildCount() == 0:
            return left
        op = None
        if ctx.MULT(): op = '*'
        elif ctx.DIV(): op = '/'
        elif ctx.MOD(): op = '%'
        if op:
            right = self.visit(ctx.factor())
            temp = self.temps.next_temporal_con_tipo(left, right, op)
            self.codigo.append(f'{temp} = {left} {op} {right}')
            if ctx.t():
                return self.visitT(ctx.t(), temp)
            return temp
        return left

    #FACTOR (Números, Variables, Parentesis, Llamada)
    def visitFactor(self, ctx: compiladorParser.FactorContext):
        #Numeross y literales
        if ctx.NUMERO(): return ctx.NUMERO().getText()
        elif ctx.DECIMAL(): return ctx.DECIMAL().getText()
        elif ctx.TRUE(): return 'true'
        elif ctx.FALSE(): return 'false'
        
        #Variables
        elif ctx.ID(): return ctx.ID().getText()
            
        #Expresiones entre parentesis
        elif ctx.PA():
            #volvemos a empezar la jerarquía desde arriba (opal)
            return self.visit(ctx.opal())
            
        #Llamadas a función y = suma(a,b)
        elif ctx.llamada():
            return self.visit(ctx.llamada())

        #NOT
        elif ctx.NOT():
            val = self.visit(ctx.factor())
            temp = self.temps.next_temporal("bool")
            self.codigo.append(f'{temp} = !{val}')
            return temp
        #INC
        elif ctx.INC():
            #hay que determinar si es prefijo (++x) o posfijo (x++)
            es_prefijo = ctx.getChild(0).getText() == "++"
            nombre_var = self.visit(ctx.factor())
            if es_prefijo:
                self.codigo.append(f"{nombre_var} = {nombre_var} + 1")
                return nombre_var
            else:#es posfijo
                temp = self.temps.next_temporal("int")
                self.codigo.append(f"{temp} = {nombre_var}")
                self.codigo.append(f"{nombre_var} = {nombre_var} + 1")
                return temp
        #DEC
        elif ctx.DEC(): #funciona igual que INC
            es_prefijo = ctx.getChild(0).getText() == "--"
            nombre_var = self.visit(ctx.factor())
            if es_prefijo:
                self.codigo.append(f"{nombre_var} = {nombre_var} - 1")
                return nombre_var
            else:
                temp = self.temps.next_temporal("int")
                self.codigo.append(f"{temp} = {nombre_var}")
                self.codigo.append(f"{nombre_var} = {nombre_var} - 1")
                return temp
            
        return None
    