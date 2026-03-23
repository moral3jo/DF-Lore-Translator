--@ module = true
-- traductor.lua
-- Overlay para DF-Lore-Translator: añade dos botones a la ficha de personaje.
--
--   Shift+E  →  Exporta descripción física + personalidad
--   Shift+B  →  Exporta pensamientos / emociones
--
-- Los ficheros se guardan en el directorio raíz de DF:
--   df-lore-bio-<id>.txt
--   df-lore-thoughts-<id>.txt
--
-- Activar overlay:   overlay enable traductor.export_panel
-- Desactivar:        overlay disable traductor.export_panel

local overlay = require('plugins.overlay')
local widgets = require('gui.widgets')
local gui     = require('gui')

-- ============================================================
-- Utilidades
-- ============================================================

local function reformat(s)
    s = s:gsub('%[B%]', '\n')
    s = s:gsub('%[R%]', '\n')
    s = s:gsub('%[P%]', '')
    s = s:gsub('%[C:%d+:%d+:%d+%]', '')
    s = s:gsub('%[KEY:%d+%]', '')
    -- Limpiar caracteres CP437 residuales (◙ y similares)
    s = s:gsub('\226\151\153', '\n')   -- ◙ UTF-8 bytes (U+25D9)
    s = s:gsub('\226\151[\128-\191]', '')  -- otros chars del bloque Box Drawing
    s = s:gsub('\n\n+', '\n\n')
    s = s:gsub('^\n+', '')  -- quitar newlines al inicio
    return s
end

local function to_utf(s)
    return dfhack.df2utf(reformat(s))
end

local function write_file(path, lines)
    local f, err = io.open(path, 'w')
    if not f then
        dfhack.printerr('[traductor] No se pudo escribir ' .. path .. ': ' .. tostring(err))
        return false
    end
    for _, line in ipairs(lines) do
        f:write(line .. '\n')
    end
    f:close()
    return true
end

local function read_str_vector(vec)
    local out = {}
    if not vec then return out end
    for i = 0, #vec - 1 do
        local entry = vec[i]
        local s = type(entry) == 'string' and entry
               or (entry and entry.value)
        if s and s ~= '' then
            table.insert(out, to_utf(s))
        end
    end
    return out
end

-- ============================================================
-- Simulación de clics en pestañas (método de markdown.lua)
-- ============================================================

local function click_tab(screen, gps, windowSize, x_offset, y)
    gps.mouse_x = windowSize - x_offset
    gps.mouse_y = y
    gui.simulateInput(screen, '_MOUSE_L')
end

local function cargar_datos_bio()
    local gps        = df.global.gps
    local screen     = dfhack.gui.getDFViewscreen()
    local windowSize = dfhack.screen.getWindowSize()
    local is_adv     = dfhack.world.isAdventureMode()

    -- Mismo orden que markdown.lua:
    -- 1. Personality (carga personality_raw_str)
    click_tab(screen, gps, windowSize,
        is_adv and 68 or 48,
        is_adv and 13 or 11)

    -- 2. Health
    click_tab(screen, gps, windowSize,
        74,
        is_adv and 15 or 13)

    -- 3. Health/Description (carga unit_health_raw_str con descripción física)
    click_tab(screen, gps, windowSize,
        is_adv and 74 or 51,
        is_adv and 17 or 15)
end

-- ============================================================
-- Export Bio (descripción física + personalidad)
-- ============================================================

local function exportar_bio(unit)
    cargar_datos_bio()

    local vs   = df.global.game.main_interface.view_sheets
    local name = dfhack.units.getReadableName(unit)

    local lines = {}
    local function add(s) table.insert(lines, s or '') end

    add('=== FICHA DE PERSONAJE ===')
    add('Nombre: ' .. name)
    add('')

    -- Descripción física
    add('--- Descripcion ---')
    if #vs.unit_health_raw_str > 0 then
        add(to_utf(vs.unit_health_raw_str[0].value))
    else
        add('[Sin datos de descripcion]')
    end
    add('')

    -- Personalidad
    add('--- Personalidad ---')
    local pers = read_str_vector(vs.personality_raw_str)
    if #pers > 0 then
        for _, line in ipairs(pers) do add(line) end
    else
        add('[Sin datos. Visita la pestana Personality > Traits antes de exportar.]')
    end
    add('')
    add('=== FIN ===')

    local path = dfhack.getDFPath() .. '/df-lore-bio-' .. unit.id .. '.txt'
    if write_file(path, lines) then
        dfhack.print('[traductor] Bio exportada: ' .. path .. '\n')
    end
