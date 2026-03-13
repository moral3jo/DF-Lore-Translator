# DF-Lore-Translator

Traductor de lore en tiempo real para Dwarf Fortress. Lee el log del juego, traduce cada línea al español usando DeepL (o Google/Azure) y la muestra en consola con colores.

---

## Requisitos

- Python 3.10 o superior
- Dwarf Fortress instalado (Steam o manual)
- Una clave API de DeepL, Google Translate o Azure Translator
  - DeepL con cuenta gratuita ofrece 500.000 caracteres al mes
  - Google Translate ofrece 1.000.000 caracteres al mes
  - Azure Translator ofrece 500.000 caracteres al mes

---

## Instalación

```bash
# 1. Clona el repositorio
git clone https://github.com/TU_USUARIO/df-traductor.git
cd df-traductor

# 2. Crea un entorno virtual e instala las dependencias
python -m venv venv
venv\Scripts\pip install -r backend\requirements.txt

# 3. Copia la plantilla de configuración y rellena tus datos
copy .env.example .env
```

Edita `.env` con tus valores:

```env
TRANSLATION_ENGINE=deepl
DF_INSTALL_PATH=D:/SteamLibrary/steamapps/common/Dwarf Fortress
DEEPL_API_KEY=tu-clave-aqui
```

> **Nota:** Solo necesitas rellenar la clave API del motor que vayas a usar.

---

## Arranque rápido — Panel de Control

Haz doble clic en **`df-lore-translator.bat`** para abrir el panel de control:

```
====================================================
       DF-Lore-Translator  -  Panel de Control
====================================================

  Motor: deepl     Pitido: activado     Visual: console
  Servidor: o detenido      Watcher: o detenido

----------------------------------------------------

  > Arrancar servidor + watcher
    Parar todo
    Desplegar scripts Lua a DFHack
    Configuracion
    Salir
```

Desde aquí puedes:

- **Arrancar y parar** el servidor y el watcher con una sola opción
- **Desplegar los scripts Lua** a la carpeta de DFHack (enlace simbólico o copia)
- **Cambiar la configuración** (motor de traducción, visualizador, pitido en consola)

### Arranque manual (alternativa)

Si prefieres arrancar los servicios por separado, usa los `.bat` individuales o la línea de comandos:

**Terminal 1:**
```bash
cd backend
python api/app.py
```

**Terminal 2:**
```bash
cd backend
python watcher/gamelog_watcher.py
```

---

## Configuración

### Variables de entorno (`.env`)

| Variable | Descripción | Valores |
|---|---|---|
| `TRANSLATION_ENGINE` | Motor de traducción activo | `deepl` / `google` / `azure` |
| `DF_INSTALL_PATH` | Ruta de instalación de Dwarf Fortress | Ruta absoluta |
| `DEEPL_API_KEY` | Clave API de DeepL | — |
| `GOOGLE_API_KEY` | Clave API de Google Translate | — |
| `AZURE_API_KEY` | Clave API de Azure Translator | — |
| `AZURE_REGION` | Región de Azure | `westeurope`, etc. |
| `BEEP_ENABLED` | Pitido en consola al traducir | `true` / `false` |

### Ajustes técnicos (`backend/config.yaml`)

El archivo `config.yaml` contiene ajustes técnicos y la configuración del visualizador:

- `watcher.poll_interval_seconds` — frecuencia de lectura del log (por defecto 0.5s)
- `watcher.translation_service_url` — URL del servidor (por defecto `http://localhost:5100`)
- `cache.path` — ruta de la base de datos SQLite
- `display.mode` — modo de visualización (`console` / `overlay`)
- `display.overlay.*` — opciones de la ventana flotante (ver sección siguiente)

> Las claves API y la ruta de DF se leen primero desde `.env`. Los valores de `config.yaml` solo se usan como fallback.

---

## Visualizador

El watcher soporta dos modos de mostrar las traducciones, seleccionables desde el panel de control (**Configuración → Cambiar visualizador**) o editando `display.mode` en `config.yaml`.

### Modo `console` (por defecto)

Las traducciones aparecen en la misma ventana de consola del watcher, con los colores originales del juego convertidos a ANSI. Es el modo más sencillo y no requiere dependencias adicionales.

