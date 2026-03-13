# Fase 1 — Lector de gamelog y backend de traducción modular

> **Objetivo de esta fase:** Leer en tiempo real el archivo `gamelog.txt` que genera Dwarf Fortress, enviar cada línea nueva a un servicio de traducción local, y mostrar el resultado. Todo sin tocar DFHack todavía. Al terminar esta fase tendrás el motor de traducción estable y probado, listo para ser conectado al juego en fases posteriores.

---

## Visión general del sistema

El sistema se divide en dos piezas independientes que se comunican entre sí:

**1. El Watcher** — un script Python que vigila `gamelog.txt` y detecta líneas nuevas en tiempo real, de la misma manera que el comando `tail -f` en Linux. Cuando detecta texto nuevo, lo envía al servicio de traducción y muestra el resultado.

**2. El Translation Service** — una pequeña API HTTP local (un servidor que escucha en tu propia máquina) que recibe texto en inglés y devuelve texto en español. Por dentro, este servicio puede usar distintos motores de traducción (Ollama, DeepL, LibreTranslate, etc.) y cambiar entre ellos sin que el Watcher lo note.

```
gamelog.txt  ──►  Watcher (Python)  ──►  POST /translate  ──►  Translation Service
                                                                       │
                                                            ┌──────────▼──────────┐
                                                            │  Motor activo        │
                                                            │  (config.yaml)       │
                                                            │                      │
                                                            │  • Ollama (local)    │
                                                            │  • LibreTranslate    │
                                                            │  • DeepL             │
                                                            │  • Google Translate  │
                                                            └─────────────────────┘
```

La separación es deliberada: si mañana quieres cambiar de Ollama a DeepL porque se te acabó el límite gratuito, solo cambias una línea en un archivo de configuración. El Watcher no sabe ni le importa qué hay detrás.

---

## Estructura del repositorio completo

El repositorio está pensado desde el principio para acoger las fases futuras sin necesidad de reorganizar nada. Aunque en esta fase solo desarrollamos el `backend`, la carpeta `mod` ya existe vacía para los scripts de DFHack que vendrán después.

```
df-traductor/                            ← raíz del repositorio Git
│
├── backend/                             ← todo el código Python (esta fase)
│   ├── watcher/
│   │   └── gamelog_watcher.py           # Detecta líneas nuevas en gamelog.txt
│   │
│   ├── translator/
│   │   ├── base.py                      # Clase abstracta común a todos los motores
│   │   ├── ollama_translator.py         # Motor: Ollama (local, sin límites)
│   │   ├── libretranslate.py            # Motor: LibreTranslate (self-hosted o nube)
│   │   ├── deepl_translator.py          # Motor: DeepL (API de pago con tier gratuito)
│   │   └── factory.py                   # Lee config.yaml y devuelve el motor correcto
│   │
│   ├── api/
│   │   └── app.py                       # Servidor HTTP con el endpoint POST /translate
│   │
│   ├── config.yaml                      # Configuración activa (qué motor usar, parámetros)
│   └── requirements.txt                 # Dependencias Python del proyecto
│
├── mod/                                 ← scripts Lua para DFHack (fases futuras)
│   └── scripts/
│       └── .gitkeep                     # carpeta vacía por ahora, no borrar
│
├── docs/                                ← documentación del proyecto
│   └── FASE1-gamelog-translator.md      # este documento
│
└── deploy.py                            # conecta mod/ con la carpeta del juego (ver abajo)
```

---

## Dónde van los archivos en el juego y cómo conectarlos al repo

> Aunque esta fase no tiene scripts Lua, conviene entender esto ahora para no tener que mover archivos más adelante.

Los scripts de Lua que DFHack ejecuta **no se compilan**: DFHack los lee directamente desde el disco. Esto significa que hay que tenerlos en una carpeta concreta dentro de la instalación del juego. La carpeta correcta para desarrollo propio es:

```
[carpeta de instalación de Dwarf Fortress]/
└── dfhack-config/
    └── scripts/          ← aquí van los .lua del mod
```

Esta carpeta está pensada para scripts de usuario y no se sobreescribe al actualizar DFHack ni interfiere con los scripts oficiales.

Para no tener dos copias del código (una en el repo y otra en el juego), se usa un **enlace simbólico**: un acceso directo del sistema operativo que hace que la carpeta del juego apunte directamente a `mod/scripts/` dentro del repo. De esta manera, al editar un archivo en el repo, el juego ve el cambio al instante sin necesidad de copiar nada.

El archivo `deploy.py` en la raíz del repo se encarga de crear este enlace de forma automática. Solo hay que ejecutarlo una vez, después de clonar el repo. Requiere que Dwarf Fortress esté instalado y que se configure la ruta en `config.yaml`.

Si por algún motivo no se pueden usar enlaces simbólicos (permisos, limitaciones del sistema), `deploy.py` puede funcionar también en modo copia manual: copia los archivos de `mod/scripts/` a la carpeta del juego. En ese modo hay que ejecutarlo cada vez que se modifique un script Lua.

