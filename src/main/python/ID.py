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
    def __init__(self, nombre, tipoDato, inicializado=False, usado=False, declarado=True):
        super().__init__(nombre, tipoDato)
        self.inicializado = inicializado
        self.usado = usado
        self.declarado = declarado  
     
    
        pass
class Funcion(ID):
    # representa una funcion con el tipo que devuelve y lista de argumentos
    def __init__(self, nombre, tipoDato, inicializado=False, usado=False, declarado=True, args=None):
        # 1. Al padre (ID) solo le pasamos lo que sabe manejar: nombre y tipoDato
        super().__init__(nombre, tipoDato)
        
        # 2. Sobrescribimos o asignamos los valores específicos aquí en la hija
        self.inicializado = inicializado
        self.usado = usado
        self.declarado = declarado
        
        self.prototipado = False
        self.args = [] if args is None else args

    def setArgs(self, args):
        self.args = args.copy() if args else []

    def setUsado(self, valor=True):
        self.usado = True

    def getListaArgs(self):
        return self.args
        