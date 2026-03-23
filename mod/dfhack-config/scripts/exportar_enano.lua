--@ module = true

local overlay = require('plugins.overlay')
local widgets = require('gui.widgets')
local utils = require('utils')

-- Definimos nuestra clase Overlay
BotonExportarOverlay = defclass(BotonExportarOverlay, overlay.OverlayWidget)

BotonExportarOverlay.ATTRS = {
    desc = "Añade un botón para exportar el nombre del enano a un TXT.",
    -- Posición por defecto: x negativo significa que empieza desde la derecha de la pantalla.
    -- y = 5 significa 5 casillas desde arriba.
    default_pos = {x = -45, y = 10}, 
    default_enabled = true,
    -- Esto le dice a DFHack en qué pantallas debe aparecer nuestro botón
    viewscreens = {
        'dwarfmode/ViewSheets/UNIT', -- Pestaña principal del enano
    },
    frame = {w = 3, h = 1}, -- Ancho y alto del botón
}

function BotonExportarOverlay:init()
    -- Añadimos el botón visual
    self:addviews{
        widgets.TextButton{
            frame = {t = 0, l = 0},
            label = 'E', -- La letra que se mostrará
            text_pen = COLOR_LIGHTGREEN,
            on_click = function() self:exportar_datos() end
        }
    }
end

function BotonExportarOverlay:exportar_datos()
    local view_sheets = df.global.game.main_interface.view_sheets
    local pestaña_activa = view_sheets.active_sheet
    
    local unit = df.unit.find(view_sheets.active_id)
    local nombre = unit and dfhack.units.getReadableName(unit) or "Enano"

    local archivo = io.open("enanos_exportados.txt", "a")
    if not archivo then return end
    
    -- Cabecera minimalista para tu programa
    archivo:write(">>> " .. nombre .. "\n")
    
    -- Función para volcar vectores de forma limpia
    local function volcar_vector(vector, limite)
        if not vector or #vector == 0 then return end
        
        local inicio = 1
        -- Si ponemos un límite (como 5), calculamos desde dónde empezar a leer
        if limite and #vector > limite then
            inicio = #vector - limite + 1
        end

        for i = inicio, #vector do
            local linea = vector[i]
            local texto = type(linea) == "string" and linea or (linea.value or tostring(linea))
            
            if texto ~= "" then
                archivo:write(texto .. "\n")
            end
        end
    end

    -- Solo exportamos la pestaña que el usuario está viendo (seguridad ante crashes)
    if pestaña_activa == 0 then -- Overview / Thoughts
        -- Aquí limitamos a los 5 últimos
        volcar_vector(view_sheets.raw_thought_str, 5)
    
    elseif pestaña_activa == 1 then -- Health
        volcar_vector(view_sheets.unit_health_raw_str)
        
    elseif pestaña_activa == 4 then -- Personality
        volcar_vector(view_sheets.personality_raw_str)
        
    elseif pestaña_activa == 7 then -- Kills
        volcar_vector(view_sheets.kill_description_raw_str)
    end

    archivo:write("\n")
    archivo:close()
    
    dfhack.printerr("Exportado: " .. nombre .. " (Pestaña " .. pestaña_activa .. ")")
end

-- Registramos el widget para que el sistema de Overlay de DFHack lo reconozca
OVERLAY_WIDGETS = {
    boton_exportar = BotonExportarOverlay,
}