#Requires -Version 5.1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = 'DF-Lore-Translator'

$script:Root       = $PSScriptRoot
$script:EnvFile    = Join-Path $script:Root '.env'
$script:ConfigFile = Join-Path $script:Root 'backend\config.yaml'

# Modo distribución (python/ embebido) o modo dev (venv/)
$_distPy = Join-Path $script:Root 'python\python.exe'
$_devPy  = Join-Path $script:Root 'venv\Scripts\python.exe'
if     (Test-Path $_distPy) { $script:VenvPy = $_distPy; $script:DistMode = $true  }
elseif (Test-Path $_devPy)  { $script:VenvPy = $_devPy;  $script:DistMode = $false }
else                         { $script:VenvPy = $null;    $script:DistMode = $false }

# --- Utilidades ---

function Load-Env {
    if (-not (Test-Path $script:EnvFile)) { return }
    foreach ($raw in (Get-Content $script:EnvFile -Encoding UTF8)) {
        $line = $raw.Trim()
        if ($line -and -not $line.StartsWith('#') -and $line.Contains('=')) {
            $idx = $line.IndexOf('=')
            $key = $line.Substring(0, $idx).Trim()
            $val = $line.Substring($idx + 1).Trim()
            [Environment]::SetEnvironmentVariable($key, $val, 'Process')
        }
    }
}

function Set-EnvValue {
    param([string]$Key, [string]$Value)
    $lines = [System.IO.File]::ReadAllLines($script:EnvFile)
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match "^$Key=") { $lines[$i] = "$Key=$Value" }
    }
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllLines($script:EnvFile, $lines, $utf8)
    [Environment]::SetEnvironmentVariable($Key, $Value, 'Process')
}

function Get-ServiceStatus {
    $procs = Get-Process cmd -ErrorAction SilentlyContinue
    $sv = $false
    $wt = $false
    if ($procs) {
        foreach ($p in $procs) {
            if ($p.MainWindowTitle -eq 'DFLT-Server')  { $sv = $true }
            if ($p.MainWindowTitle -eq 'DFLT-Watcher') { $wt = $true }
        }
    }
    return @{ Server = $sv; Watcher = $wt }
}

function Get-DisplayMode {
    if (-not (Test-Path $script:ConfigFile)) { return 'console' }
    $lines = Get-Content $script:ConfigFile -Encoding UTF8
    $inDisplay = $false
    foreach ($line in $lines) {
        if ($line -match '^display:')                          { $inDisplay = $true; continue }
        if ($inDisplay -and $line -match '^\s{2}mode:\s*(\S+)') { return $Matches[1] }
        if ($inDisplay -and $line -match '^\S')                { break }
    }
    return 'console'
}

function Set-DisplayMode {
    param([string]$Mode)
    $lines = Get-Content $script:ConfigFile -Encoding UTF8
    $inDisplay = $false
    $newLines = for ($i = 0; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        if ($line -match '^display:')     { $inDisplay = $true }
        elseif ($line -match '^\S')       { $inDisplay = $false }

        if ($inDisplay -and $line -match '^\s{2}mode:\s*\S+') {
            $line -replace '(^\s{2}mode:\s*)\S+', "`${1}$Mode"
        } else {
            $line
        }
    }
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllLines($script:ConfigFile, $newLines, $utf8)
}

function Wait-Key {
    param([string]$Msg = 'Pulsa cualquier tecla...')
    Write-Host ''
    Write-Host "    $Msg" -ForegroundColor DarkGray
    $null = [Console]::ReadKey($true)
}

# --- Cabecera ---

