# CuantoCuesta
Backend para optmizar cuentas con chatgpt.

## Configuración

Copia el archivo `.env` y ajusta las variables necesarias. La aplicación
requiere al menos `OPENAI_API_KEY` y `DATABASE_URL`. Si tu contraseña de base de
datos contiene caracteres especiales (por ejemplo `!`), pon el valor entre
comillas o codifica esos caracteres (`!` → `%21`).

### Render

Si despliegas la aplicación en [Render](https://render.com), debes definir la
variable `DATABASE_URL` en tu servicio:

1. En el panel de Render ve a tu servicio → **Environment**.
2. Agrega una nueva variable con nombre `DATABASE_URL` y como valor la cadena de
   conexión de tu base de datos PostgreSQL.
3. Guarda los cambios y realiza el despliegue para que la aplicación use esta
   configuración.

La versión completa de la API se ejecuta desde `app/main.py`. Se incluye un
ejemplo más simple en `examples/simple_main.py` solo para pruebas locales.

## Using ChatGPT

1. Define tu clave de OpenAI en el archivo `.env` mediante la variable
   `OPENAI_API_KEY`.
2. Importa y utiliza la función asíncrona `consulta_gpt` del módulo
   `openai_client.py` en tu código.
3. Puedes experimentar de forma local ejecutando el ejemplo
   `examples/simple_main.py`.

```python
import asyncio
from openai_client import consulta_gpt


async def main():
    respuesta = await consulta_gpt("¿Cuál es la capital de Chile?")
    print(respuesta)


asyncio.run(main())
```
