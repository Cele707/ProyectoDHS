# EscuchaSintactico.py
from antlr4.error.ErrorListener import ErrorListener

class EscuchaSintactico(ErrorListener):
    def __init__(self):
        super().__init__()
        self.errores = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        
        texto = offendingSymbol.text if offendingSymbol is not None else ""
        mensaje = ""

        #falta de parentesis de cierre
        #posibles msj de error cuando falta parentesis de cierre
        if ("expecting ')'" in msg or "missing ')'" in msg or "no viable alternative at input" in msg) \
           and texto in ["{", ";", "else", "ID", "NUMERO"]:
            mensaje = f"[ERROR SINTACTICO] falta un paréntesis de cierre ')' antes de '{texto}' (línea {line})"

        #falta parrentesis de apertura
        elif ("extraneous input" in msg and texto == ")") or ("missing '('" in msg):
            mensaje = f"[ERROR SINTACTICO] falta un paréntesis de apertura '(' (línea {line})"

        #falta punto y coma
        elif "expecting ';'" in msg or ("mismatched input" in msg and texto in ["}", "else"]):
            mensaje = f"[ERROR SINTACTICO] falta un punto y coma ';' al final de la instrucción (línea {line})"

        #formato incorrecto en declaracion de variables
        #ejemplo: int x, y z;  falta coma entre 'y' y 'z'
        elif ("missing ID" in msg 
              or ("mismatched input" in msg and "ID" in msg) 
              or ("no viable alternative at input" in msg and texto.isidentifier())):
            mensaje = f"[ERROR SINTACTICO] formato incorrecto en la lista de declaración de variables (línea {line})"

        #token '}' inesperado (para recuperación de errores)
        elif "no viable alternative at input" in msg and texto == "}":
            mensaje = f"[ERROR SINTACTICO] probablemente falta un ';' o ')' antes del bloque '}}' (línea {line})"

        #otros errores genericos
        else:
            mensaje = f"[ERROR SINTACTICO] línea {line}, columna {column}: {msg}"

        #guardar e imprimir
        self.errores.append(mensaje)
        print(mensaje)

    #metodo para saber si hay errores (por ahora no lo usamos)
    #def hay_errores(self):
    #    return len(self.errores) > 0