### Rutas habituales de instalación de Dwarf Fortress

| Sistema operativo | Ruta típica |
|---|---|
| Windows (Steam) | `C:\Program Files (x86)\Steam\steamapps\common\Dwarf Fortress` |
| Windows (manual) | `C:\Dwarf Fortress\` |
| Linux (Steam) | `~/.steam/steam/steamapps/common/Dwarf Fortress` |
| Linux (manual) | `~/.local/share/df_linux/` |
| macOS | `~/Library/Application Support/Steam/steamapps/common/Dwarf Fortress` |

La ruta se configura en `config.yaml` bajo la clave `df_install_path` para que `deploy.py` la use automáticamente.

---

## Pieza 1 — El Watcher de gamelog.txt

### Qué hace

Dwarf Fortress escribe todas las notificaciones del juego (ataques, muertes, eventos, anuncios) en un archivo de texto plano llamado `gamelog.txt`, ubicado en la carpeta raíz de la instalación del juego. Este archivo crece continuamente mientras juegas.

El Watcher abre ese archivo, salta al final (para ignorar el historial anterior), y entra en un bucle donde comprueba si han llegado líneas nuevas cada cierto intervalo (por ejemplo, cada 0.5 segundos). Cuando detecta una línea nueva, la manda al Translation Service y muestra el resultado en pantalla.

### Comportamiento esperado

- Arranca y no hace nada hasta que DF empiece a escribir.
- Cada vez que aparece una línea nueva en `gamelog.txt`, la traduce y la imprime en consola con el texto original y su traducción.
- Si el Translation Service no está disponible, el Watcher debe avisar con un mensaje claro y seguir intentándolo, en lugar de cerrarse con un error.
- Si DF se cierra y el archivo deja de crecer, el Watcher simplemente espera sin consumir recursos significativos.

### Parámetros configurables

Desde `config.yaml` se debe poder ajustar:
- La ruta al `gamelog.txt` (varía según sistema operativo y dónde instalaste DF).
- El intervalo de polling en segundos (cuánto espera entre comprobaciones).
- La URL del Translation Service (por defecto `http://localhost:5100`).

---

## Pieza 2 — El Translation Service

### Qué hace

Es un servidor HTTP minimalista que expone un único endpoint:

```
POST /translate
Content-Type: application/json

{ "text": "The goblin has been struck down!", "target": "es" }
```

Respuesta:
```json
{ "translated": "¡El goblin ha sido abatido!", "engine": "ollama" }
```

El campo `engine` en la respuesta es útil para saber qué motor está traduciendo en cada momento, especialmente durante pruebas.

### El contrato común (la clase base)

Todos los motores de traducción deben implementar el mismo contrato: reciben un texto y un idioma destino, y devuelven el texto traducido. Este contrato se define como una clase abstracta en Python.

Esto significa que `factory.py` puede devolver cualquier motor y el resto del código no necesita saber cuál es: siempre llama al mismo método de la misma manera.

### Motores disponibles y cómo elegirlos

El motor activo se define en `config.yaml` con una clave simple, por ejemplo `engine: ollama`. El archivo `factory.py` lee esa clave y devuelve la instancia correcta. No hay que tocar código para cambiar de motor.

---

## Motores de traducción — Descripción de cada uno

### Ollama (recomendado para empezar)

**Qué es:** Ollama es una herramienta que permite ejecutar modelos de lenguaje (LLMs) en tu propia máquina, sin conexión a internet y sin límites de uso. Si ya tienes Ollama instalado para otro proyecto (Story Engine, por ejemplo), puedes reutilizarlo directamente.

**Cómo funciona la traducción:** Se le envía un prompt al modelo pidiéndole que traduzca el texto, y se parsea su respuesta. Es el motor más flexible porque el prompt es configurable, pero puede ser más lento que APIs especializadas en traducción.

**Cuándo usarlo:** Siempre que quieras cero costes, privacidad total, y no te importe que la traducción tarde entre 1 y 5 segundos por línea dependiendo del modelo y tu hardware.

**Parámetros en config.yaml:**
- `ollama_url`: dirección del servidor Ollama (por defecto `http://localhost:11434`)
- `ollama_model`: el modelo a usar (por ejemplo `llama3`, `mistral`, `phi3`)
- `ollama_prompt_template`: el prompt que se manda al modelo, con un placeholder `{text}` donde va el texto a traducir

---

### LibreTranslate (alternativa gratuita self-hosted)

**Qué es:** LibreTranslate es un servicio de traducción de código abierto que puedes ejecutar tú mismo en local (via Docker) o usar instancias públicas gratuitas mantenidas por la comunidad.

**Ventaja frente a Ollama:** Es un motor especializado en traducción, así que es más rápido y consistente. No usa un LLM genérico, sino modelos entrenados específicamente para traducir.

**Cuándo usarlo:** Cuando quieras rapidez sin pagar, o cuando Ollama sea demasiado lento en tu máquina.

**Parámetros en config.yaml:**
- `libretranslate_url`: URL de la instancia (local o pública)
- `libretranslate_api_key`: clave API si la instancia lo requiere (las públicas gratuitas suelen no necesitarla o tienen una clave pública conocida)