function Show-Header {
    $s = Get-ServiceStatus
    $engine = $env:TRANSLATION_ENGINE
    if (-not $engine) { $engine = 'deepl' }
    $beepRaw = $env:BEEP_ENABLED
    if (-not $beepRaw) { $beepRaw = 'true' }
    $beep = 'activado'
    if ($beepRaw -eq 'false') { $beep = 'desactivado' }
    $displayMode = Get-DisplayMode

    $markupRaw = $env:SHOW_MARKUP_WARNINGS
    if (-not $markupRaw) { $markupRaw = 'false' }
    $markupDisp = 'ocultos'
    if ($markupRaw -eq 'true') { $markupDisp = 'visibles' }

    Clear-Host
    Write-Host ''
    Write-Host '   ====================================================' -ForegroundColor DarkCyan
    Write-Host '          DF-Lore-Translator  -  Panel de Control'            -ForegroundColor Cyan
    Write-Host '   ====================================================' -ForegroundColor DarkCyan
    Write-Host ''
    Write-Host '    Motor: '      -NoNewline -ForegroundColor Gray
    Write-Host $engine            -NoNewline -ForegroundColor Yellow
    Write-Host '     Pitido: '    -NoNewline -ForegroundColor Gray
    Write-Host $beep              -NoNewline -ForegroundColor Yellow
    Write-Host '     Visual: '    -NoNewline -ForegroundColor Gray
    Write-Host $displayMode       -ForegroundColor Yellow
    Write-Host '    Avisos: '     -NoNewline -ForegroundColor Gray
    Write-Host $markupDisp        -ForegroundColor Yellow

    Write-Host '    Servidor: ' -NoNewline -ForegroundColor Gray
    if ($s.Server) {
        Write-Host '* activo'   -NoNewline -ForegroundColor Green
    } else {
        Write-Host 'o detenido' -NoNewline -ForegroundColor DarkGray
    }
    Write-Host '      Watcher: ' -NoNewline -ForegroundColor Gray
    if ($s.Watcher) {
        Write-Host '* activo'   -ForegroundColor Green
    } else {
        Write-Host 'o detenido' -ForegroundColor DarkGray
    }

    Write-Host ''
    Write-Host '   ----------------------------------------------------' -ForegroundColor DarkCyan
}

# --- Menu interactivo con flechas ---

function Show-Menu {
    param(
        [string[]]$Items,
        [int]$Default = 0
    )

    [Console]::CursorVisible = $false
    $sel = $Default
    $w = [Console]::WindowWidth - 1

    # Pre-reserva espacio para evitar scroll al redibujar
    $totalLines = $Items.Count + 3
    for ($j = 0; $j -lt $totalLines; $j++) { Write-Host '' }
    $startY = [Console]::CursorTop - $totalLines

    try {
        while ($true) {
            [Console]::SetCursorPosition(0, $startY)

            Write-Host (' '.PadRight($w)) -ForegroundColor Gray
            for ($i = 0; $i -lt $Items.Count; $i++) {
                if ($i -eq $sel) {
                    $line = '    > ' + $Items[$i]
                    Write-Host $line.PadRight($w) -ForegroundColor White
                } else {
                    $line = '      ' + $Items[$i]
                    Write-Host $line.PadRight($w) -ForegroundColor Gray
                }
            }
            Write-Host (' '.PadRight($w)) -ForegroundColor Gray
            $help = '    Flechas: mover   Enter: seleccionar   Esc: volver'
            Write-Host $help.PadRight($w) -ForegroundColor DarkGray

            $key = [Console]::ReadKey($true)

            switch ($key.Key) {
                'UpArrow'   { $sel = ($sel - 1 + $Items.Count) % $Items.Count }
                'DownArrow' { $sel = ($sel + 1) % $Items.Count }
                'Enter'     { return $sel }
                'Escape'    { return -1 }
            }
        }
    } finally {
        [Console]::CursorVisible = $true
    }
}

# --- Acciones ---

