class ID:
    #cuando se crea una clase 
    def __init__(self, nombre:str, tipoDato: str):
        self.nombre = nombre
        self.tipoDato = tipoDato
        self.inicializado = False
        self.usado = False
    
    #=================
    #getters y setters
    #=================
    def getNombre(self):
        return self.nombre
    
    def getTipoDato(self):
        return self.tipoDato
    
    #valor = True lo pone como True por defecto si no se especifica pero al tener el valor y no ponerlo
    #directamente en self.inicializado permite poner False si se llega a necesitar en algun caso
    def setInicializado(self, valor = True):
        self.inicializado = valor
        
    def getInicializado(self):
        return self.inicializado
    
    def setUsado(self, valor= True):
        self.usado = valor
        
    def getUsado(self):
        return self.usado
    
    #=========================
    #CLASES VARIABLE Y FUNCION
    #=========================
    
class Variable(ID):
        #representa una variable del programa con su tipo de dato y estado
        pass
class Funcion(ID):
        #representa una funcion con el tipo que devuelve y lista de argumentos
    def __init__(self, nombre, tipoDato, args = None):
        super().__init__(nombre, tipoDato)
        self.args = args if args else []
        
    def getListaArgs(self):
        return self.args
        