---

### DeepL

**Qué es:** Uno de los mejores servicios de traducción automática disponibles. Tiene un tier gratuito con un límite mensual de caracteres (500.000 caracteres/mes a fecha de 2024, suficiente para uso moderado).

**Cuándo usarlo:** Cuando quieras la máxima calidad de traducción y puedas asumir el límite mensual o pagar el plan Pro.

**Parámetros en config.yaml:**
- `deepl_api_key`: la clave que obtienes al registrarte en deepl.com

---

### Google Translate / otros

Se pueden añadir motores adicionales siguiendo el mismo patrón: crear un archivo nuevo en `translator/`, implementar el contrato de la clase base, y añadir la entrada correspondiente en `factory.py` y `config.yaml`. El sistema está diseñado para crecer sin modificar el código existente.

---

## El archivo config.yaml — Estructura completa

```yaml
# Motor de traducción activo
# Valores posibles: ollama | libretranslate | deepl
engine: ollama

# Ruta de instalación de Dwarf Fortress
# deploy.py la usa para crear el enlace simbólico de mod/scripts/ → dfhack-config/scripts/
df_install_path: "C:/Program Files (x86)/Steam/steamapps/common/Dwarf Fortress"   # Windows
# df_install_path: "~/.steam/steam/steamapps/common/Dwarf Fortress"               # Linux

# Configuración del Watcher
watcher:
  # gamelog.txt está siempre en la raíz de la instalación del juego
  # deploy.py puede calcular esta ruta automáticamente a partir de df_install_path
  gamelog_path: "C:/Program Files (x86)/Steam/steamapps/common/Dwarf Fortress/gamelog.txt"
  poll_interval_seconds: 0.5
  translation_service_url: "http://localhost:5100"

# Configuración de Ollama
ollama:
  url: "http://localhost:11434"
  model: "llama3"
  prompt_template: "Translate the following English text to Spanish. Return only the translated text, no explanations:\n\n{text}"

# Configuración de LibreTranslate
libretranslate:
  url: "http://localhost:5000"
  api_key: ""

# Configuración de DeepL
deepl:
  api_key: "TU_CLAVE_AQUI"
```

---

## Flujo completo de una traducción

Para que quede claro de extremo a extremo, esto es lo que ocurre cuando DF escribe una línea nueva:

1. Dwarf Fortress escribe `"A goblin has been slain by Urist McAxedwarf."` en `gamelog.txt`.
2. El Watcher detecta la línea nueva en su siguiente ciclo de polling.
3. El Watcher hace una petición HTTP POST a `http://localhost:5100/translate` con el texto.
4. El Translation Service recibe la petición y consulta `config.yaml` para saber qué motor está activo.
5. El motor activo (por ejemplo Ollama) procesa el texto y devuelve la traducción.
6. El Translation Service responde al Watcher con `{ "translated": "Un goblin ha sido matado por Urist McAxedwarf.", "engine": "ollama" }`.
7. El Watcher imprime en pantalla el original y la traducción.

---

## Requisitos técnicos

### Python
- Versión 3.10 o superior.
- Dependencias principales: `flask` (para el servidor HTTP), `requests` (para las llamadas HTTP del Watcher), `pyyaml` (para leer el archivo de configuración).
- Dependencias opcionales según el motor: `deepl` (SDK oficial de DeepL).

### Ollama (si se usa ese motor)
- Ollama debe estar instalado y ejecutándose antes de arrancar el Translation Service.
- El modelo especificado en `config.yaml` debe estar descargado (`ollama pull nombre-del-modelo`).

### Para ejecutar el sistema completo
Se necesitan **dos terminales** abiertas simultáneamente:
1. Una ejecutando el Translation Service (`python api/app.py`)
2. Otra ejecutando el Watcher (`python watcher/gamelog_watcher.py`)

El orden importa: primero arranca el Translation Service, luego el Watcher.

---

## Criterios de éxito de esta fase

Esta fase se considera completa cuando:

- [ ] El Watcher detecta líneas nuevas en `gamelog.txt` en tiempo real.
- [ ] El Translation Service responde correctamente a peticiones POST /translate.
- [ ] El motor Ollama traduce frases del juego de forma comprensible.
- [ ] Se puede cambiar de motor (por ejemplo de Ollama a LibreTranslate) modificando solo `config.yaml`, sin tocar código.
- [ ] Si el Translation Service no está disponible, el Watcher avisa y sigue en espera en lugar de crashear.
- [ ] El sistema completo puede dejarse corriendo durante una sesión de juego sin degradación.

---

## Siguiente fase (referencia futura)

Una vez esta fase esté estable, la Fase 2 consistirá en reemplazar la lectura de `gamelog.txt` por un hook directo de DFHack usando el evento `eventful.onReport`, que captura los mensajes del juego en el momento en que se generan (antes de que lleguen al log) y permite mayor control sobre qué se traduce y qué no. El Translation Service de esta fase se reutilizará sin cambios.