function Start-All {
    Show-Header
    Write-Host ''
    Write-Host '    Arrancando servidor de traduccion...' -ForegroundColor Yellow

    if ($script:DistMode) {
        $py = $script:VenvPy
        $serverCmd  = 'title DFLT-Server  & cd /d "{0}\backend" & "{1}" api/app.py' -f $script:Root, $py
        $watcherCmd = 'title DFLT-Watcher & cd /d "{0}\backend" & "{1}" watcher/gamelog_watcher.py' -f $script:Root, $py
    } else {
        $serverCmd  = 'title DFLT-Server  & cd /d "{0}" & call venv\Scripts\activate.bat & cd backend & python api/app.py' -f $script:Root
        $watcherCmd = 'title DFLT-Watcher & cd /d "{0}" & call venv\Scripts\activate.bat & cd backend & python watcher/gamelog_watcher.py' -f $script:Root
    }

    Start-Process cmd -ArgumentList '/k', $serverCmd

    Write-Host '    Esperando 3 segundos...' -ForegroundColor DarkGray
    Start-Sleep -Seconds 3

    Write-Host '    Arrancando watcher del gamelog...' -ForegroundColor Yellow
    Start-Process cmd -ArgumentList '/k', $watcherCmd

    Write-Host ''
    Write-Host '    OK - Servidor y watcher arrancados.' -ForegroundColor Green
    Write-Host ''
    Write-Host '    Para detenerlos: cierra las ventanas que se han abierto.' -ForegroundColor DarkGray
    Wait-Key
}

function Stop-All {
    Show-Header
    Write-Host ''
    Write-Host '    Deteniendo procesos...' -ForegroundColor Yellow

    $found = $false
    $procs = Get-Process cmd -ErrorAction SilentlyContinue
    if ($procs) {
        foreach ($p in $procs) {
            if ($p.MainWindowTitle -match '^DFT-') {
                $found = $true
                $null = & taskkill /PID $p.Id /T /F 2>&1
            }
        }
    }

    if ($found) {
        Write-Host '    OK - Procesos detenidos.' -ForegroundColor Green
    } else {
        Write-Host '    No hay procesos activos.' -ForegroundColor DarkGray
    }
    Wait-Key
}

function Deploy-Menu {
    $dfPath = $env:DF_INSTALL_PATH
    if (-not $dfPath) {
        Show-Header
        Write-Host ''
        Write-Host '    DF_INSTALL_PATH no esta configurado en .env' -ForegroundColor Red
        Wait-Key
        return
    }

    Show-Header
    Write-Host ''
    Write-Host '    Ruta de DF: ' -NoNewline -ForegroundColor Gray
    Write-Host $dfPath -ForegroundColor Yellow

    $items = @(
        'Enlace simbolico (recomendado; cambios instantaneos)'
        'Copiar archivos'
        'Volver'
    )
    $c = Show-Menu -Items $items

    if ($c -eq 0) {
        Write-Host ''
        & $script:VenvPy (Join-Path $script:Root 'deploy.py')
        Wait-Key
    } elseif ($c -eq 1) {
        Write-Host ''
        & $script:VenvPy (Join-Path $script:Root 'deploy.py') '--copy'
        Wait-Key
    }
}