### Modo `overlay`

Abre una **ventana flotante transparente** sobre el juego que muestra las traducciones en tiempo real con texto contorneado para máxima legibilidad sobre cualquier fondo.

Se compone de **dos ventanas**:

| Ventana | Descripción |
|---|---|
| **Barra de control** | Tira fina encima del área de texto con dos minibotones |
| **Área de texto** | Fondo 100 % transparente, click-through (los clics pasan al juego) |

**Botones de la barra de control:**
- **`⠿`** — arrastra aquí para mover toda la overlay a otro lugar de la pantalla.
- **`▼`/`▲`** — colapsa o expande el área de texto (la barra siempre permanece visible).

La posición inicial se configura con `x`/`y` en `config.yaml`; la barra se coloca automáticamente encima del área de texto.

Para activarlo, cambia `display.mode` a `overlay` en `config.yaml` (o usa el panel de control) y reinicia el watcher. Requiere tener PyQt6 instalado (`pip install PyQt6`).

#### Las dos ventanas del modo overlay

Al arrancar en modo overlay se abren **dos ventanas**:

| Ventana | Título | Contenido |
|---|---|---|
| Consola `cmd` | `DFLT-Watcher` | Mensajes de estado, errores, avisos de markup |
| Overlay Qt | _(sin barra de título)_ | Traducciones flotando sobre el juego |

La consola cmd es necesaria para que el proceso siga vivo — **no la cierres** o el watcher se detendrá. Puedes minimizarla o moverla a un rincón; las traducciones seguirán apareciendo en el overlay.

#### Configuración del overlay

Todas las opciones se editan en `backend/config.yaml` bajo `display.overlay`. Los cambios se aplican al reiniciar el watcher.

```yaml
display:
  mode: overlay
  overlay:
    x: 10                        # píxeles desde el borde izquierdo de la pantalla
    y: 10                        # píxeles desde el borde superior
    width: 700                   # ancho de la ventana en píxeles
    height: 300                  # alto de la ventana en píxeles
    opacity: 1.0                 # 0.0 = invisible · 1.0 = sólido (el fondo siempre es transparente)
    font_size: 13                # tamaño de fuente en puntos
    font_family: "Consolas"      # cualquier fuente instalada en el sistema
    default_text_color: "#FFFFFF"  # color para texto sin markup DFHack
    outline_color: "#000000"     # color del contorno del texto
    outline_width: 2             # grosor del contorno en píxeles (1–4 recomendado)
    always_on_top: true          # mantener sobre todas las ventanas
    max_messages: 10             # máximo de mensajes visibles a la vez
    fade_seconds: 0              # segundos hasta desvanecerse (0 = permanente)
```

| Opción | Descripción |
|---|---|
| `x` / `y` | Posición de la esquina superior izquierda de la ventana |
| `width` / `height` | Tamaño de la ventana |
| `opacity` | Afecta solo al texto (el fondo es siempre transparente) |
| `font_family` | `"Consolas"`, `"Courier New"`, `"Segoe UI"`, cualquier fuente del sistema |
| `default_text_color` | Color del texto sin markup DFHack; el markup sobreescribe este color por palabras |
| `outline_color` | Color del contorno; `"#000000"` negro es lo más habitual |
| `outline_width` | `2` es sutil, `3–4` da más contraste sobre fondos claros |
| `max_messages` | Cuando se supera, el mensaje más antiguo desaparece automáticamente |
| `fade_seconds` | Con `0` los mensajes son permanentes; con `10` desaparecen solos a los 10s |

#### Posicionamiento con dos monitores

Las coordenadas `x`/`y` son absolutas respecto al escritorio virtual completo. Para colocar el overlay en el **segundo monitor**, suma la resolución horizontal del primero al valor de `x`:

```yaml
# Monitor principal: 1920 × 1080 → segundo monitor empieza en x = 1920
x: 1930
y: 10
```

Si el segundo monitor está a la izquierda o arriba del principal, usa valores negativos:

```yaml
# Segundo monitor a la izquierda (también 1920 px de ancho)
x: -1910
y: 10
```

---

## Glosario de términos (solo DeepL)

