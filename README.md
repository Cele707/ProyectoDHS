Material practico de la materia Desarrollo de Herramientas de Software.

Requisitos
- Java 21
- Maven 3.8+
- Python 3.10+

Ejecucion rapida (Python)
1. Crear entorno virtual:
	/bin/python3 -m venv .venv
2. Activar entorno virtual:
	source .venv/bin/activate
3. Instalar dependencias:
	pip install antlr4-python3-runtime==4.9
4. Ejecutar el compilador:
	.venv/bin/python src/main/python/App.py

Entradas de ejemplo
- Sin errores: input/entradaSinErrores.txt
- Con errores: input/entradaConErrores.txt

Salida esperada
- output/CodigoIntermedio.txt
- output/CodigoOptimizado.txt
- output/TablaDeSimbolos.txt

Compilar modulo Java (opcional)
- mvn clean test
- mvn package

Notas
- Si quieres pasar otro archivo de entrada:
  .venv/bin/python src/main/python/App.py input/programa.txt
- Los archivos generados de ANTLR ya estan incluidos en el repositorio.
- Si modificas la gramatica compilador.g4, regenera asi:
	mvn -q -DincludeScope=compile -Dmdep.outputFile=/tmp/proyectodhs.cp dependency:build-classpath
	cd src/main/python
	java -cp "$(cat /tmp/proyectodhs.cp)" org.antlr.v4.Tool -Dlanguage=Python3 -visitor compilador.g4
	cd ../../..
