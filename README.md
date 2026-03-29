# DF-Lore-Translator

Herramienta modular para jugar Dwarf Fortress en español. Incluye un traductor del log del juego en tiempo real, un panel de administración web, un mod para traducir los nombres propios del mundo y scripts de DFHack que se ejecutan desde dentro del juego.

---

## Modulos

| Modulo | Como arrancar | Puerto / ubicacion |
|---|---|---|
| Traductor en tiempo real | `df-lore-translator.bat` o `start-server.bat` + `start-watcher.bat` | Puerto 5100 |
| Panel de administracion | `start-admin.bat` | Puerto 5200 |
| Mod NombresEspanol | `mod/mods/NombresEspanol/start.bat` | — |
| Script `nombres-espanoles` | Desde DFHack dentro del juego | Dentro del juego |
| Script `exportar_enano` | Desde DFHack dentro del juego | Dentro del juego |

---

## Arranque rapido

### 1. Traductor en tiempo real (gamelog)

Lee el `gamelog.txt` del juego en tiempo real, traduce cada linea al español con DeepL (o Google/Azure) y la muestra en consola o en una ventana flotante sobre el juego.

**Opcion A — Panel de control (recomendado):**

```
Doble clic en df-lore-translator.bat
→ Seleccionar "Arrancar servidor + watcher"
```

Se abren dos ventanas: el servidor de traduccion (puerto 5100) y el watcher que lee el log.

**Opcion B — Manual:**

```bash
# Terminal 1: servidor de traduccion
cd backend
python api/app.py

# Terminal 2: watcher del log
cd backend
python watcher/gamelog_watcher.py
```

El watcher detecta nuevas lineas en `gamelog.txt` cada 0.5s y las envia al servidor. Las traducciones aparecen en consola o en overlay segun la configuracion.

---

### 2. Panel de administracion web

Interfaz web para gestionar la cache de traducciones, editar el glosario y ver estadisticas de uso.

```bash
start-admin.bat
# o manualmente:
cd backend
python admin/app.py
```

Abre el navegador en `http://localhost:5200`.

---

### 3. Mod NombresEspanol

Mod para Dwarf Fortress que traduce las palabras del diccionario del juego al español (`language_words.txt`). Incluye una interfaz web para traducir palabra por palabra y generar el fichero del mod.

```bash
mod/mods/NombresEspanol/start.bat
```

Instala las dependencias automaticamente y arranca la interfaz en el navegador. El flujo es:

1. Pulsar "Traer datos" para importar las palabras del juego
2. Traducir palabra por palabra (nombre, verbo, adjetivo...)
3. Pulsar "Generar fichero" para exportar el mod listo para usar

---

### 4. Script DFHack: `nombres-espanoles`

> **Requiere estar dentro del juego con DFHack activo.**

Asigna nombres españoles a enanos, fortalezas y sitios del mundo. Los nombres son personajes y lugares conocidos de la cultura española.

**Antes de usarlo**, despliega los scripts a la carpeta de DFHack:

```bash
# Desde la raiz del proyecto (fuera del juego)
python deploy.py
```

**Dentro del juego**, en la consola de DFHack:

```
nombres-espanoles              # muestra ayuda
nombres-espanoles enanos       # renombra los enanos de tu fortaleza
nombres-espanoles fortaleza    # renombra la fortaleza actual
nombres-espanoles sitios       # renombra los sitios del mundo
nombres-espanoles todo         # renombra enanos + fortaleza + sitios
nombres-espanoles todo forzar  # sobrescribe nombres ya asignados
```

Para que se ejecute automaticamente al cargar la partida, añade esto al archivo `dfhack-config/init.d/nombres.lua` de tu instalacion de DF:

```lua
dfhack.run_script('nombres-espanoles', 'enanos')
```

---

### 5. Script DFHack: `exportar_enano`

> **Requiere estar dentro del juego con DFHack activo.**

Añade un boton **[E]** en la ficha de cada enano. Al pulsarlo, exporta los datos del enano a un archivo TXT.

**Antes de usarlo**, despliega los scripts:

```bash
python deploy.py
```

**Dentro del juego**, en la consola de DFHack:

```
enable exportar_enano
```

El boton `[E]` aparecera en la esquina superior derecha de la pantalla de ficha del enano (`dwarfmode/ViewSheets/UNIT`).

---

### Desplegar scripts a DFHack

Copia o enlaza los scripts Lua a la carpeta de DFHack para que el juego los encuentre:

```bash
# Enlace simbolico (recomendado — los cambios son instantaneos)
python deploy.py

# Copiar archivos (si los symlinks no funcionan)
python deploy.py --copy
```

> En Windows, el enlace simbolico requiere **modo Desarrollador activo** o ejecutar como Administrador.

---

## Configuracion inicial

### 1. Instalar dependencias

```bash
python -m venv venv
venv\Scripts\pip install -r backend\requirements.txt
```

### 2. Configurar variables de entorno

```bash
copy .env.example .env
```

Edita `.env` con tus datos:

```env
TRANSLATION_ENGINE=deepl
DF_INSTALL_PATH=D:/SteamLibrary/steamapps/common/Dwarf Fortress
DEEPL_API_KEY=tu-clave-aqui
```

Solo necesitas la clave del motor que vayas a usar. DeepL ofrece 500.000 caracteres/mes gratis; Google Translate 1.000.000; Azure 500.000.

---

## Requisitos

- Python 3.10 o superior
- Dwarf Fortress instalado (Steam o manual)
- DFHack instalado (para los scripts Lua)
- Clave API de DeepL, Google Translate o Azure Translator

---

## Configuracion avanzada

### Variables de entorno (`.env`)