function Clean-Cache {
    Show-Header
    Write-Host ''

    $dbPath = Join-Path $script:Root 'backend\cache\translations.db'

    if (-not (Test-Path $dbPath)) {
        Write-Host '    No se encontro la base de datos de traducciones.' -ForegroundColor DarkGray
        Write-Host '    (Se crea automaticamente al traducir por primera vez.)' -ForegroundColor DarkGray
        Wait-Key
        return
    }

    $size = [math]::Round((Get-Item $dbPath).Length / 1KB, 1)
    Write-Host '    Base de datos: ' -NoNewline -ForegroundColor Gray
    Write-Host "$dbPath  ($size KB)" -ForegroundColor Yellow
    Write-Host ''
    Write-Host '    Se eliminaran las traducciones generadas automaticamente.' -ForegroundColor Gray
    Write-Host '    Las entradas editadas manualmente se conservan.' -ForegroundColor DarkGray
    Write-Host ''

    $items = @('Limpiar traducciones automaticas', 'Cancelar')
    $c = Show-Menu -Items $items
    if ($c -ne 0) { return }

    Write-Host ''
    Write-Host '    Limpiando...' -ForegroundColor DarkGray

    $tmpPy = [System.IO.Path]::GetTempFileName() + '.py'
    @"
import sqlite3
conn = sqlite3.connect(r'$dbPath')
cur  = conn.cursor()
cur.execute('SELECT COUNT(*) FROM translations WHERE is_edited = 0')
n = cur.fetchone()[0]
cur.execute('DELETE FROM translations WHERE is_edited = 0')
conn.commit()
conn.close()
print(n)
"@ | Out-File -FilePath $tmpPy -Encoding utf8

    $result = & $script:VenvPy $tmpPy 2>&1
    Remove-Item $tmpPy -ErrorAction SilentlyContinue

    $deleted = ($result | Select-Object -Last 1).ToString().Trim()
    Write-Host "    OK - $deleted traducciones eliminadas." -ForegroundColor Green
    Wait-Key
}

function Config-Menu {
    while ($true) {
        Show-Header

        $items = @(
            'Cambiar motor de traduccion'
            'Cambiar visualizador  (consola / overlay)'
            'Activar/desactivar pitido  (solo modo consola)'
            'Activar/desactivar avisos de markup'
            'Limpiar cache de traducciones'
            'Volver'
        )
        $c = Show-Menu -Items $items

        switch ($c) {
            0 { Config-Engine }
            1 { Config-Visualizer }
            2 { Config-Beep }
            3 { Config-Markup }
            4 { Clean-Cache }
            default { return }
        }
    }
}

function Config-Visualizer {
    Show-Header
    Write-Host ''
    $cur = Get-DisplayMode
    Write-Host '    Visualizador actual: ' -NoNewline -ForegroundColor Gray
    Write-Host $cur -ForegroundColor Yellow
    Write-Host ''

    $names = @(
        'console  -  texto en esta ventana de consola'
        'overlay  -  ventana flotante transparente sobre el juego'
        'Volver'
    )
    $values = @('console', 'overlay')
    $defIdx = [Array]::IndexOf($values, $cur)
    if ($defIdx -lt 0) { $defIdx = 0 }

    $c = Show-Menu -Items $names -Default $defIdx

    if ($c -ge 0 -and $c -lt $values.Count) {
        Set-DisplayMode $values[$c]
        Write-Host ''
        Write-Host ('    OK - Visualizador cambiado a: ' + $values[$c]) -ForegroundColor Green
        if ($values[$c] -eq 'overlay') {
            Write-Host ''
            Write-Host '    Para personalizar la ventana overlay edita:' -ForegroundColor DarkGray
            Write-Host '      backend\config.yaml  (seccion display.overlay)' -ForegroundColor White
            Write-Host ''
            Write-Host '    Opciones disponibles:' -ForegroundColor DarkGray
            Write-Host '      x, y             posicion en pantalla (pixeles)' -ForegroundColor DarkGray
            Write-Host '      width, height    tamano de la ventana' -ForegroundColor DarkGray
            Write-Host '      opacity          transparencia  (0.0 - 1.0)' -ForegroundColor DarkGray
            Write-Host '      font_size        tamano de fuente' -ForegroundColor DarkGray
            Write-Host '      font_family      familia de fuente' -ForegroundColor DarkGray
            Write-Host '      background_color color de fondo  (#RRGGBB)' -ForegroundColor DarkGray
            Write-Host '      max_messages     mensajes visibles a la vez' -ForegroundColor DarkGray
            Write-Host '      fade_seconds     segundos hasta desvanecerse (0=nunca)' -ForegroundColor DarkGray
        }
        Write-Host ''
        Write-Host '    Reinicia el watcher para que surta efecto.' -ForegroundColor DarkGray
        Wait-Key
    }
}

