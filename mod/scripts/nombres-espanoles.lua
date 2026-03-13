--@ module = true
--@ enable = true
-- nombres-espanoles.lua
-- Uso: nombres-espanoles [enanos|fortaleza|sitios|todo|help] [forzar]

local utils = require('utils')
local GLOBAL_KEY = 'nombres-espanoles'
local state = state or { enabled = false }

-- ============================================================
-- DATOS: edita estas listas a tu gusto
-- ============================================================

local HOMBRES = {
    "Pablo Picasso", "Salvador Dali", "Miguel Cervantes", "Julio Iglesias", "Antonio Banderas", "Rafael Nadal", "Butragueno",
    "Fernando Alonso", "Pedro Almodovar", "Javier Bardem", "Juan Manuel Serrat", "Arturo Valls", "Bunbury",
    "David Bisbal", "Melendi", "Raphael", "Amancio Ortega", "Pedro Sanchez", "Mariano Rajoy",
    "Santiago Abascal", "Felipe Borbón", "Juan Carlos Borbón", "Andrés Iniesta", "Juan Buenafuente",
    "El Quijote", "Sancho Panza", "Iker Jimenez", "Pau Gasol", "Alejandro Sanz", "Joaquin Sabina",
    "Manolo Escobar", "Paco León", "Santiago Segura", "Gaudi", "David Broncano", "Ibai Llanos",
    "Manolo", "Paco", "Pepe", "Curro", "Quevedo", "Góngora", "Jesús Vázquez", "Carlos Alcaraz",
    "Camarón", "Bertín Osborne", "Kiko Rivera", "Karlos Arguiñano", "Matías Prats", "Chiquito de la Calzada"
}

local MUJERES = {
    "Rosalía Vila", "Penélope Cruz", "Isabel Pantoja", "Conchita", "Lola Flores", "Rocío Jurado",
    "Belén Esteban", "Ana Obregón", "Letizia Ortiz", "Díaz Ayuso", "Alexia Putellas", "Carolina Marín",
    "Mireia Belmonte", "Blanca Suárez", "Elsa Pataky", "Cristina Pedroche", "Paz Padilla",
    "Ana Rosa Quintana", "Mercedes Milá", "Susanna Griso", "Concha Velasco", "Carmen Sevilla",
    "Tamara Falcó", "Aitana Ocaña", "Mónica Naranjo", "Marta Sánchez", "Clara Campoamor",
    "Terelu Campos", "Pepa Flores", "Antonia Abad", "Olvido Gara", "Yolanda Díaz",
    "Irene Montero", "Emilia Pardo", "Rosalía de Castro", "Carmen de Mairena",
}

local PUEBLOS = {
    "Tamame", "Ledesma", "Vitigudino", "Bejar", "Penaranda", "Guijuelo",
    "Alba de Tormes", "Cantalapiedra", "Macotera", "Ciudad Rodrigo",
    "La Alberca", "Mogarraz", "Pedraza", "Sepulveda", "Medinaceli",
    "Frias", "Covarrubias", "Lerma", "Avila", "Segovia", "Astorga",
    "Tordesillas", "Ainsa", "Albarracin", "Polvazares", "Olite",
    "Laguardia", "Briones", "Pals", "Besalu", "Siurana", "Morella",
    "Cuenca", "Siguenza", "Trujillo", "Guadalupe", "Caceres", "Zafra",
    "Ronda", "Ubeda", "Baeza", "Osuna", "Antequera", "Carmona",
    "Comillas", "Laredo", "Potes", "Cangas de Onis", "Luarca",
    "Combarro", "Allariz", "Xativa", "Bocairent", "Peniscola",
    "Santillana del Mar", "Zugarramurdi", "Madrigal de las Altas Torres",
    "Cangas de Onís", "Robledillo de Gata", "Puebla de Sanabria", "Alcalá del Júcar",
    "Cudillero", "La Alberca", "Pedraza", "Albarracín",
}

local TIPOS_SITIOS = {
    PlayerFortress = true,
    DwarfFortress  = true,
    MountainHalls  = true,
    Town           = true,
    Hamlet         = true,
    ForestRetreat  = true,
    Fortress       = true,
    Cave           = false,
    Labyrinth      = false,
    Shrine         = false,
    Camp           = false,
    Tomb           = false,
}

-- ============================================================
-- Utilidades
-- ============================================================

local function shuffle(original)
    local t = {}
    for i, v in ipairs(original) do t[i] = v end
    local n = #t
    for i = n, 2, -1 do
        local j = math.random(i)
        t[i], t[j] = t[j], t[i]
    end
    return t
end

-- Saca el siguiente nombre de la lista, reciclandola si se acaba
local function siguiente(lista, estado)
    if estado.idx > #lista then
        lista = shuffle(lista)
        estado.idx = 1
        estado.lista = lista
    end
    local nombre = lista[estado.idx]
    estado.idx = estado.idx + 1
    return nombre
end

-- ============================================================
-- Logica de renombrado
-- ============================================================

