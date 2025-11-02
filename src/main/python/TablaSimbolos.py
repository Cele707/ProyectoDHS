from Contexto import Contexto
from ID import ID

class TablaSimbolos :
    _instance = None #atributo de clase para singleton
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TablaSimbolos, cls).__new__(cls)
            cls._instance.contextos = [] #lista de contextos
            cls._instance.addContexto() #para tener el contexto 0
        return cls._instance #retorna la unica instancia si ya existe
    
    def addContexto(self):
        #agrega un nuevo contexto a la pila
        nuevo = Contexto()
        nuevo = self.contextos.append(nuevo)
        return nuevo
    
    
    def delContexto(self): #elimina el ultimo contexto, no se puede eliminar el contexto 0
        #elimina el contexto actual
        if len(self.contextos) > 1:
            self.contextos.pop()
        else:
            raise ValueError("No se puede eliminar el contexto global")
    
    def addSimbolo(self, id_obj: ID):
        #agrega una variable en el contexto actual
        self.contextos[-1].addSimbolo(id_obj)# con -1 se accede al ultimo de la lista
        
    def buscarSimbolo(self, nombre):
        #busca un simbolo en los contextos, empezando por el mas interno
        for contexto in reversed(self.contextos):
            simbolo = contexto.buscarSimbolo(nombre)
            if simbolo is not None:
                return simbolo
        return None
    
    def buscarSimboloContexto(self, nombre):
        #busca un simbolo en el contexto actual
        return self.contextos[-1].buscarSimbolo(nombre)   