end

-- ============================================================
-- Export Thoughts (emociones + estrés)
-- ============================================================

local function exportar_thoughts(unit)
    local name = dfhack.units.getReadableName(unit)

    local lines = {}
    local function add(s) table.insert(lines, s or '') end

    add('=== PENSAMIENTOS Y ESTADO ===')
    add('Nombre: ' .. name)
    add('')

    local soul = unit.status and unit.status.current_soul
    local pers = soul and soul.personality

    -- Emociones activas
    add('--- Emociones activas ---')
    local emo_found = false
    local ok1, err1 = pcall(function()
        if pers then
            local emotions = pers.emotions
            for i = 0, #emotions - 1 do
                local e       = emotions[i]
                local thought = df.unit_thought_type[e.thought] or tostring(e.thought)
                local emotion = df.emotion_type[e.type]         or tostring(e.type)
                add('  ' .. emotion .. ' por: ' .. thought
                    .. '  (intensidad: ' .. tostring(e.strength) .. ')')
                emo_found = true
            end
        end
    end)
    if not ok1 then
        add('  [Error emociones: ' .. tostring(err1) .. ']')
    end
    if not emo_found then add('  Sin emociones registradas') end
    add('')

    -- Nivel de estrés
    local ok2, err2 = pcall(function()
        if pers then
            local stress = pers.stress
            local label
            if     stress >  200000 then label = 'Crisis'
            elseif stress >   50000 then label = 'Muy estresado'
            elseif stress >   10000 then label = 'Estresado'
            elseif stress >       0 then label = 'Algo estresado'
            elseif stress >  -10000 then label = 'Neutro'
            elseif stress >  -50000 then label = 'Contento'
            else                         label = 'Muy contento'
            end
            add('Nivel de estres: ' .. tostring(stress) .. '  (' .. label .. ')')
        end
    end)
    if not ok2 then
        add('[Error estres: ' .. tostring(err2) .. ']')
    end

    add('')
    add('=== FIN ===')

    local path = dfhack.getDFPath() .. '/df-lore-thoughts-' .. unit.id .. '.txt'
    if write_file(path, lines) then
        dfhack.print('[traductor] Thoughts exportados: ' .. path .. '\n')
    end
end

-- ============================================================
-- Overlay Widget
-- ============================================================

local ExportPanel = defclass(ExportPanel, overlay.OverlayWidget)
ExportPanel.ATTRS {
    desc            = 'Exporta bio y pensamientos de la unidad seleccionada.',
    default_pos     = {x = -30, y = 8},
    default_enabled = true,
    viewscreens     = 'dwarfmode/ViewSheets/UNIT',
    frame           = {w = 30, h = 5},
}

function ExportPanel:init()
    self:addviews{
        widgets.TextButton{
            frame       = {t = 0, l = 0, w = 28},
            label       = 'Export Bio',
            key         = 'CUSTOM_SHIFT_E',
            on_activate = function()
                local unit = dfhack.gui.getSelectedUnit()
                if unit then
                    exportar_bio(unit)
                else
                    dfhack.printerr('[traductor] Ninguna unidad seleccionada.')
                end
            end,
        },
        widgets.TextButton{
            frame       = {t = 2, l = 0, w = 28},
            label       = 'Export Thoughts',
            key         = 'CUSTOM_SHIFT_B',
            on_activate = function()
                local unit = dfhack.gui.getSelectedUnit()
                if unit then
                    exportar_thoughts(unit)
                else
                    dfhack.printerr('[traductor] Ninguna unidad seleccionada.')
                end
            end,
        },
    }
end

OVERLAY_WIDGETS = { export_panel = ExportPanel }