local function renombrar_enanos(forzar)
    -- Estados independientes para cada lista
    local hombres = shuffle(HOMBRES)
    local mujeres = shuffle(MUJERES)
    local estado_h = { lista = hombres, idx = 1 }
    local estado_m = { lista = mujeres, idx = 1 }

    local contador = 0

    for _, unit in ipairs(df.global.world.units.all) do
        if dfhack.units.isActive(unit)
        and dfhack.units.isCitizen(unit)
        and not dfhack.units.isAnimal(unit) then
            if forzar or unit.name.nickname == '' then
                local nombre
                -- unit.sex: 0 = femenino, 1 = masculino
                if unit.sex == 0 then
                    nombre = siguiente(estado_m.lista, estado_m)
                else
                    nombre = siguiente(estado_h.lista, estado_h)
                end
                unit.name.nickname = nombre
                contador = contador + 1
            end
        end
    end
    return contador
end

local function renombrar_fortaleza(nombre_custom)
    local site_id = df.global.plotinfo.site_id
    for _, site in ipairs(df.global.world.world_data.sites) do
        if site.id == site_id then
            local nombre = nombre_custom or PUEBLOS[math.random(#PUEBLOS)]
            site.name.first_name = nombre
            site.name.has_name = true
            dfhack.print('[nombres-espanoles] Fortaleza renombrada a: ' .. nombre .. '\n')
            return true
        end
    end
    dfhack.printerr('[nombres-espanoles] No se encontro el sitio de la fortaleza.')
    return false
end

local function renombrar_sitios()
    local pueblos = shuffle(PUEBLOS)
    local site_id_jugador = df.global.plotinfo.site_id
    local idx = 1
    local contador = 0
    for _, site in ipairs(df.global.world.world_data.sites) do
        if site.id ~= site_id_jugador then
            local tipo_str = df.world_site_type[site.type]
            if tipo_str and TIPOS_SITIOS[tipo_str] then
                if idx > #pueblos then
                    pueblos = shuffle(PUEBLOS)
                    idx = 1
                end
                site.name.first_name = pueblos[idx]
                site.name.has_name = true
                idx = idx + 1
                contador = contador + 1
            end
        end
    end
    return contador
end

-- ============================================================
-- Hook automatico al cargar partida
-- ============================================================

dfhack.onStateChange[GLOBAL_KEY] = function(sc)
    if sc == SC_MAP_LOADED and df.global.gamemode == df.game_mode.DWARF then
        state = { enabled = false }
        utils.assign(state, dfhack.persistent.getSiteData(GLOBAL_KEY, state))
        if state.enabled then
            dfhack.print('[nombres-espanoles] Modo automatico: renombrando enanos...\n')
            local n = renombrar_enanos(false)
            dfhack.print('[nombres-espanoles] ' .. tostring(n) .. ' enano(s) renombrado(s).\n')
        end
    end
end

-- ============================================================
-- Enable / disable
-- ============================================================

function isEnabled()
    return state.enabled
end

local function persistir()
    dfhack.persistent.saveSiteData(GLOBAL_KEY, state)
end

if dfhack_flags.enable then
    if dfhack_flags.enable_state then
        state.enabled = true
        persistir()
        dfhack.print('[nombres-espanoles] Modo automatico ACTIVADO.\n')
    else
        state.enabled = false
        persistir()
        dfhack.print('[nombres-espanoles] Modo automatico DESACTIVADO.\n')
    end
    return
end

-- ============================================================
-- Ejecucion bajo demanda
-- ============================================================

if dfhack_flags.module then return end

if not dfhack.isMapLoaded() then
    dfhack.printerr('[nombres-espanoles] Necesitas tener una partida cargada.')
    return
end

local args = {...}
local accion = args[1] or 'enanos'

if accion == 'help' or accion == '--help' then
    print([[
nombres-espanoles - Renombra enanos y sitios con nombres espanoles.

ACCIONES:
  (sin args)            Renombra enanos sin apodo
  enanos                Igual
  enanos forzar         Renombra TODOS sobreescribiendo apodos existentes
  fortaleza             Renombra tu fortaleza con pueblo aleatorio
  fortaleza "Nombre"    Renombra con ese nombre concreto
  sitios                Renombra sitios del mundo
  todo                  Enanos + fortaleza + sitios
  help                  Esta ayuda

MODO AUTOMATICO:
  enable nombres-espanoles
  disable nombres-espanoles
]])
    return
end

if accion == 'enanos' then
    local forzar = (args[2] == 'forzar')
    local n = renombrar_enanos(forzar)
    dfhack.print('[nombres-espanoles] ' .. tostring(n) .. ' enano(s) renombrado(s).\n')

elseif accion == 'fortaleza' then
    renombrar_fortaleza(args[2])

elseif accion == 'sitios' then
    local n = renombrar_sitios()
    dfhack.print('[nombres-espanoles] ' .. tostring(n) .. ' sitio(s) renombrado(s).\n')

elseif accion == 'todo' then
    local n_enanos = renombrar_enanos(false)
    renombrar_fortaleza(nil)
    local n_sitios = renombrar_sitios()
    dfhack.print('[nombres-espanoles] Hecho: '
        .. tostring(n_enanos) .. ' enano(s), '
        .. tostring(n_sitios) .. ' sitio(s).\n')

else
    dfhack.printerr('[nombres-espanoles] Accion desconocida: "' .. accion .. '". Prueba: nombres-espanoles help')
end