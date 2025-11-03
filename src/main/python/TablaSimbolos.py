from Contexto import Contexto
from ID import ID, Variable


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
        for idx, contexto in enumerate(self.historialCTX):
            # Título del contexto sin sangría
            print(f"--- Contexto #{idx} (nivel {contexto.nivel}) ---")
            
            # Cabecera de columnas sin sangría
            print(f"{'Variable':<15} {'Tipo':<10} {'Inicializado':<12} {'Usado':<6}")

            if not contexto.simbolos:
                print("vacío")
            else:
                for nombre, simbolo in contexto.simbolos.items():
                    print(f"{nombre:<15} {simbolo.tipoDato:<10} "
                        f"{str(simbolo.inicializado):<12} {str(simbolo.usado):<6}")

            # Línea en blanco entre contextos
            print("\n")