El archivo `backend/glossary.txt` permite forzar traducciones concretas para palabras que DeepL traduce mal. Formato:

```
# Comentarios con #
misses   = falla
strikes  = golpea
dwarf    = enano
dwarves  = enanos
```

**Para añadir o cambiar términos:**

1. Edita `backend/glossary.txt`
2. Reinicia el servidor (opción 2 → 1 en el panel, o reinicia `start-server.bat`)

El servidor detecta automáticamente los cambios, borra el glosario anterior en DeepL y crea uno nuevo.

---

## Despliegue de scripts Lua

Para que los scripts Lua funcionen dentro del juego, necesitan estar en la carpeta de DFHack. Usa la opción **[3]** del panel de control o ejecuta:

```bash
# Enlace simbólico (recomendado — los cambios son instantáneos)
python deploy.py

# Copiar archivos (si los symlinks no funcionan)
python deploy.py --copy
```

> El enlace simbólico requiere **modo Desarrollador activo** o ejecutar como Administrador en Windows.

---

## Caché de traducciones

Todas las traducciones se guardan en una base de datos SQLite (`backend/cache/translations.db`). Las peticiones repetidas se sirven desde caché sin coste de API.

### Editar una traducción manualmente

Abre la base de datos con cualquier cliente SQLite (por ejemplo [DB Browser for SQLite](https://sqlitebrowser.org/)) y modifica el campo `translated`. Después pon `is_edited = 1` en esa fila para que nunca sea sobreescrita ni eliminada por las limpiezas automáticas.

---

## Limpieza de caché (`manage.py`)

Desde la raíz del proyecto:

```bash
# Ver qué se eliminaría sin borrar nada (recomendado antes de limpiar)
python manage.py clean --min-uses 2 --older-than-days 30 --dry-run

# Eliminar entradas usadas menos de 2 veces Y con más de 30 días sin usarse
python manage.py clean --min-uses 2 --older-than-days 30

# Solo eliminar por antigüedad (entradas no usadas en más de 60 días)
python manage.py clean --older-than-days 60

# Solo eliminar por uso (entradas usadas menos de 3 veces)
python manage.py clean --min-uses 3
```

**Reglas:**
- Si se combinan `--min-uses` y `--older-than-days`, se eliminan solo las entradas que cumplan **ambas** condiciones.
- Las entradas con `is_edited = 1` **nunca** se eliminan, independientemente de los filtros.

---

## Logs

Los logs se generan automáticamente en `backend/logs/`:

| Archivo | Contenido |
|---|---|
| `translations_YYYY-MM-DD.log` | Log diario de auditoría con cada par EN/ES traducido |
| `markup_mismatch.jsonl` | Entradas donde los códigos de color no se conservaron correctamente |

Revísalo periódicamente para detectar traducciones malas y añadir los términos problemáticos al glosario.

---

## Estructura del proyecto

```
df-traductor/
├── .env.example              ← plantilla de variables de entorno
├── .gitignore
├── df-lore-translator.bat         ← panel de control (arrancar, parar, config)
├── start-server.bat          ← arranca solo el servidor
├── start-watcher.bat         ← arranca solo el watcher
├── deploy.py                 ← despliega scripts Lua a DFHack
├── manage.py                 ← herramienta de administración de caché
├── backend/
│   ├── config.yaml           ← ajustes técnicos
│   ├── requirements.txt      ← dependencias Python
│   ├── glossary.txt          ← términos forzados para DeepL
│   ├── translation_cache.py  ← módulo de caché SQLite
│   ├── api/app.py            ← servidor HTTP de traducción
│   ├── watcher/              ← lector de gamelog.txt
│   ├── visualizer/           ← modos de visualización
│   │   ├── base.py           ←   interfaz base
│   │   ├── console.py        ←   salida ANSI por consola
│   │   └── overlay.py        ←   ventana flotante PyQt6
│   ├── translator/           ← motores (DeepL, Google, Azure)
│   ├── rules/                ← reglas locales (sin API)
│   ├── cache/                ← base de datos SQLite (generada)
│   └── logs/                 ← logs diarios (generados)
└── mod/scripts/              ← scripts Lua para DFHack
```
