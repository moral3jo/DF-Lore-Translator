-- traductor.lua
-- Con la ficha de un enano abierta, escribe "traductor" en la consola.
-- Vuelca Overview + Personality + Thoughts al fichero df-traductor-events.txt

local unit = dfhack.gui.getSelectedUnit()
if not unit then
    dfhack.printerr('[traductor] Abre la ficha de un enano primero.')
    return
end

local lines = {}
local function add(s) table.insert(lines, s or '') end

-- ============================================================
-- CABECERA
-- ============================================================

local name       = dfhack.units.getReadableName(unit)
local profession = dfhack.units.getProfessionName(unit)
local job        = 'No job'
if unit.job and unit.job.current_job then
    job = df.job_type[unit.job.current_job.job_type] or 'Unknown job'
end

add('=== ' .. name .. ' ===')
add('Profession: ' .. profession)
add('Job: ' .. job)
add('')

-- ============================================================
-- OVERVIEW
-- ============================================================

add('--- OVERVIEW ---')

-- Edad y sexo
local age = math.floor(dfhack.units.getAge(unit))
local sex = unit.sex == 0 and 'female' or 'male'
add(tostring(age) .. ' years old, ' .. sex)
add('')

-- Rasgos visibles (columna derecha arriba - beliefs y traits destacados)
if unit.status and unit.status.current_soul then
    local soul = unit.status.current_soul
    -- Traits destacados
    if soul.traits then
        for i = 0, #soul.traits - 1 do
            local val = soul.traits[i]
            if val and (val >= 70 or val <= 30) then
                local tname = df.personality_facet_type[i] or ('trait_' .. i)
                if val >= 70 then
                    add(tname .. ' (high)')
                else
                    add(tname .. ' (low)')
                end
            end
        end
    end
end
add('')

-- Salud
local health = 'Healthy'
if unit.body and unit.body.wounds and #unit.body.wounds > 0 then
    health = #unit.body.wounds .. ' wound(s)'
end
add('Health: ' .. health)
add('')

-- Posicion y squad
local position = 'No official position'
add(position)
local squad = 'Squad: None'
if unit.military and unit.military.squad_id >= 0 then
    squad = 'Squad: ' .. tostring(unit.military.squad_id)
end
add(squad)
add('')

-- Top skills
add('Top skills:')
if unit.status and unit.status.current_soul then
    local skill_list = {}
    for _, skill in ipairs(unit.status.current_soul.skills) do
        if skill.rating > 0 then
            table.insert(skill_list, {
                name   = df.job_skill[skill.id] or tostring(skill.id),
                rating = skill.rating,
                experience = skill.experience,
            })
        end
    end
    table.sort(skill_list, function(a, b) return a.rating > b.rating end)
    for i = 1, math.min(6, #skill_list) do
        local s = skill_list[i]
        local levels = {'Dabbling','Novice','Adequate','Competent','Skilled',
                        'Proficient','Talented','Adept','Expert','Professional',
                        'Accomplished','Master','High Master','Grand Master','Legendary'}
        local level = levels[math.min(s.rating, 14) + 1] or tostring(s.rating)
        add('  ' .. level .. ' ' .. s.name)
    end
end
add('')

-- Necesidades
add('Needs:')
local has_needs = false
if unit.status and unit.status.needs then
    for _, need in ipairs(unit.status.needs) do
        if need.stress_delta > 0 then
            local nname = df.need_type[need.id] or tostring(need.id)
            add('  Unmet: ' .. nname)
            has_needs = true
        end
    end
end
if not has_needs then add('  No unmet needs') end
add('')

-- Cita
if unit.status and unit.status.current_soul and unit.status.current_soul.personality_summary then
    add('"' .. tostring(unit.status.current_soul.personality_summary) .. '"')
else
    -- Intentar con la descripcion de humor
    add('Mood: ' .. tostring(unit.mood))
end
add('')

-- ============================================================
-- PERSONALITY
-- ============================================================

add('--- PERSONALITY ---')
if unit.status and unit.status.current_soul then
    local soul = unit.status.current_soul

    -- Values / beliefs
    add('Values:')
    if soul.beliefs then
        for i = 0, #soul.beliefs - 1 do
            local b = soul.beliefs[i]
            if b and b.strength ~= 0 then
                local bname = df.value_type[b.id] or tostring(b.id)
                add('  ' .. bname .. ': ' .. tostring(b.strength))
            end
        end
    end
    add('')

    -- Facets / traits
    add('Facets:')
    if soul.traits then
        for i = 0, #soul.traits - 1 do
            local val = soul.traits[i]
            if val then
                local tname = df.personality_facet_type[i] or ('trait_' .. i)
                add('  ' .. tname .. ': ' .. tostring(val))
            end
        end
    end
    add('')

    -- Goals
    add('Goals:')
    if soul.goals then
        for _, goal in ipairs(soul.goals) do
            local gname = df.goal_type[goal.id] or tostring(goal.id)
            add('  ' .. gname)
        end
    else
        add('  None')
    end
end
add('')

-- ============================================================
-- THOUGHTS
-- ============================================================

add('--- THOUGHTS ---')
if unit.status and unit.status.recent_events then
    local found = false
    for _, event in ipairs(unit.status.recent_events) do
        local ename = df.unit_thought_type[event.type] or tostring(event.type)
        add('  ' .. ename .. ' (' .. tostring(event.age) .. ' ticks ago)')
        found = true
    end
    if not found then add('  No recent thoughts') end
else
    add('  No recent thoughts')
end
add('')
add('=== END ===')

-- ============================================================
-- Escribir fichero
-- ============================================================

local path = dfhack.getDFPath() .. '/df-traductor-events.txt'
local f, err = io.open(path, 'w')
if not f then
    dfhack.printerr('[traductor] Error: ' .. tostring(err))
    return
end
for _, line in ipairs(lines) do
    f:write(line .. '\n')
end
f:close()

dfhack.print('[traductor] Ficha de ' .. name .. ' guardada.\n')