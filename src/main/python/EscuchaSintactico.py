#EscuchaSintactico.py
from antlr4.error.ErrorListener import ErrorListener

#lo que hace nuestro EscuchaSintactico es ver los mensajes de error que tira por defecto ANTLR,
#identificarlos y cambiar el mensaje que se muestra
class EscuchaSintactico(ErrorListener):
    def __init__(self):
        super().__init__()
        self.errores = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        texto = offendingSymbol.text if offendingSymbol is not None else ""
        mensaje = ""

        #---FALTA DE PARENTESIS DE CIERRE---
        if ("expecting ')'" in msg or "missing ')'" in msg or "no viable alternative at input" in msg) and texto in ["{", ";", "ID", "NUMERO"]:
            mensaje = f"[ERROR SINTACTICO] falta un paréntesis de cierre ')' antes de '{texto}' (línea {line})"

        #--- FALTA DE PARENTESIS DE APERTURA---
        elif ("extraneous input" in msg and texto == ")") or ("missing '('" in msg):
            mensaje = f"[ERROR SINTACTICO] falta un paréntesis de apertura '(' (línea {line})"

        #---FALTA DE PUNTO Y COMA---
        elif ("expecting ';'" in msg 
            or ("mismatched input" in msg and "expecting ';'" in msg)
            or ("mismatched input" in msg and texto in ["}", "else"])
            or ("no viable alternative at input" in msg and texto in ["int", "double", "if", "while", "for", "return"])
            ):
            linea_reportada = line #linea del token ofensivo
            if "expecting ';'" in msg or "no viable alternative" in msg: #estos mensajes de error suelen aparecer cuando se encuentra un error en la siguiente linea no vacia.
                tokens = recognizer.getInputStream().tokens #se cargan los tokens
                if offendingSymbol.tokenIndex > 0:
                    token_previo = tokens[offendingSymbol.tokenIndex - 1]
                    linea_reportada = token_previo.line
            
            mensaje = f"[ERROR SINTACTICO] falta un punto y coma ';' al final de la instrucción (línea {linea_reportada})"


        #--- FALTA DE COMA ENTRE VARIABLES---
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
        elif ("missing ID" in msg 
              or ("mismatched input" in msg and "ID" in msg)
              or ("no viable alternative at input" in msg and texto.isidentifier())
              ):
            mensaje = f"[ERROR SINTACTICO] formato incorrecto en la lista de declaración de variables (línea {line})"

        # --- OTROS ERRORES ---
        else:
            mensaje = f"[ERROR SINTACTICO] línea {line}, columna {column}: {msg}"

        self.errores.append(mensaje)
        print(mensaje)