# EscuchaSintactico.py
from antlr4.error.ErrorListener import ErrorListener

class EscuchaSintactico(ErrorListener):
    def __init__(self):
        super().__init__()
        self.errores = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        texto = offendingSymbol.text if offendingSymbol is not None else ""
        mensaje = ""

        # falta de parentesis de cierre
        if ("expecting ')'" in msg or "missing ')'" in msg or "no viable alternative at input" in msg) \
           and texto in ["{", ";", "else", "ID", "NUMERO"]:
            mensaje = f"[ERROR SINTACTICO] falta un paréntesis de cierre ')' antes de '{texto}' (línea {line})"

        #falta de parentesis de apertura
        elif ("extraneous input" in msg and texto == ")") or ("missing '('" in msg):
            mensaje = f"[ERROR SINTACTICO] falta un paréntesis de apertura '(' (línea {line})"

        #falta de punto y coma
        elif "expecting ';'" in msg or ("mismatched input" in msg and texto in ["}", "else"]):
            mensaje = f"[ERROR SINTACTICO] falta un punto y coma ';' al final de la instrucción (línea {line})"

        # falta ';' antes de nueva declaracion (arregla el error de que si falta un ; despues de una declaracion de variables
        # ej: 
        # int x, y, z
        # float w;
        # marcaba como error en lista de declaracion cuando en realidad era que faltaba ;)
        elif ("no viable alternative at input" in msg and texto in ["int", "float", "char", "bool"]):
            mensaje = f"[ERROR SINTACTICO] falta un punto y coma ';' antes de la nueva declaración (línea {line})"

        #errores en listas de declaracion de variables
        elif texto == "<missing ID>":
            mensaje = f"[ERROR SINTACTICO] falta un identificador en la lista de variables (línea {line})"

        elif "no viable alternative at input" in msg and texto.isidentifier():
            mensaje = f"[ERROR SINTACTICO] falta una coma entre variables (línea {line})"

        elif ("missing ID" in msg 
              or ("mismatched input" in msg and "ID" in msg)):
            mensaje = f"[ERROR SINTACTICO] formato incorrecto en la lista de declaración de variables (línea {line})"

        #token '}' inesperado ---
        elif "no viable alternative at input" in msg and texto == "}":
            mensaje = f"[ERROR SINTACTICO] probablemente falta un ';' o ')' antes del bloque '}}' (línea {line})"

        #ptros errores genericos ---
        else:
            mensaje = f"[ERROR SINTACTICO] línea {line}, columna {column}: {msg}"

        self.errores.append(mensaje)
        print(mensaje)
