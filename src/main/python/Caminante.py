from compiladorVisitor import compiladorVisitor
from compiladorParser import compiladorParser

# ===============================================
# METODOS AUXILIARES
# ===============================================

class Temporales:
    def __init__(self):
        self.counter = 0
        self.tipos = {} #diccionario para recordar el tipo de cada temporal
    
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
        #1. Operaciones logicas siempre dan bool
        if operacion in ['&&', '||', '==', '!=', '<', '>', '<=', '>=']:
            tipo_resultado = "bool"
        #2. Operaciones aritmeticas, si hay un . asumimos que es float
        elif '.' in str(op1) or '.' in str(op2):
            tipo_resultado= "float"
        
        return self.next_temporal(tipo_resultado)
    
    def get_tipo(self,temporal):
        """Obtener el tipo de un temporal"""
        return self.tipos.get(temporal, "int")
    
class Etiquetas:
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
        self.temps = Temporales()
        self.lables = Etiquetas()
        
        self.codigo = []
        
        self.inFuncion = False
        self.indent_level = 0
        
    def imprimirCodigo(self):
        """Imprime todo el codigo generado en la consola"""
        print("\n" + "="*30)
        print("   CÓDIGO INTERMEDIO GENERADO")
        print("="*30)
        
        for linea in self.codigo:
            print(linea)
        print("="*30 + "\n")
        
    # ====================================
    # UTILIDADES Y PUNTO DE ENTRADA
    # ====================================
    def separateBlock(self):
        """Agrega un separador visual en la lista de codigo"""
        self.codigo.append("")#agrega una linea vacia
        
    def visitPrograma(self, ctx:compiladorParser.ProgramaContext):
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
        #instrucciones -> instruccion instrucciones
        #visitChildren recorre la lista automaticamente
        return self.visitChildren(ctx)
    def visitInstruccion(self, ctx: compiladorParser.InstruccionContext):
        #verificamos que el hijo exista y visitamos ese nodo
        if ctx.asignacion():
            return self.visit(ctx.asignacion())
        elif ctx.declaracion():
            return self.visit(ctx.declaracion())
        elif ctx.iif():
            return self.visit(ctx.iif())
        elif ctx.iwhile():
            return self.visit(ctx.iwhile())
        elif ctx.ifor():
            return self.visit(ctx.ifor())
        elif ctx.ireturn():
            return self.visit(ctx.ireturn())
        elif ctx.bloque():
            return self.visit(ctx.bloque())
        elif ctx.prototipo():
            return self.visit(ctx.prototipo())
        elif ctx.funcion():
            return self.visit(ctx.funcion())
        elif ctx.llamada():
            return self.visit(ctx.llamada())
        return None
    
    # ===========================================
    # ASIGNACIONES
    # ===========================================
    def visitAsignacion(self, ctx:compiladorParser.AsignacionContext):
        #asignacion solo es un 'envoltorio' de expASIG que le agrega PYC
        return self.visit(ctx.expASIG())
    def visitExpASIG(self, ctx: compiladorParser.ExpASIGContext):
        """Maneja asignaciones tanto aritmeticas como logicas"""
        nombre_variable = ctx.ID().getText()
        #resolvemos el valor de la derecha
        #visitOpal se encarga de devolver lo necesario
        resultado = self.visit(ctx.opal())
        
        #generacion de la instruccion de asignacion
        self.codigo.append(f"{nombre_variable} = {resultado}")
        return nombre_variable
    
    # ============================================
    # EXPRESIONES con orden de precedencia
    # ============================================
    # *************
    # NIVEL 1: OPAL
    # *************
    def visitOpal(self, ctx: compiladorParser.OpalContext):
        # opal solo envuelve a expOR
        return self.visit(ctx.expOR())

    # ************
    # NIVEL 2: OR
    # ***********
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

    # ************
    # NIVEL 3: AND
    # ************
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

    # *****************
    # NIVEL 4: IGUALDAD
    # *****************
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

    # ********************
    # NIVEL 5: COMPARACIÓN
    # ********************
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
    # ********************
    # NIVEL 6: EXPRESIONES (Suma y Resta)
    # ********************
    def visitExp(self, ctx: compiladorParser.ExpContext):
        # 1. Obtener el primer término (la izquierda)
        left = self.visit(ctx.term())

        # 2. Si hay operaciones siguientes (+ ...), visitE se encarga
        if ctx.e():
            return self.visitE(ctx.e(), left)
        
        # 3. Si no, devolvemos el valor limpio
        return left

    def visitE(self, ctx: compiladorParser.EContext, left=None):
        # Caso base: no hay más operaciones
        if ctx.getChildCount() == 0:
            return left

        # 1. Identificar operación
        op = None
        if ctx.SUMA(): op = '+'
        elif ctx.RESTA(): op = '-'

        if op:
            # 2. Obtener derecha
            right = self.visit(ctx.term())
            
            # 3. Generar temporal
            temp = self.temps.next_temporal_con_tipo(left, right, op)
            self.codigo.append(f'{temp} = {left} {op} {right}')
            
            # 4. Recursividad (por si hay 5 + 5 + 5)
            if ctx.e():
                return self.visitE(ctx.e(), temp)
            
            return temp
        return left

    # *****************
    # NIVEL 7: TÉRMINOS (Multiplicación, División, Mod)
    # *****************
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

    # ***************
    # NIVEL 8: FACTOR
    # ***************
    def visitFactor(self, ctx: compiladorParser.FactorContext):
        # 1. Números y Literales
        if ctx.NUMERO():
            return ctx.NUMERO().getText()
        elif ctx.DECIMAL():
            return ctx.DECIMAL().getText()
        elif ctx.TRUE():
            return 'true'
        elif ctx.FALSE():
            return 'false'
        
        # 2. Variables
        elif ctx.ID():
            return ctx.ID().getText()
            
        # 3. Expresiones entre paréntesis: ( 5 + 5 )
        elif ctx.PA():
            #volvemos a empezar la jerarquía desde arriba (opal)
            return self.visit(ctx.opal())
            
        # 4. Llamadas a función
        elif ctx.llamada():
            #IMPLEMENTAR VISITLLAMADA
            return self.visit(ctx.llamada())

        # 5. NOT
        elif ctx.NOT():
            val = self.visit(ctx.factor())
            temp = self.temps.next_temporal("bool")
            self.codigo.append(f'{temp} = !{val}')
            return temp

        #IMPLEMENTAR INC Y DEC
        return None