from Contexto import Contexto
from ID import ID, Variable, Funcion


class TablaSimbolos:
    _instance = None  # atributo de clase para singleton

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TablaSimbolos, cls).__new__(cls)
            cls._instance.contextos = []      # Pila de contextos actuales
            cls._instance.historialCTX = []   # Historial de todos los contextos creados
            cls._instance.addContexto()       # Crear el contexto global (nivel 0)
        return cls._instance

    def addContexto(self):
        """Agrega un nuevo contexto a la pila y al historial."""
        nuevo_contexto = Contexto()
         # Nivel basado en el último contexto de la pila
        if self.contextos:
            nuevo_contexto.nivel = self.contextos[-1].nivel + 1
        else:
            nuevo_contexto.nivel = 0  # Guarda nivel de anidación
        self.contextos.append(nuevo_contexto)       # Pila de contextos actual
        self.historialCTX.append(nuevo_contexto)    # Historial completo
        return nuevo_contexto

    def delContexto(self):
        """Elimina el último contexto de la pila actual, sin tocar el historial."""
        if len(self.contextos) > 1:
            self.contextos.pop()
        #else:
            #raise ValueError("No se puede eliminar el contexto global")

    def addSimbolo(self, id_obj: ID):
        """Agrega un símbolo al contexto actual (tope de la pila)."""
        self.contextos[-1].addSimbolo(id_obj)

    def buscarSimbolo(self, nombre):
        """Busca un símbolo en los contextos de adentro hacia afuera."""
        for contexto in reversed(self.contextos):
            simbolo = contexto.buscarSimbolo(nombre)
            if simbolo is not None:
                return simbolo
        return None

    def buscarSimboloContexto(self, nombre):
        """Busca un símbolo solo en el contexto actual (tope de la pila)."""
        return self.contextos[-1].buscarSimbolo(nombre)

    def imprimirTS(self):
        print("\n[INFO]: Tabla de símbolos final:")
        for idx, contexto in enumerate(self.historialCTX):
            print(f"--- Contexto #{idx} (nivel {contexto.nivel}) ---")
            
            # DEFINICIÓN DE COLUMNAS:
            # Funcion: 30 espacios (para que quepan nombre y argumentos)
            # Variable: 20 espacios
            # Tipo: 10 espacios
            # Inicializado: 12 espacios
            # Usado: 6 espacios
            print(f"{'Funcion':<30} {'Variable':<20} {'Tipo':<10} {'Inicializado':<12} {'Usado':<6}")

            if not contexto.simbolos:
                print("vacío")
            else:
                for nombre, simbolo in contexto.simbolos.items():
                    
                    # Variables auxiliares para llenar las columnas
                    col_funcion = ""
                    col_variable = ""
                    
                    if isinstance(simbolo, Funcion):
                        # Si es funcion, armamos el string con argumentos y lo ponemos en col_funcion
                        # Asumiendo que simbolo.args es tu lista de diccionarios
                        args_str = "(" + ", ".join(f"{arg['tipo']} {arg['nombre']}" for arg in simbolo.args) + ")"
                        col_funcion = f"{nombre} {args_str}"
                        col_variable = "-" # Guion o vacio en la columna de variable
                    
                    elif isinstance(simbolo, Variable):
                        # Si es variable, ponemos el nombre en col_variable
                        col_funcion = "-"  # Guion o vacio en la columna de funcion
                        col_variable = nombre
                    
                    # IMPRESIÓN DE LA FILA
                    # Usamos los mismos anchos definidos arriba (<30, <20, etc.)
                    print(f"{col_funcion:<30} {col_variable:<20} {simbolo.tipoDato:<10} {str(simbolo.inicializado):<12} {str(simbolo.usado):<6}")

            print("\n")
            