| Variable | Descripcion | Valores |
|---|---|---|
| `TRANSLATION_ENGINE` | Motor de traduccion activo | `deepl` / `google` / `azure` |
| `DF_INSTALL_PATH` | Ruta de instalacion de Dwarf Fortress | Ruta absoluta |
| `DEEPL_API_KEY` | Clave API de DeepL | — |
| `GOOGLE_API_KEY` | Clave API de Google Translate | — |
| `AZURE_API_KEY` | Clave API de Azure Translator | — |
| `AZURE_REGION` | Region de Azure | `westeurope`, etc. |
| `BEEP_ENABLED` | Pitido en consola al traducir | `true` / `false` |

### Ajustes tecnicos (`backend/config.yaml`)

- `watcher.poll_interval_seconds` — frecuencia de lectura del log (por defecto 0.5s)
- `watcher.translation_service_url` — URL del servidor (por defecto `http://localhost:5100`)
- `display.mode` — modo de visualizacion (`console` / `overlay`)
- `display.overlay.*` — opciones de la ventana flotante

---

## Visualizador

### Modo `console` (por defecto)

Las traducciones aparecen en la ventana del watcher con los colores originales del juego en ANSI.

### Modo `overlay`

Ventana flotante transparente sobre el juego. Click-through: los clics pasan al juego.

- **Barra de control**: boton `⠿` para arrastrar, boton `▼`/`▲` para colapsar
- **Area de texto**: fondo transparente, texto con contorno para legibilidad

Para activarlo: cambia `display.mode` a `overlay` en `config.yaml` o usa el panel de control.

```yaml
display:
  mode: overlay
  overlay:
    x: 10
    y: 10
    width: 700
    height: 300
    font_size: 13
    font_family: "Consolas"
    default_text_color: "#FFFFFF"
    outline_color: "#000000"
    outline_width: 2
    always_on_top: true
    max_messages: 10
    fade_seconds: 0     # 0 = permanente
```

Para el segundo monitor, suma la resolucion horizontal del primero al valor de `x`:

```yaml
x: 1930   # segundo monitor a la derecha de uno de 1920px
y: 10
```

---

## Glosario de terminos (solo DeepL)

El archivo `backend/glossary.txt` fuerza traducciones concretas para palabras que DeepL traduce mal:

```
# Comentarios con #
misses   = falla
strikes  = golpea
dwarf    = enano
dwarves  = enanos
```

Para aplicar cambios: reinicia el servidor. Se sincroniza automaticamente con DeepL al arrancar.

---

## Cache de traducciones

Todas las traducciones se guardan en `backend/cache/translations.db` (SQLite). Las peticiones repetidas se sirven desde cache sin coste de API.

### Limpiar la cache (`manage.py`)

```bash
# Ver que se eliminaria sin borrar nada
python manage.py clean --min-uses 2 --older-than-days 30 --dry-run

# Eliminar entradas usadas menos de 2 veces Y sin usar en mas de 30 dias
python manage.py clean --min-uses 2 --older-than-days 30

# Solo por antigüedad
python manage.py clean --older-than-days 60

# Solo por uso
python manage.py clean --min-uses 3
```

Las entradas con `is_edited = 1` nunca se eliminan.

### Editar una traduccion manualmente

Abre `translations.db` con [DB Browser for SQLite](https://sqlitebrowser.org/), edita el campo `translated` y pon `is_edited = 1` para que no sea sobreescrita.

---

## Logs

Los logs se generan en `backend/logs/`:

| Archivo | Contenido |
|---|---|
| `translations_YYYY-MM-DD.log` | Log diario con cada par EN/ES traducido |
| `markup_mismatch.jsonl` | Entradas donde los codigos de color no se conservaron |
| `rules_debug.jsonl` | Debug del motor de reglas locales |

---

## Generar distribucion (`build.py`)

Genera un ZIP listo para distribuir que incluye Python embebido (el usuario final no necesita Python instalado):

```bash
python build.py              # version "dev"
python build.py --version 1.0.0
```

El resultado queda en `dist/DF-Lore-Translator-vX.X.X.zip`.

---

## Estructura del proyecto

```
df-traductor/
├── df-lore-translator.bat        ← panel de control principal
├── start-server.bat              ← arranca solo el servidor
├── start-watcher.bat             ← arranca solo el watcher
├── start-admin.bat               ← panel de administracion web
├── deploy.py                     ← despliega scripts Lua a DFHack
├── manage.py                     ← gestion de la cache SQLite
├── build.py                      ← genera distribucion ZIP
├── .env.example                  ← plantilla de configuracion
├── backend/
│   ├── config.yaml               ← ajustes tecnicos
│   ├── requirements.txt          ← dependencias Python
│   ├── glossary.txt              ← terminos forzados para DeepL
│   ├── api/app.py                ← servidor HTTP de traduccion (puerto 5100)
│   ├── watcher/                  ← lector de gamelog.txt
│   ├── visualizer/               ← modos de visualizacion (console / overlay)
│   ├── translator/               ← motores (DeepL, Google, Azure)
│   ├── rules/                    ← reglas locales sin llamada a API
│   ├── admin/                    ← panel de administracion web (puerto 5200)
│   ├── cache/                    ← base de datos SQLite (generada)
│   └── logs/                     ← logs diarios (generados)
└── mod/
    ├── dfhack-config/scripts/    ← scripts Lua para DFHack
    │   ├── nombres-espanoles.lua ←   asigna nombres españoles a enanos/sitios
    │   └── exportar_enano.lua    ←   boton E en la ficha del enano
    └── mods/NombresEspanol/      ← mod DF para traducir el diccionario del juego
        ├── start.bat             ←   arranca la interfaz del mod
        ├── translator.py         ←   motor de traduccion del mod
        └── objects/language_words.txt  ← diccionario traducido
```
