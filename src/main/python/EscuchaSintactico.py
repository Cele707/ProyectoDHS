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
        if ("expecting ')'" in msg or "missing ')'" in msg) \
           and texto in ["{", ";", "ID", "NUMERO"]:
            mensaje = f"[ERROR SINTACTICO] falta un paréntesis de cierre ')' antes de '{texto}' (línea {line})"

        #falta de parentesis de apertura
        elif ("extraneous input" in msg and texto == ")") or ("missing '('" in msg):
            mensaje = f"[ERROR SINTACTICO] falta un paréntesis de apertura '(' (línea {line})"

        #falta de punto y coma
        elif "expecting ';'" in msg or ("mismatched input" in msg and texto in ["}", "else"]):
            mensaje = f"[ERROR SINTACTICO] falta un punto y coma ';' al final de la instrucción (línea {line})"

        #falta de punto y coma antes de una nueva declaracion
        elif ("no viable alternative at input" in msg and texto in ["int", "float", "char", "bool"]):
            mensaje = f"[ERROR SINTACTICO] falta un punto y coma ';' antes de la nueva declaración (línea {line})"

        #falta de identificador en una lista de variables
        elif texto == "<missing ID>":
            mensaje = f"[ERROR SINTACTICO] falta un identificador en la lista de variables (línea {line})"

        #falta de coma entre variables
        elif ("no viable alternative at input" in msg or "mismatched input" in msg) and texto.isidentifier():
            try:
                #obtenemos el siguiente token para adivinar si falta la coma
                siguiente_token_obj = recognizer.getTokenStream().LT(1)
                siguiente_texto = siguiente_token_obj.text if siguiente_token_obj else ""
                if siguiente_texto.isidentifier():
                    mensaje = f"[ERROR SINTACTICO] falta una coma entre variables antes de '{siguiente_texto}' (línea {line})"
                else:
                    mensaje = f"[ERROR SINTACTICO] falta una coma o separador en la lista de variables (línea {line})"
            except:
                mensaje = f"[ERROR SINTACTICO] falta una coma o separador en la lista de variables (línea {line})"

        # --- FORMATO INCORRECTO EN LISTA DE DECLARACIÓN ---
        elif ("missing ID" in msg or ("mismatched input" in msg and "ID" in msg)):
            mensaje = f"[ERROR SINTACTICO] formato incorrecto en la lista de declaración de variables (línea {line})"

        # --- TOKEN '}' INESPERADO ---
        elif "no viable alternative at input" in msg and texto == "}":
            mensaje = f"[ERROR SINTACTICO] probablemente falta un ';' o ')' antes del bloque '}}' (línea {line})"

        # --- ERRORES GENÉRICOS ---
        else:
            mensaje = f"[ERROR SINTACTICO] línea {line}, columna {column}: {msg}"

        self.errores.append(mensaje)
        print(mensaje)
