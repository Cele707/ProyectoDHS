#EscuchaSintactico.py
from antlr4.error.ErrorListener import ErrorListener

#lo que hace nuestro EscuchaSintactico es ver los mensajes de error que tira por defecto ANTLR,
#identificarlos y cambiar el mensaje que se muestra
class EscuchaSintactico(ErrorListener):
    def __init__(self):
        super().__init__()
        self.errores = []

    def _obtener_linea_anterior(self, recognizer, offendingSymbol, linea_por_defecto):
        """
        Devuelve la línea del token anterior para reportar mejor errores
        que ANTLR detecta recién en la línea siguiente.
        """
        try:
            if offendingSymbol is None or offendingSymbol.tokenIndex <= 0:
                return linea_por_defecto

            tokens = recognizer.getInputStream().tokens
            token_previo = tokens[offendingSymbol.tokenIndex - 1]
            return token_previo.line
        except Exception:
            return linea_por_defecto

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        texto = offendingSymbol.text if offendingSymbol is not None else ""
        msg_min = msg.lower()
        mensaje = ""

        # Normalizamos algunas pistas para clasificar mejor los errores.
        es_identificador = texto.isidentifier()
        es_tipo = texto in ["int", "double", "float", "void", "char", "bool"]
        es_cierre_bloque = texto in ["}", "else", "<EOF>"]
        es_apertura_bloque = texto == "{"
        es_cierre_parentesis = texto in ["{", ";", "else", "ID", "NUMERO", ")", "<EOF>"]

        # --- FALTA DE PARENTESIS DE CIERRE ---
        if (
            (("expecting ')'" in msg_min or "missing ')'" in msg_min) and texto in ["{", ";", "else", ")", "ID", "NUMERO", "<EOF>"])
            or ("no viable alternative at input" in msg_min and texto in ["{", ";", "else", "ID", "NUMERO", ")"])
        ):
            mensaje = f"[ERROR SINTACTICO] falta un paréntesis de cierre ')' antes de '{texto}' (línea {line})"

        # --- FALTA DE PARENTESIS DE APERTURA ---
        elif ("extraneous input" in msg_min and texto == ")") or ("missing '('" in msg_min):
            mensaje = f"[ERROR SINTACTICO] falta un paréntesis de apertura '(' (línea {line})"

        # --- FALTA DE PUNTO Y COMA ---
        elif (
            "expecting ';'" in msg_min
            or ("mismatched input" in msg_min and "expecting ';'" in msg_min)
            or ("mismatched input" in msg_min and texto in ["}", "else"])
            or ("no viable alternative at input" in msg_min and texto in ["int", "double", "float", "void", "char", "bool", "if", "while", "for", "return", "<EOF>"])
        ):
            linea_reportada = line
            if "expecting ';'" in msg_min or "no viable alternative" in msg_min:
                linea_reportada = self._obtener_linea_anterior(recognizer, offendingSymbol, line)

            mensaje = f"[ERROR SINTACTICO] falta un punto y coma ';' al final de la instrucción (línea {linea_reportada})"

        # --- LISTA DE PARÁMETROS DE FUNCIÓN O PROTOTIPO MAL FORMADA ---
        elif (
            ("expecting ')'" in msg_min or "missing ')'" in msg_min)
            and texto in ["bool", "char", "double", "float", "int", "void", "ID", ",", ")"]
        ):
            mensaje = f"[ERROR SINTACTICO] formato incorrecto en la declaración o prototipo de función (línea {line})"

        # --- FALTA DE COMA ENTRE VARIABLES O DECLARACIÓN MAL FORMADA ---
        elif (
            ("no viable alternative at input" in msg_min or "mismatched input" in msg_min)
            and es_identificador
            and not es_tipo
        ):
            try:
                # Obtenemos el siguiente token para adivinar si falta la coma.
                siguiente_token_obj = recognizer.getTokenStream().LT(1)
                siguiente_texto = siguiente_token_obj.text if siguiente_token_obj else ""
                if siguiente_texto.isidentifier():
                    mensaje = f"[ERROR SINTACTICO] falta una coma entre variables antes de '{siguiente_texto}' (línea {line})"
                else:
                    mensaje = f"[ERROR SINTACTICO] falta una coma o separador en la lista de variables (línea {line})"
            except:
                mensaje = f"[ERROR SINTACTICO] falta una coma o separador en la lista de variables (línea {line})"

        # --- FORMATO INCORRECTO EN LISTA DE DECLARACIÓN ---
        elif (
            "missing id" in msg_min
            or ("mismatched input" in msg_min and "id" in msg_min)
            or ("no viable alternative at input" in msg_min and es_tipo)
            or ("extraneous input" in msg_min and es_identificador)
        ):
            mensaje = f"[ERROR SINTACTICO] formato incorrecto en la lista de declaración de variables (línea {line})"

        # --- FALTA DE LLAVE DE CIERRE ---
        elif (
            "expecting '}'" in msg_min
            or "missing '}'" in msg_min
            or ("no viable alternative at input" in msg_min and texto == "<EOF>")
        ):
            linea_reportada = self._obtener_linea_anterior(recognizer, offendingSymbol, line)
            mensaje = f"[ERROR SINTACTICO] falta una llave de cierre '}}' (línea {linea_reportada})"

        # --- FALTA DE LLAVE DE APERTURA ---
        elif (
            "expecting '{'" in msg_min
            or "missing '{'" in msg_min
            or ("mismatched input" in msg_min and "expecting '{'" in msg_min)
        ):
            mensaje = f"[ERROR SINTACTICO] falta una llave de apertura '{{' (línea {line})"

        # --- LISTA DE PARÁMETROS DE FUNCIÓN O PROTOTIPO MAL FORMADA ---
        elif (
            "no viable alternative at input" in msg_min
            and texto in ["int", "double", "float", "void", "char", "bool", "id", ",", ")"]
        ):
            mensaje = f"[ERROR SINTACTICO] formato incorrecto en la declaración o prototipo de función (línea {line})"

        # --- OTROS ERRORES ---
        else:
            mensaje = f"[ERROR SINTACTICO] línea {line}, columna {column}: {msg}"

        self.errores.append(mensaje)
        print(mensaje)