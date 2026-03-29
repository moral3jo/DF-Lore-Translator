RUTAS:
ruta juego
D:\SteamLibrary\steamapps\common\Dwarf Fortress

palabras
D:\SteamLibrary\steamapps\common\Dwarf Fortress\data\vanilla\vanilla_languages\objects

ficheros extra
C:\Users\moral\AppData\Roaming\Bay 12 Games\Dwarf Fortress
    carpetas:data,mods,prefs,save

-----
HAcer un miniprograma que permita hacer la traduccion de manera sencilla, podria incluso montar una pequeña interface para gestionarlo mejor.
todo autocontenido dentro de la carpeta del mod, la gracia es que enviando la carpeta se tenga las herramientas y el mod listo para desplegar
el fin es traducir las palabras y cada palabra puede tener diferentes formas
por ejemplo una palabra se puede expresar como nombre, verbo o adjetivo...

caso de uso, arranco script me crea una mini interface:
abro la pagina me sale todo vacio con las rutas por defecto arriba indicadas
pulso el boton de traer datos, se trae los ficheros necesarios copiandolos y extrae las palabras a la carpeta del mod (tal vez una sqlite local?)
entonces veo hay 200 palabras por traducir y voy traduciendolas, 
a la izquierda nombre actual a la derecha nuevo con las opciones (nombre, verbo, adj....)
traduzco palabras se guardan en bbdd o lo que sea en tiempo real para no tener que pulsar guardar

y luego tengo un boton de generar nuevo fichero
esto hace, pilla el fichero original, sustituye las palabras que he reescrito y las que no las deja como estaban
haz una funcionalidad por defecto, cuando el fichero original tenga nombre y adj por ejemplo pues en la parte derecha me muestras ambos, segun escribo nombre si adj esta vacio se pone lo mismo y si quiero ya lo cambio yo
asi vamos mas rapido

tendre los filtros minimos para ver palabras traducidas sin traducir, estadisticas totales que faltan


aqui te suelto algunos detalles tecnicos de los ficheros que vamos a procesar y al final un trozo del fichero original



Para que tu mod funcione, tienes que clonar el archivo entero con todas sus etiquetas y estructura, pero cambiando únicamente las palabras en minúscula que están dentro de los corchetes de las categorías gramaticales.

Aquí tienes la guía definitiva o "documentación" que necesitas para programar tu script:

1. La anatomía de language_words.txt
El fichero original es básicamente un bloque de texto gigante. Las primeras dos líneas siempre son la cabecera (esto tu script debe copiarlo tal cual):

Plaintext
language_words

[OBJECT:LANGUAGE]
A partir de ahí, el fichero define "Conceptos" uno por uno. Un bloque típico de una palabra se ve así:

Plaintext
[WORD:BATTLE]
[NOUN:battle:battles]
[VERB:battle:battles:battled:battled:battling]
[ADJ:battling]
2. Qué cambiar y qué NO cambiar (¡Vital!)
[WORD:BATTLE] -> NO SE TOCA NUNCA. Esta palabra en mayúsculas es el "ID interno" que usa el motor del juego. Si cambias esto a [WORD:BATALLA], el juego se rompe porque los enanos buscarán BATTLE en su diccionario y no lo encontrarán.