function Config-Engine {
    Show-Header
    Write-Host ''
    $cur = $env:TRANSLATION_ENGINE
    if (-not $cur) { $cur = 'deepl' }
    Write-Host '    Motor actual: ' -NoNewline -ForegroundColor Gray
    Write-Host $cur -ForegroundColor Yellow

    $names = @(
        'deepl   (recomendado; soporta glosario)'
        'google  (Google Cloud Translation)'
        'azure   (Azure Cognitive Services)'
        'Volver'
    )
    $values = @('deepl', 'google', 'azure')

    $defIdx = [Array]::IndexOf($values, $cur)
    if ($defIdx -lt 0) { $defIdx = 0 }

    $c = Show-Menu -Items $names -Default $defIdx

    if ($c -ge 0 -and $c -lt 3) {
        Set-EnvValue 'TRANSLATION_ENGINE' $values[$c]
        Write-Host ''
        Write-Host ('    OK - Motor cambiado a: ' + $values[$c]) -ForegroundColor Green
        Write-Host '      Reinicia el servidor para que surta efecto.' -ForegroundColor DarkGray
        Wait-Key
    }
}

function Config-Beep {
    $cur = $env:BEEP_ENABLED
    if ($cur -eq 'false') { $new = 'true' } else { $new = 'false' }
    if ($new -eq 'true') { $disp = 'activado' } else { $disp = 'desactivado' }

    Set-EnvValue 'BEEP_ENABLED' $new

    Show-Header
    Write-Host ''
    Write-Host "    OK - Pitido: $disp" -ForegroundColor Green
    Write-Host '      Reinicia el watcher para que surta efecto.' -ForegroundColor DarkGray
    Wait-Key
}

function Config-Markup {
    $cur = $env:SHOW_MARKUP_WARNINGS
    if (-not $cur) { $cur = 'false' }
    if ($cur -eq 'false') { $new = 'true' } else { $new = 'false' }
    if ($new -eq 'true') { $disp = 'visibles' } else { $disp = 'ocultos' }

    Set-EnvValue 'SHOW_MARKUP_WARNINGS' $new

    Show-Header
    Write-Host ''
    Write-Host "    OK - Avisos de tokens: $disp" -ForegroundColor Green
    Write-Host '      Reinicia el watcher para que surta efecto.' -ForegroundColor DarkGray
    Wait-Key
}

# --- Punto de entrada ---

if (-not $script:VenvPy -or -not (Test-Path $script:VenvPy)) {
    Write-Host ''
    Write-Host '   No se encontro Python.' -ForegroundColor Red
    Write-Host ''
    Write-Host '   Opcion A — distribucion (sin instalar nada):' -ForegroundColor Gray
    Write-Host '     Descarga el ZIP desde los Releases de GitHub y ejecuta desde ahi.' -ForegroundColor White
    Write-Host ''
    Write-Host '   Opcion B — entorno de desarrollo:' -ForegroundColor Gray
    Write-Host '     python -m venv venv' -ForegroundColor White
    Write-Host '     venv\Scripts\pip install -r backend\requirements.txt' -ForegroundColor White
    Wait-Key 'Pulsa cualquier tecla para salir...'
    exit 1
}

if (-not (Test-Path $script:EnvFile)) {
    Write-Host ''
    Write-Host '   No se encontro .env' -ForegroundColor Red
    Write-Host '   Copia la plantilla:  copy .env.example .env' -ForegroundColor Gray
    Wait-Key 'Pulsa cualquier tecla para salir...'
    exit 1
}

Load-Env

while ($true) {
    Show-Header

    $mainItems = @(
        'Arrancar servidor + watcher'
        'Desplegar scripts Lua a DFHack'
        'Configuracion'
        'Salir'
    )
    $choice = Show-Menu -Items $mainItems

    switch ($choice) {
        0 { Start-All }
        1 { Deploy-Menu }
        2 { Config-Menu }
        default { exit 0 }
    }
}
