from Contexto import Contexto
from ID import ID, Variable, Funcion


class TablaSimbolos:
    """
    Administrador central de identificadores
    Maneja una pila de contextos para soportar anidamiento logico
    """
    _instance = None  # atributo de clase para singleton

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TablaSimbolos, cls).__new__(cls)
            cls._instance.contextos = []      # Pila de contextos activos
            cls._instance.historialCTX = []   # Historial de todos los contextos creados
            cls._instance.addContexto()       # Crear el contexto global (nivel 0)
        return cls._instance

    def addContexto(self):
        """Agrega un nuevo contexto a la pila y al historial."""
        nuevo_contexto = Contexto()
         #nivel basado en el último contexto de la pila
        if self.contextos:
            nuevo_contexto.nivel = self.contextos[-1].nivel + 1
        else:
            nuevo_contexto.nivel = 0  #guarda nivel de anidación
        self.contextos.append(nuevo_contexto)       #pila de contextos actual
        self.historialCTX.append(nuevo_contexto)    #historial completo
        return nuevo_contexto

    def delContexto(self):
        """Elimina el último contexto de la pila actual, sin tocar el historial."""
        if len(self.contextos) > 1:
            self.contextos.pop()
        else:
            raise ValueError("No se puede eliminar el contexto global")

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
        """Imprime la tabla de simbolos en el caso de que no haya errores"""
        print("\n[INFO]: Tabla de símbolos final:")
        for idx, contexto in enumerate(self.historialCTX):
            print(f"--- Contexto #{idx} (nivel {contexto.nivel}) ---")
            #encabezado
            print(f"{'Funcion':<30} {'Variable':<20} {'Tipo':<10} {'Inicializado':<12} {'Usado':<6}")

            if not contexto.simbolos:
                print("vacío")
            else:
                for nombre, simbolo in contexto.simbolos.items():
                    
                    #variables auxiliares para llenar las columnas
                    col_funcion = ""
                    col_variable = ""
                    
                    if isinstance(simbolo, Funcion):
                        #si es funcion, armamos el string con argumentos y lo ponemos en col_funcion
                        args_str = "(" + ", ".join(f"{arg['tipo']} {arg['nombre']}" for arg in simbolo.args) + ")"
                        col_funcion = f"{nombre} {args_str}"
                        col_variable = "-" #guion o vacio en la columna de variable
                    
                    elif isinstance(simbolo, Variable):
                        #si es variable, ponemos el nombre en col_variable
                        col_funcion = "-"  #guion o vacio en la columna de funcion
                        col_variable = nombre
    
                    print(f"{col_funcion:<30} {col_variable:<20} {simbolo.tipoDato:<10} {str(simbolo.inicializado):<12} {str(simbolo.usado):<6}")

            print("\n")
    
    def generarArchivo(self, nombre_archivo="TablaDeSimbolos.txt"):
        #funciona igual que imprimirTS nada mas que ahora lo imprime en un archivo
        """Genera un archivo de texto con el contenido de la tabla de símbolos"""
        with open(nombre_archivo, "w") as f:
            
            for idx, contexto in enumerate(self.historialCTX):
                f.write(f"\n--- Contexto #{idx} (nivel {contexto.nivel}) ---\n")
                f.write(f"{'Funcion':<30} {'Variable':<20} {'Tipo':<10} {'Inicializado':<12} {'Usado':<6}\n")
                f.write("-" * 85 + "\n")

                if not contexto.simbolos:
                    f.write("vacío\n")
                else:
                    for nombre, simbolo in contexto.simbolos.items():
                        col_funcion = ""
                        col_variable = ""
                        
                        if isinstance(simbolo, Funcion):
                            args_str = "(" + ", ".join(f"{arg['tipo']} {arg['nombre']}" for arg in simbolo.args) + ")"
                            col_funcion = f"{nombre} {args_str}"
                            col_variable = "-"
                        
                        elif isinstance(simbolo, Variable):
                            col_funcion = "-"
                            col_variable = nombre
        
                        f.write(f"{col_funcion:<30} {col_variable:<20} {simbolo.tipoDato:<10} {str(simbolo.inicializado):<12} {str(simbolo.usado):<6}\n")
            