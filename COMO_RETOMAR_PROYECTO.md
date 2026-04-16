# Como retomar este proyecto en otro dia

Esta guia es para cuando cierras VS Code, trabajas en otros proyectos y luego vuelves a este repo.

## Flujo rapido (2 minutos)

1. Abre VS Code y abre la carpeta del proyecto.
2. Abre una terminal en la raiz del repo.
3. Activa el entorno virtual:

```bash
source .venv/bin/activate
```

4. Ejecuta el compilador con un input de prueba:

```bash
.venv/bin/python src/main/python/App.py input/entradaSinErrores.txt
```

5. Revisa la consola:
- Mensajes sintacticos: salen por EscuchaSintactico.
- Mensajes semanticos y advertencias: salen por Escucha.

## Si quieres probar con errores

```bash
.venv/bin/python src/main/python/App.py input/entradaConErrores.txt
```

## Si quieres ver el parse tree en texto

1. En `src/main/python/App.py`, descomenta la linea:

```python
#print(tree.toStringTree(recog=parser))
```

2. Debe quedar asi:

```python
print(tree.toStringTree(recog=parser))
```

3. Ejecuta de nuevo el mismo comando.

## Si no te reconoce paquetes (antlr4)

Activa primero la venv y reinstala:

```bash
source .venv/bin/activate
pip install antlr4-python3-runtime==4.9
```

## Opcional: dejar VS Code apuntando siempre a la venv

1. Ctrl+Shift+P
2. Python: Select Interpreter
3. Elige el interprete de `.venv`

Con eso, Run/Debug suele usar automaticamente ese Python para este proyecto.

## Recordatorio corto

Cada vez que vuelvas al repo:
1. `source .venv/bin/activate`
2. Ejecutar `App.py` con un input
3. Mirar consola
