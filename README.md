# CuantoCuesta
[![CI](https://github.com/CuantoCuesta/CuantoCuestaBackend/actions/workflows/ci.yml/badge.svg)](https://github.com/CuantoCuesta/CuantoCuestaBackend/actions/workflows/ci.yml) [![Coverage](https://img.shields.io/badge/coverage-80%25-brightgreen)](#)

Backend para optmizar cuentas con chatgpt.

## Configuración

Copia el archivo `.env` y ajusta las variables necesarias. La aplicación
requiere al menos `OPENAI_API_KEY` y `DATABASE_URL`. Si tu contraseña de base de
datos contiene caracteres especiales (por ejemplo `!`), pon el valor entre
comillas o codifica esos caracteres (`!` → `%21`).

La versión completa de la API se ejecuta desde `app/main.py`. Se incluye un
ejemplo más simple en `examples/simple_main.py` solo para pruebas locales.

## Using ChatGPT

1. Define tu clave de OpenAI en el archivo `.env` mediante la variable
   `OPENAI_API_KEY`.
2. Importa y utiliza la función `consulta_gpt` del módulo `openai_client.py` en
   tu código.
3. Puedes experimentar de forma local ejecutando el ejemplo
   `examples/simple_main.py`.

```python
from openai_client import consulta_gpt

respuesta = consulta_gpt("¿Cuál es la capital de Chile?")
print(respuesta)
```