Todo lo demás ([NOUN..., [VERB..., [ADJ...) -> SE TRADUCE. Estas son las formas que el juego muestra por pantalla.

3. Los formatos que tu script tiene que buscar (Expresiones Regulares / Splitting)
Tu script tendrá que leer línea a línea y buscar las siguientes etiquetas. Fíjate en cómo se estructuran separadas por dos puntos : y cerradas por un corchete ].

A. Sustantivos ([NOUN])
Tienen dos partes: Singular y Plural.

Formato original: [NOUN:singular:plural]

Ejemplo inglés: [NOUN:battle:battles]

Objetivo español: [NOUN:batalla:batallas]

B. Adjetivos ([ADJ])
Tienen una sola parte.

Formato original: [ADJ:adjetivo]

Ejemplo inglés: [ADJ:bloody]

Objetivo español: [ADJ:sangriento]

C. Verbos ([VERB]) - El más complejo
Tienen cinco partes. A veces en español no encajan perfectamente uno a uno con el inglés, pero se adaptan bien:

Formato original: [VERB:presente:presente_3ra_persona:pasado:participio:gerundio]

Ejemplo inglés: [VERB:smash:smashes:smashed:smashed:smashing]

Objetivo español: [VERB:aplastar:aplasta:aplasto:aplastado:aplastando]
(Nota: no uses tildes, usa ASCII estándar (aplasto en vez de aplastó) para evitar problemas visuales en el juego).

D. Prefijos ([PREFIX])
Aparecen menos, pero existen. Tienen una sola parte.

Formato original: [PREFIX:prefijo]

Ejemplo inglés: [PREFIX:arch]

Objetivo español: [PREFIX:archi]

------
language_words

[OBJECT:LANGUAGE]

[WORD:ABBEY]
	[NOUN:abbey:abbeys]
		[FRONT_COMPOUND_NOUN_SING]
		[REAR_COMPOUND_NOUN_SING]
		[THE_NOUN_SING]
		[REAR_COMPOUND_NOUN_PLUR]
		[OF_NOUN_PLUR]

[WORD:ACE]
	[NOUN:ace:aces]
		[FRONT_COMPOUND_NOUN_SING]
		[REAR_COMPOUND_NOUN_SING]
		[THE_NOUN_SING]
		[REAR_COMPOUND_NOUN_PLUR]
		[OF_NOUN_PLUR]
	[ADJ:ace]
		[ADJ_DIST:1]
		[FRONT_COMPOUND_ADJ]
		[THE_COMPOUND_ADJ]

[WORD:ACT]
	[NOUN:act:acts]
		[FRONT_COMPOUND_NOUN_SING]
		[REAR_COMPOUND_NOUN_SING]
		[THE_NOUN_SING]
		[REAR_COMPOUND_NOUN_PLUR]
		[OF_NOUN_PLUR]
	[VERB:act:acts:acted:acted:acting]
		[STANDARD_VERB]

[WORD:AFTER]
	[PREFIX:after]
		[FRONT_COMPOUND_PREFIX]
		[THE_COMPOUND_PREFIX]

[WORD:AGE]
	[NOUN:age:ages]
		[FRONT_COMPOUND_NOUN_SING]
		[REAR_COMPOUND_NOUN_SING]
		[THE_NOUN_SING]
		[OF_NOUN_SING]
		[FRONT_COMPOUND_NOUN_PLUR]
		[REAR_COMPOUND_NOUN_PLUR]
		[THE_NOUN_PLUR]
		[OF_NOUN_PLUR]
	[VERB:age:ages:aged:aged:aging]
		[STANDARD_VERB]

[WORD:AGELESS]
	[ADJ:ageless]
		[ADJ_DIST:4]

[WORD:ALE]
	[NOUN:ale:ales]
		[FRONT_COMPOUND_NOUN_SING]
		[REAR_COMPOUND_NOUN_SING]
		[THE_NOUN_SING]
		[OF_NOUN_SING]
		[FRONT_COMPOUND_NOUN_PLUR]
		[REAR_COMPOUND_NOUN_PLUR]
		[THE_NOUN_PLUR]
		[OF_NOUN_PLUR]

[WORD:ANCIENT]
	[NOUN:ancient:ancients]
		[FRONT_COMPOUND_NOUN_SING]
		[REAR_COMPOUND_NOUN_SING]
		[THE_NOUN_SING]
		[OF_NOUN_PLUR]
	[ADJ:ancient]
		[ADJ_DIST:4]
		[FRONT_COMPOUND_ADJ]

[WORD:ANGEL]
	[NOUN:angel:angels]
		[FRONT_COMPOUND_NOUN_SING]
		[REAR_COMPOUND_NOUN_SING]
		[THE_NOUN_SING]
		[REAR_COMPOUND_NOUN_PLUR]
		[OF_NOUN_PLUR]
	[ADJ:angelic]
		[ADJ_DIST:3]

[WORD:ANGER]
	[NOUN:anger:angers]
		[FRONT_COMPOUND_NOUN_SING]
		[REAR_COMPOUND_NOUN_SING]
		[THE_COMPOUND_NOUN_SING]
		[THE_NOUN_SING]
		[OF_NOUN_SING]
		[REAR_COMPOUND_NOUN_PLUR]
	[ADJ:angry]
		[ADJ_DIST:2]
		[FRONT_COMPOUND_ADJ]
		[THE_COMPOUND_ADJ]

[WORD:ANIMAL]
	[NOUN:animal:animals]
		[THE_COMPOUND_NOUN_SING]
		[THE_NOUN_SING]
		[OF_NOUN_PLUR]

[WORD:APE]
	[NOUN:ape:apes]
		[FRONT_COMPOUND_NOUN_SING]
		[REAR_COMPOUND_NOUN_SING]
		[THE_NOUN_SING]
		[FRONT_COMPOUND_NOUN_PLUR]
		[REAR_COMPOUND_NOUN_PLUR]
		[THE_NOUN_PLUR]
		[OF_NOUN_PLUR]

[WORD:APPLE]
	[NOUN:apple:apples]
		[FRONT_COMPOUND_NOUN_SING]
		[REAR_COMPOUND_NOUN_SING]
		[THE_NOUN_SING]
		[FRONT_COMPOUND_NOUN_PLUR]
		[REAR_COMPOUND_NOUN_PLUR]
		[THE_NOUN_PLUR]
		[OF_NOUN_PLUR]

[WORD:ARCH]
	[PREFIX:arch]
		[FRONT_COMPOUND_PREFIX]
		[THE_COMPOUND_PREFIX]

[WORD:ARM]
	[NOUN:arm:arms]
		[FRONT_COMPOUND_NOUN_SING]
		[REAR_COMPOUND_NOUN_SING]
		[THE_NOUN_SING]

