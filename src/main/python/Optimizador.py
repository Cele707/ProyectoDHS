import re

class Optimizador:
    def __init__(self, archivo_entrada="output/CodigoIntermedio.txt", archivo_salida="output/CodigoOptimizado.txt"):
        self.archivo_entrada = archivo_entrada
        self.archivo_salida = archivo_salida
        self.codigo = []

    def cargar_codigo(self):
        try:
            with open(self.archivo_entrada, "r") as f:
                self.codigo = [line.strip() for line in f.readlines() if line.strip()]
            return True
        except FileNotFoundError:
            print(f"[ERROR]: No se encontró {self.archivo_entrada}")
            return False

    def guardar_codigo(self):
        with open(self.archivo_salida, "w") as f:
            for linea in self.codigo:
                f.write(linea + "\n")
        print(f"Archivo generado: {self.archivo_salida}")

    def es_temporal(self, var):
        """Retorna True si la variable empieza con 't' y sigue un numero (t0, t1...)"""
        return var.startswith('t') and var[1:].isdigit()

    # =======================================================
    # PLEGADO DE CONSTANTES
    # Convierte t0 = 5 + 5  en  t0 = 10
    # =======================================================
    def plegado_constantes(self):
        """
        El plegado de constantes consiste en detectar operaciones donde ambos operandos son valores
        conocidos por lo cual se puede resolver en tiempo de compilacion.
        """
        nuevo_codigo = []
        cambios = False

        for linea in self.codigo:
            #expresion regular res = op1 OPERADOR op2
            regex = r'(\w+)\s*=\s*(\d+)\s*(==|!=|>=|<=|&&|\|\||[\+\-\*\/<>])\s*(\d+)'
            #(\w+): cualquier palabra 
            #\s*=\s*: signo = (\s* para capturar si hay espacios)
            #(\d+): op1 y op2 al final
            #(==|!=|>=|<=|&&|\|\||[\+\-\*\/<>]) capta los operadores
            match = re.match(regex, linea)#esto significa que la linea "matchea" con la expresion regular
            
            if match:
                res, op1, operador, op2 = match.groups()#match.groups son los distintos grupos que estan en el regex
                val1, val2 = int(op1), int(op2)
                resultado = None #usamos None para saber si calculamos algo

                #si es una operacion aritmetica calcula el valor del resultado
                if operador == '+': resultado = val1 + val2
                elif operador == '-': resultado = val1 - val2
                elif operador == '*': resultado = val1 * val2
                elif operador == '/': resultado = val1 // val2 if val2 != 0 else 0
                
                #si es operacion logica devuelve 1 (true) o 0 (false)
                elif operador == '<': resultado = 1 if val1 < val2 else 0
                elif operador == '>': resultado = 1 if val1 > val2 else 0
                elif operador == '<=': resultado = 1 if val1 <= val2 else 0
                elif operador == '>=': resultado = 1 if val1 >= val2 else 0
                elif operador == '==': resultado = 1 if val1 == val2 else 0
                elif operador == '!=': resultado = 1 if val1 != val2 else 0
                
                elif operador == '&&': resultado = 1 if (val1 and val2) else 0
                elif operador == '||': resultado = 1 if (val1 or val2) else 0

                #reconstruir la linea
                if resultado is not None:#si se pudo calcular algo se actualiza
                    nueva_linea = f"{res} = {resultado}"
                    if nueva_linea != linea:
                        print(f"[OPT] Plegado de constantes: {linea} -> {nueva_linea}")
                        nuevo_codigo.append(nueva_linea)
                        cambios = True
                    else:
                        nuevo_codigo.append(linea)
                else:
                    nuevo_codigo.append(linea)
            else:
                nuevo_codigo.append(linea)
        
        self.codigo = nuevo_codigo
        return cambios

    # =======================================================
    # PROPAGACION DE COPIA
    # Detecta: t0 = VALOR  y luego  x = t0
    # Convierte a: x = VALOR
    # =======================================================
    def propagacion_copia(self):
        """
        Si encuentra 'A = B' y la linea anterior era 'B = ...', 
        fusiona ambas líneas para eliminar el intermediario B.
        """
        indices_a_borrar = set()
        cambios = False

        #recorrer el codigo buscando asignaciones
        for i in range(1, len(self.codigo)):#se empieza desde la segunda linea pq hay que comparar siempre la actual con la anterior
            linea_actual = self.codigo[i]
            linea_anterior = self.codigo[i-1]

            #parseamos linea actual: dest = src
            parts_act = [p.strip() for p in linea_actual.split('=')]
            
            #separamos las dos partes asignaciones
            if len(parts_act) == 2 and 'call' not in linea_actual:
                dest, src = parts_act[0], parts_act[1]
                
                #parseamos linea anterior: VAR_ANT = VALOR_ANT
                parts_prev = [p.strip() for p in linea_anterior.split('=')]
                
                # CHEQUEO DE FUSION:
                # 1. La anterior debe ser una asignación (len=2)
                # 2. La variable definida en la anterior (parts_prev[0]) debe ser igual a la usada ahora (src)
                # 3. La variable anterior debe ser un TEMPORAL (t0, t1) para evitar romper lógica de variables reales
                if len(parts_prev) == 2 and parts_prev[0] == src and self.es_temporal(src):
                    
                    valor_original = parts_prev[1]
                    
                    nueva_anterior = f"{dest} = {valor_original}"
                    self.codigo[i-1] = nueva_anterior #reemplazamos la anterior
                    indices_a_borrar.add(i)           #borramos la actual (ya se fusionó arriba)
                    
                    print(f"[OPT] Propagación de copia: Fusión de '{src}' -> {nueva_anterior}")
                    cambios = True

        #reconstruir eliminando las lineas borradas
        if cambios:
            self.codigo = [linea for i, linea in enumerate(self.codigo) if i not in indices_a_borrar]
            
        return cambios

    # =======================================================
    # ELIMINACION DE CODIGO MUERTO
    # =======================================================
    def eliminacion_codigo_muerto(self):
        """
        Elimina variables que se definen pero nunca se usan
        """
        usos = {} #contador de usos ej: {'t0': 2, 'a': 1}
        definiciones = {} #mapa para saber la linea donde se define ej { Linea_5:'t0'}

        #1: Contar usos
        for i, linea in enumerate(self.codigo):
            #separar por espacios y simbolos
            tokens = re.findall(r'\w+', linea)
            #\w+ cualquier cantidad (1 o mas) de letras, numeros o guiones bajos
            #si encuentra: t1 = variable_a + (b * 10);
            #lo guarda asi: ['t1', 'variable_a', 'b', '10']
            
            #si es asignacion (LHS = RHS) LHS: Left Hand Side, RHS: Right Hand Side
            if '=' in linea:
                partes = linea.split('=')
                lhs = partes[0].strip()
                rhs = partes[1]
                
                #el lado izquierdo es una definicion, no cuenta como uso
                definiciones[i] = lhs
                
                #el lado derecho son usos
                tokens_rhs = re.findall(r'\w+', rhs)
                for t in tokens_rhs:
                    usos[t] = usos.get(t, 0) + 1
            
            #si no es asignacion (param, ifnot, return), todo son usos
            #de esta forma tambien nos evitamos borrar etiquetas por las dudas
            else:
                for t in tokens:
                    if t not in ['param', 'ifnot', 'jmp', 'return', 'label', 'call']:
                         usos[t] = usos.get(t, 0) + 1

        #2: Eliminar lineas inutiles
        nuevo_codigo = []
        cambios = False
        
        for i, linea in enumerate(self.codigo):
            if i in definiciones:
                var_definida = definiciones[i]
                
                # Si la variable tiene 0 usos
                if usos.get(var_definida, 0) == 0:
                    #NO borrar llamadas a funcion
                    if 'call' in linea:
                        nuevo_codigo.append(linea)
                        continue
                    
                    print(f"[OPT] Código muerto eliminado: {linea}")
                    cambios = True
                    continue 

            nuevo_codigo.append(linea)

        self.codigo = nuevo_codigo
        return cambios

    def ejecutar(self):
        if not self.cargar_codigo():
            return
        
        print("\n==============================")
        print("OPTIMIZACION GENERADA")
        print("==============================")
        iteracion = 1
        while True:
            print(f"--- Iteración {iteracion} ---")
            c1 = self.plegado_constantes()
            c2 = self.propagacion_copia()
            c3 = self.eliminacion_codigo_muerto()
            
            #Si en una pasada completa no hubo ningun cambio, terminamos
            if not (c1 or c2 or c3):
                break
            iteracion += 1
            
        print("==============================\n")
        self.guardar_codigo()

