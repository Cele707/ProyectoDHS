class ID:
    """
    Clase base para cualquier identificador en el compilador.  
    """
    def __init__(self, nombre:str, tipoDato: str):
        self.nombre = nombre
        self.tipoDato = tipoDato
        self.inicializado = False
        self.usado = False
        self.declarado = True
    
    #=================
    #getters y setters
    #=================
    def getNombre(self) -> str:
        return self.nombre
    
    def getTipoDato(self) -> str:
        return self.tipoDato
    
    #valor = True lo pone como True por defecto si no se especifica pero al tener el valor y no ponerlo
    #directamente en self.inicializado permite poner False si se llega a necesitar en algun caso
    def setInicializado(self, valor: bool = True):
        self.inicializado = valor
        
    def getInicializado(self) -> bool:
        return self.inicializado
    
    def setUsado(self, valor:bool = True):
        self.usado = valor
        
    def getUsado(self)-> bool:
        return self.usado
    
    #=========================
    #CLASES VARIABLE Y FUNCION
    #=========================
    
class Variable(ID):
    """Representa una variable, hereda todo de ID"""
    def __init__(self, nombre, tipoDato, inicializado=False, usado=False, declarado=True):
        super().__init__(nombre, tipoDato)
        self.inicializado = inicializado
        self.usado = usado
        self.declarado = declarado  
        
class Funcion(ID):
    """Representa una funcion, ademas de lo basico tambien almacena los argumentos y si fue prototipada"""
    def __init__(self, nombre, tipoDato, inicializado=False, usado=False, declarado=True, args=None):
        super().__init__(nombre, tipoDato)
        self.inicializado = inicializado
        self.usado = usado
        self.declarado = declarado
        
        self.prototipado = False
        self.args = args.copy() if args else []

    def setArgs(self, args:list):
        """Asigna la lista de argumentos de la funcion"""
        self.args = args.copy() if args else []

    def setUsado(self, valor=True):
        self.usado = True

    def getListaArgs(self)-> list:
        return self.args
        