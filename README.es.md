<p align="center">
  <strong>Language:</strong>
  <a href="README.md">English</a> |
  <a href="README.ko.md">한국어</a> |
  <a href="README.zh-CN.md">简体中文</a> |
  <a href="README.ja.md">日本語</a> |
  <a href="README.es.md">Español</a> |
  <a href="README.ru.md">Русский</a>
</p>

Este documento es una traducción automática con IA de la versión en inglés. Si hay diferencias, prevalece la versión en inglés.

# AVD

<p align="center">
  <a href="https://github.com/metapbl/AVD/releases"><img alt="Latest release" src="https://img.shields.io/github/v/release/metapbl/AVD?style=flat-square"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue?style=flat-square"></a>
  <a href="#requisitos"><img alt="Python 3.12+" src="https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat-square&logo=python&logoColor=white"></a>
  <a href="#requisitos"><img alt="Platform: Windows | macOS" src="https://img.shields.io/badge/platform-Windows_%7C_macOS-lightgrey?style=flat-square"></a>
</p>

Un descargador de vídeo y audio en Python basado en yt-dlp — compatible con YouTube y más de 1000 sitios.

## Funciones

AV Downloader es una aplicación de escritorio (PySide6) que pone [yt-dlp](https://github.com/yt-dlp/yt-dlp) detrás de una ventana, para descargar sin usar la línea de comandos.

- Descargas de vídeo y audio (MP3/M4A) con los metadatos y la miniatura incrustados en el archivo
- Una ventana de calidad: mejor calidad, máxima compatibilidad (H.264 + AAC), cada resolución, MP3 o M4A; recuerda tu última elección
- Varias descargas a la vez con cola, y progreso, velocidad y tiempo restante en directo
- Listas de reproducción: elige solo los elementos que quieras (hasta 500)
- Normalización del volumen MP3 (ReplayGain sin pérdidas) con el paquete incluido `gaindb`
- Cookies de inicio de sesión (Firefox o cookies.txt) para vídeos que tu propia cuenta puede ver, como los que tienen restricción de edad
- Enlaces desde el portapapeles, Ctrl+V, arrastrar y soltar, o varias líneas a la vez
- Temas oscuro y claro; seis idiomas (English, 한국어, 简体中文, 日本語, Español, Русский)
- Mantiene yt-dlp actualizado por sí misma y nunca sobrescribe un archivo con el mismo nombre

## Requisitos

- **Windows 11** (la versión publicada es para Windows x64). **macOS** funciona ejecutándolo desde el código fuente. Linux no es compatible: allí no funciona abrir la carpeta de descargas.
- **ffmpeg / ffprobe** en el PATH — para combinar, convertir a MP3/M4A e incrustar etiquetas. Windows: `winget install Gyan.FFmpeg` o las [compilaciones de Gyan](https://www.gyan.dev/ffmpeg/builds/).
- **Node.js** en el PATH — opcional en general, pero necesario para YouTube, que obliga a yt-dlp a resolver un desafío de JavaScript ([yt-dlp EJS](https://github.com/yt-dlp/yt-dlp/wiki/EJS)). Deno o Bun también sirven. Windows: `winget install OpenJS.NodeJS`.
- **Python 3.12 o posterior** — solo para ejecutar desde el código fuente.

## Instalación

### Versión publicada (Windows x64)

1. Descarga `AVD-v{versión}-win64.zip` desde [Releases](https://github.com/metapbl/AVD/releases) y descomprímelo donde quieras. Obtendrás una carpeta `AVD`.
2. Instala ffmpeg y Node.js (consulta [Requisitos](#requisitos)). No están incluidos.
3. Ejecuta `AVD\AVD.exe`. No hace falta Python.

Los ajustes se guardan en `config.json` junto a `AVD.exe`, así que si mueves la carpeta, los ajustes se mueven con ella.

### Desde el código fuente

```bash
git clone https://github.com/metapbl/AVD.git
cd AVD
python -m venv venv
venv\Scripts\python -m pip install -r requirements.txt
```

Esto crea un entorno virtual e instala en él los paquetes de la aplicación. En macOS usa `venv/bin/python` en lugar de `venv\Scripts\python`. `requirements.txt` fija a propósito una versión antigua de yt-dlp; la aplicación la actualiza la primera vez que se inicia.

## Inicio rápido

```bash
venv\Scripts\python main.py
```

Se abre una ventana titulada **AV Downloader** con su versión, en el idioma de tu sistema, con una lista vacía y una indicación para añadir enlaces. Copia el enlace de un vídeo, pulsa **Ctrl+V** en la ventana, elige una calidad y pulsa **Descargar**. El archivo se guarda en tu carpeta `Downloads`; cuando termina, **📂 Abrir** lo muestra.

## Uso

- **Añadir enlaces** — el botón **+ Añadir enlaces**, Ctrl+V, o arrastra los enlaces a la ventana. Cada enlace abre la ventana de calidad por turnos; un enlace de lista de reproducción abre una lista para elegir.
- **Calidad** — *Mejor calidad (automática)* deja elegir a yt-dlp; *Máxima compatibilidad* elige un MP4 H.264 + AAC que se reproduce casi en cualquier sitio; MP3 y M4A guardan solo el audio.
- **Ajustes (⚙)** — carpeta de destino, número de descargas simultáneas (se recomienda 1–3), cookies de inicio de sesión, normalización del volumen MP3, comprobación automática de actualizaciones de yt-dlp, idioma y tema. Los cambios se aplican al pulsar **Guardar**, sin reiniciar.
- **Archivos** — nunca se sobrescribe un archivo con el mismo nombre; el nuevo se guarda como `Title (1).mp4`. Durante la descarga aparece una carpeta de trabajo `.avd_*` en la carpeta de destino, que desaparece cuando termina el elemento. Las carpetas de trabajo que quedan tras un cierre inesperado se eliminan un día después, al iniciar la aplicación.

## Cookies de inicio de sesión

Los vídeos que requieren una cuenta con sesión iniciada, como los que tienen restricción de edad, se pueden descargar con las cookies de tu propia cuenta. Actívalo en **⚙ Ajustes > Cookies de inicio de sesión**; está desactivado por defecto.

- **Leer de Firefox** — inicia sesión en el sitio (YouTube u otros) en Firefox y elige esta opción. Es la forma más sencilla.
- **Archivo cookies.txt** — para Chrome, Edge y otros navegadores, exporta las cookies a un archivo y elígelo. En Windows, Chrome y Edge cifran las cookies para su propio uso, así que no se pueden leer directamente.

Cómo crear cookies.txt (Chrome, Edge):

1. Instala la extensión **Get cookies.txt LOCALLY** desde la Chrome Web Store (la que recomienda la documentación de yt-dlp). Algunas extensiones con nombres parecidos han enviado cookies a otros sitios, así que comprueba el nombre con cuidado.
2. Abre una **ventana privada (Incógnito/InPrivate)** e inicia sesión en el sitio. Las cookies de una ventana normal las sustituye pronto el sitio, y el archivo exportado deja de servir.
3. En esa ventana, pulsa la extensión y usa **Export** para exportar las cookies del sitio; después cierra la ventana privada.
4. En AVD, elige el archivo con **Examinar** junto a **Archivo cookies.txt**.

Conviene saber:

- cookies.txt contiene tu inicio de sesión. No lo compartas y bórralo cuando termines.
- AVD no copia ni guarda cookies y nunca modifica tu cookies.txt. En los ajustes solo se guardan el método elegido y la ruta del archivo.
- Descargar mucho en poco tiempo con una cuenta con sesión iniciada puede hacer que el sitio limite esa cuenta.
- El contenido protegido con DRM no se descarga, ni siquiera con cookies ([Política de distribución](#política-de-distribución)).

## Estado del proyecto

- Desarrollado y probado en **Windows 11**, tanto desde el código fuente como con la versión publicada. Cada cambio ejecuta una batería de pruebas automáticas (pytest).
- **macOS** desde el código fuente es compatible, pero aún no se ha comprobado en un Mac real. No hay paquete de aplicación para macOS.
- Los idiomas de la interfaz distintos del inglés y el coreano son traducciones automáticas con IA. Las correcciones son bienvenidas (ver abajo).
- Lo desarrolla una sola persona con asistentes de IA. Las funciones aún cambian entre versiones; consulta [CHANGELOG.md](CHANGELOG.md).

## Ayuda y contribuciones

- **Preguntas y errores** — abre una [issue](https://github.com/metapbl/AVD/issues). Si es un error de descarga, incluye el texto de **Detalles** del elemento que falló.
- **Pull requests** — las correcciones de traducción y los arreglos pequeños son bienvenidos. Para cambios mayores, abre primero una issue para acordar el enfoque.
- **Antes de enviar un pull request**, ejecuta las pruebas y el linter:

  ```bash
  venv\Scripts\python -m pip install -r requirements-dev.txt
  venv\Scripts\python -m pytest
  venv\Scripts\ruff check .
  ```

  Esto instala las herramientas de desarrollo, ejecuta todas las pruebas y revisa el estilo del código; los tres comandos deben terminar sin errores.
- **Las traducciones** están en `i18n/avd_{idioma}.ts` y se pueden editar con Qt Linguist (`venv\Scripts\pyside6-linguist`). Después de editarlas, ejecuta `venv\Scripts\python tools/update_translations.py` para regenerar los archivos `.qm` y confirma ambos.
- Las reglas del proyecto y las notas de diseño están en [AGENTS.md](AGENTS.md) y [docs/](docs/) (en coreano).

## Seguridad

Informa de las vulnerabilidades de forma privada a través de GitHub: pestaña **Security** del repositorio → **Report a vulnerability**. No abras una issue pública para ellas.

## Política de distribución

**Distribución gratuita.** El autor distribuye AVD gratis como código abierto en GitHub y no lo vende ni ofrece ediciones de pago. Esto solo describe cómo lo distribuye el autor y no añade ninguna restricción a las licencias de abajo.

**Sin elusión de DRM.** No se añadirán funciones que ayuden a eludir DRM (medidas técnicas de protección) o a acceder sin permiso a contenido de pago o restringido, y las peticiones de funciones se juzgan según esta política. Las [cookies de inicio de sesión](#cookies-de-inicio-de-sesión) son para contenido que tu propia cuenta ya puede ver; eso no es acceso no autorizado, y el contenido protegido con DRM sigue sin descargarse.

## Descargo de responsabilidad

Usa esta herramienta para estudio personal y copias de seguridad. Cumplir las condiciones de uso de cada sitio y la ley de derechos de autor es tu responsabilidad; úsala solo dentro de lo que permite la ley y bajo tu propio riesgo.

Este software se ofrece "tal cual", **sin ninguna garantía**, incluidas las garantías implícitas de comerciabilidad o idoneidad para un fin concreto (las cláusulas de ausencia de garantía de MIT y de LGPL-2.1).

## Créditos

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — el motor de descarga
- [PySide6](https://doc.qt.io/qtforpython-6/) (Qt for Python) — la interfaz gráfica
- [requests](https://requests.readthedocs.io/) — miniaturas y comprobación de actualizaciones
- [psutil](https://pypi.org/project/psutil/) — detener los procesos hijos de ffmpeg/Node al cancelar
- [numpy](https://numpy.org/) y [SciPy](https://scipy.org/) — análisis del volumen en `gaindb`
- [GainDB](https://github.com/metapbl/GainDB) — normalización del volumen MP3, derivada de mp3gain

## Licencia

AVD usa una licencia por carpeta.

- **AVD en sí** — `MIT`. Consulta [LICENSE](LICENSE) para el texto y [NOTICE](NOTICE) para los avisos de copyright y de terceros.
- **El paquete incluido `gaindb/`** — `LGPL-2.1-or-later`. Contiene código adaptado de mp3gain (LGPL-2.1-or-later), así que se distribuye en las mismas condiciones. Consulta [gaindb/LICENSE](gaindb/LICENSE), [gaindb/NOTICE](gaindb/NOTICE) y [gaindb/THIRD_PARTY_LICENSES](gaindb/THIRD_PARTY_LICENSES). Original: <https://github.com/metapbl/GainDB> (versión incluida 1.1.2).

AVD solo llama a las funciones públicas de `gaindb.api`, así que es una "obra que usa la biblioteca" según la §5 de la LGPL-2.1 y su licencia MIT no se ve afectada — igual que al usar PySide6 (LGPLv3) mediante enlace dinámico. Dónde obtener el código fuente de PySide6 y Qt está en la sección de PySide6 de [THIRD_PARTY_LICENSES](THIRD_PARTY_LICENSES). Para cumplir la LGPL, la versión publicada mantiene `gaindb/` como archivos `.py` normales que puedes sustituir por tu propia versión, y cada versión en GitHub incluye el archivo de código fuente de su etiqueta.
