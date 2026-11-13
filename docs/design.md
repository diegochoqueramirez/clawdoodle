# Diseño de la skill `clawdoodle`

Estado: **borrador v0**. Decisiones tomadas por el usuario: alcance = cualquier tema con metáforas; entregables = GIF + SVG animado;
revisión por otro agente **opcional** (decisión posterior: por defecto revisión propia con comprobaciones automáticas y la rejilla; el agente solo con objetos nuevos o si el usuario lo pide); vive en este repo y debe poder instalarse en otra compu con git.

## 1. Objetivo y conversación
El usuario describe un tema o una idea ("Clawd explicando qué es una base de datos"). La skill responde con un GIF de Clawd
haciendo una acción que representa el tema, más el SVG animado. Después el usuario corrige en lenguaje natural:
"cambia de tema", "incluye un libro", "más lento", "más grande", "quita el escritorio".

Flujo de cada petición:
1. **Entender**: tema -> una metáfora visual (una sola). Preguntar solo si es ambiguo y la respuesta cambia el resultado.
2. **Escribir la escena** (JSON, ver 3) con el vocabulario de la biblioteca; dibujar objetos nuevos como cuadrículas de texto.
3. **Validar** (esquema, límites del lienzo, referencias a ids, duración) y **exportar** vista previa.
4. **Revisar**: por defecto uno mismo (validador, márgenes, rejilla de 16 momentos y `reviewer/REVIEW.md`); con un agente aparte solo si se dibujaron objetos nuevos o el usuario lo pide (hasta 3 rondas).
5. **Entregar**: rutas del GIF y del SVG, fotogramas de muestra, y qué metáfora se eligió y por qué (una línea).
6. **Corregir**: cada corrección edita **solo el JSON de la escena** (versionado v1, v2...), reexporta y vuelve a revisar.

## 2. Estructura del repo (portable)
```
clawdoodle/
  .claude/skills/clawdoodle/        <- la skill; Claude Code la descubre sola al abrir el repo (también tras clonar)
    SKILL.md                       instrucciones para Claude (flujo, reglas, comandos)
    engine/                        motor autocontenido (sin rutas absolutas, GSAP incluido en vendor/)
      clawd.js  render.js  parts/{props.js,actions.js}  export_gif.py  review_sheet.py  vendor/gsap.min.js
      scenes/                      escenas de ejemplo (*.scene.json)
    reviewer/REVIEW.md             lista de calidad + formato de reporte del agente revisor
    scripts/setup.sh               crea engine/.venv con Pillow y comprueba Chrome
  docs/                            este diseño
```
Instalar en otra compu: `git clone` -> `.claude/skills/clawdoodle/scripts/setup.sh` -> abrir Claude Code en el repo.
(Para usarla fuera del repo: enlazar la carpeta a `~/.claude/skills/clawdoodle`.)
Requisitos: Python 3, Chrome/Chromium (detectado en macOS/Linux/Windows o con `CHROME_PATH`), Pillow (lo instala setup.sh).
Salidas: `./clawd-out/<tema>/v1/…` en el directorio donde se use la skill (ignorado por git).

## 3. Lenguaje de escenas
Hoy (v0): `{name, canvas, loop, clawd{x,y}, props[{type,id,layer,...}], timeline[{at,action,...}]}` con props `desk|keyboard|crt` y
acciones `pose|type|blink|scroll|cursor`; poses `rest|lean`.

Para "cualquier tema" hay que ampliarlo (Fase 1):
- **`sprite`** (prop genérico): cuadrícula de caracteres + paleta con nombre -> rectángulos. Así el modelo dibuja cualquier objeto.
  Admite varios fotogramas (`frames`) para animación por cambio de dibujo (engranaje, llama, parpadeo de pantalla).
- **Objetos con id** y acciones genéricas sobre cualquier objeto: `move`, `hop`, `shake`, `pulse`, `appear/disappear`, `swap`, `spin(steps)`.
- **Poses de Clawd** parametrizadas (`rest, lean, look, hop, wave, point, think, shrug, crouch`), siempre planas (sin sombreado).
- **Paleta cerrada** (cuerpo `#DD775B`, ojos `#1A1A1A`, neutros y 6-8 acentos) para que todo parezca de la misma familia.
- **Validador**: bordes del lienzo, objetos que se solapan sin querer, ids inexistentes, tiempos fuera del bucle, paleta, tamaño máximo.

## 4. Metáforas ("cualquier tema")
Regla: **una metáfora, <= 3 objetos, una acción principal, bucle de 3-4 s**. Catálogo inicial para guiar al modelo:
base de datos -> archivador/cajones; red/API -> buzón o cables con nodos; seguridad -> candado y llave; bug -> insecto y lupa;
deploy -> cohete/paquete; caché -> estante cercano; búsqueda -> lupa sobre documentos; memoria -> libreta/post-its;
tiempo/espera -> reloj de arena; IA/razonar -> bocadillo de pensamiento; datos -> cinta transportadora; tests -> lista que se marca.
Si no hay metáfora clara, la skill propone 2 y deja elegir al usuario (una pregunta corta).

## 5. Reglas de estilo (invariantes que la skill no rompe)
Plano 2D, sin sombreado ni brillos; un color de cuerpo; solo rectángulos; parpadeo `^ ^` con arcos de 3 rects; sin texto en el GIF;
fondo transparente; extremidades que no sobresalen de forma fea (las patas de los extremos se meten al inclinar); nada pegado al borde;
bucle sin saltos (el personaje vuelve exacto al fotograma 0); ritmo con pausas intencionadas.

## 6. Calidad (revisión siempre)
- Herramientas: `review_sheet.py` (hoja de 12 momentos, ampliaciones, bordes, costura del bucle) y validador de escena.
- El agente revisor recibe: ruta del GIF y de la escena, `REVIEW.md`, decisiones de estilo del usuario, y debe **mirar las imágenes**.
- Entrega un reporte (problemas / cambios / verificación / estilo sin tocar). Máximo 3 iteraciones. La skill verifica por su cuenta antes de entregar.
- Limitación conocida: se revisan imágenes fijas; los tirones se detectan solo por métricas. El ojo del usuario es el control final.

## 7. Entregables
- **GIF** transparente (1056x464 aprox., 33 fps) vía Chrome headless + Pillow.
- **SVG animado.** Dos opciones, decisión pendiente:
  a) *Vivo*: HTML/JS con GSAP (incluye `vendor/gsap.min.js`), se incrusta inline; no funciona en `<img src>`.
  b) *Horneado* (elegido; se implementó con CSS `@keyframes` y no con SMIL, ver sección 14): muestrear el timeline; un solo `.svg` autónomo que
     funciona en `<img>`, navegadores y presentaciones, sin JS; pesa más.

## 8. Plan por fases
| Fase | Contenido | Estado |
|---|---|---|
| 0 | Motor autocontenido y portable en la skill (GSAP local, Chrome detectado, setup.sh, export desde cualquier carpeta) | **hecho** |
| 1 | Prop `sprite` + acciones genéricas + poses ampliadas + validador de escenas | **hecho** (ver notas abajo) |
| 2 | 8-10 escenas de ejemplo (pensar, buscar, leer, depurar, tests, desplegar, esperar...) que fijan el estilo | **hecho** (ver sección 11) |
| 3 | `SKILL.md` completo + integración del agente revisor + versionado de escenas | **hecho** (ver sección 12) |
| 4 | Exportador de SVG horneado (CSS keyframes) | **hecho** (ver sección 14) |
| 5 | Pruebas con temas reales, medir qué falla, ajustar la biblioteca | **hecho** (ver sección 15) |

## 9. Riesgos y decisiones abiertas
- "Cualquier tema" -> más variación de calidad; mitigación: metáforas guiadas, catálogo, validador y revisor.
- El SVG con GSAP necesita JS; decidir entre vivo y horneado (ver 7).
- Export lento (~50 s para 106 fotogramas): se puede bajar con `--fps 25` o escala 3 en la vista previa y subir al final.
- GSAP se incluye en el repo (licencia gratuita de GreenSock): revisar los términos si el repo se hace público.
- Las carpetas `svg/` y `pixel/` quedan como historial; el motor de la skill es `.claude/skills/clawdoodle/engine`.

## 10. Notas de la Fase 1 (hecho)
- `sprite` (cuadrícula de texto + paleta con nombre, varios fotogramas), 10 acciones genéricas (`move hop shake bob pulse appear disappear swap cycle spin`)
  más `wave`, 11 poses planas y `validate_scene.py` (estructura, ids, paleta, límites del lienzo con alcance de poses y movimientos, solapes, costura del bucle).
- `vocab.json` es la lista única de nombres; `validate_scene.py --selftest` falla si se desincroniza del JS.
- Tres escenas de prueba con temas distintos: `thinking` (razonar), `database` (base de datos), `debugging` (depurar). Las tres validan, exportan y tienen costura 0 del personaje.
- Hallazgos: el validador detectó recortes reales (la pose `cheer` sube la mano 34 unidades); el arte de los objetos sigue siendo borrador (el bicho de `debugging`
  se lee casi como una mancha verde); `point_r` estira el brazo como una barra larga (decisión de estilo pendiente); Computing ya no es idéntico píxel a píxel
  (1-3 píxeles por fotograma en los bordes de piezas giradas por el redondeo de transformaciones), sin diferencia visible.
- Siguiente: Fase 2 (más escenas ejemplo y mejor arte) o Fase 3 (SKILL.md completo con el agente revisor), a elección.

## 11. Notas de la Fase 2 (hecho)
- Diez escenas de referencia (`engine/scenes/`, catálogo en `scenes/README.md`): computing, thinking, database, debugging, searching, tests, deploy, waiting, security, network.
- `engine/STYLE.md` fija el estilo: objetos planos de dos tonos, objetos claros con borde, tamaño de celda, <= 3 objetos, estructura de cuatro tiempos (preparación / acción / remate / reinicio).
- Fallos del motor encontrados al hacer las escenas y corregidos: los fundidos con `fromTo` ocultaban el objeto desde el segundo 0 (el cohete no se veía);
  `pulse` y `spin` usaban el centro original del objeto aunque ya se hubiera movido (empujaba la lupa fuera del lienzo); `move` animaba siempre x e y y habría pisado a `bob`.
- Validador: ya no cuenta los movimientos de un objeto mientras está oculto, y acepta `overlap_ok` para declarar solapes intencionados.
- `point_r` estira menos el brazo (10 en vez de 18 unidades) para que no parezca un rectángulo suelto.
- Pendiente de arte: el catálogo no cubre aún caché, memoria, planificación, monitorización, control de versiones, pipeline de datos, errores o permisos.

## 12. Notas de la Fase 3 (hecho)
- `engine/clawd.py`: CLI de proyecto (`new list check render review-pack save versions diff revert retime remove doctor`). Cada animación vive en
  `./clawdoodles/<slug>/` con `scene.json` (lo único que se edita), `versions/`, `out/` y `review/`. `retime` hace explícitos los valores por defecto antes de escalar.
- `reviewer/AGENT_BRIEF.md`: plantilla para el agente revisor (se rellena y se pasa al Agent tool). `engine/frames_grid.py` genera la rejilla estándar de 16 momentos
  del bucle completo muestreados por tiempo (el muestreo por índice solo cubre parte del bucle porque el GIF fusiona fotogramas duplicados).
- `SKILL.md` completo: flujo de 6 pasos, tabla "lo que dice el usuario -> comando", reglas fijas. Validador con alcance de `pulse`/`spin` (con holgura de 4 unidades).
- Prueba de aceptación con un tema fuera del catálogo (**caché**): escena nueva -> `check` -> `render` -> agente revisor real con la plantilla (leyó las imágenes, no tocó nada,
  informe coherente) -> `render --final` -> `save` -> corrección "más lento" (`retime` x1,3) -> corrección "quita el archivador" (`remove`) -> `versions`/`diff`. La escena
  revisada quedó como undécimo ejemplo (`cache`).
- Prueba de instalación limpia: copia de la skill sin `.venv` a otra ruta, `setup.sh` desde cero, `doctor` OK, render desde otro directorio, sin rutas absolutas en la skill.
- Ajustes hechos al probar: umbral TIGHT de `review_sheet.py` a 1,0 % (con 1,8 % marcaba casi toda escena); `save` ya no crea versiones idénticas; `diff` reconoce un cambio de ritmo uniforme.
- Límites conocidos: el revisor solo ve imágenes fijas (los tirones se detectan solo por métricas); `setup.sh` es bash y busca `.venv/bin/python` (Windows usaría `Scripts`; sin probar);
  las versiones guardadas pueden mezclar calidades de GIF (previa y final); no hay SVG animado todavía (Fase 4).

## 13. Decisión: revisor opcional
Evidencia: en la Fase 2 el agente halló 5 problemas reales en 10 escenas (arte nuevo); en la prueba de caché (escena casi de plantilla) no cambió nada y las comprobaciones automáticas
ya cubrían lo duro. El usuario, que hace ajustes manuales, eligió: revisión propia siempre; agente solo para dibujos nuevos o bajo petición. La plantilla `AGENT_BRIEF.md` y la rejilla se mantienen.

## 14. Notas de la Fase 4 (hecho)
- `engine/bake_svg.py` + `bake.html`: Chrome carga la escena con GSAP, muestrea cada elemento (matriz de transformación, opacidad efectiva, relleno) a 60 fps durante un bucle y el script escribe
  `@keyframes` CSS lineales sobre el mismo marcado de `<rect>`/`<g>`. Sin JavaScript. Se simplifican los fotogramas clave (Ramer-Douglas-Peucker con tolerancias por componente).
- Por qué CSS y no SMIL: `animateTransform` no admite matrices; una matriz general solo se puede animar con la propiedad CSS `transform`. Las animaciones CSS dentro de un SVG funcionan en `<img src>`.
- Los cambios de longitud de los puentes de los brazos (atributos `width/x`) se convierten en una transformación afín sobre el rectángulo original, para poder animarlos con `transform`.
- Los saltos duros (cambio de fotograma de un sprite, destello de tecla) se mantienen duros: el navegador busca por bisección el instante exacto del salto y se añaden dos fotogramas clave separados 0,005 %.
- Verificación (`bake_svg.py --verify`, `clawd.py export-svg --verify`): renderiza el SVG y el original GSAP en 8 instantes y compara con una métrica tolerante al suavizado de bordes (un píxel
  pasa si cae dentro del rango min..max de colores de su vecindario en la otra imagen). Las 11 escenas del catálogo dan 0-193 píxeles de ~450.000 (<= 0,04 %); un instante distinto da miles.
- Fallos encontrados al verificar: (1) los fotogramas ocultos conservaban `display="none"` y nunca se mostraban; (2) las `SVGMatrix` no se pueden multiplicar por `DOMMatrix` (rompía `database`);
  (3) los saltos se interpolaban 16 ms y dejaban un fantasma; (4) mi primera métrica contaba cada borde suavizado como error.
- Tamaños: 20-100 KB por SVG (el GIF final pesa 150-780 KB). Prueba en `<img>`: tres capturas en instantes distintos muestran movimiento y el archivo no contiene `<script>`.
- Diferencia conocida con el GIF: las piezas giradas salen con los bordes suavizados (antialiasing) en el SVG y escalonados en el GIF; el navegador decide, y a tamaño de pantalla no se aprecia.
- Límites: el SVG es una captura a 60 fps de un bucle fijo (no es editable como animación); el muestreo asume bucle continuo (la validación de la escena ya lo comprueba); en Safari/Firefox no se ha probado
  (solo Chrome headless); no hay `prefers-reduced-motion`.

## 15. Notas de la Fase 5 (hecho): pruebas en frío con temas reales
**Método.** Seis agentes sin contexto (solo `SKILL.md` y lo que referencia) crearon cada uno un GIF de un tema nuevo: ramas de Git, entrenar un modelo, copia de seguridad, límite de peticiones,
fuga de memoria y ciclo del agua (no técnico). No podían tocar la skill; debían llevar un registro de fricción. Ronda 2: fuga de memoria y Git otra vez, con las herramientas nuevas.
**Resultado.** Los seis entregaron GIF + SVG verificado. Nota propia de cada agente para un principiante: 3, 3, 3, 3, 3,5, 3,5 (media 3,2); ronda 2: 3 y 3. Las herramientas nuevas ahorraron
iteraciones (previa de sprite, `add-gauge`, `moveTo`, `recolor`, `sprite_tools`) pero no subieron la nota: el techo lo ponen el vocabulario de poses y la regla de no usar texto.
**Bugs reales encontrados y corregidos.**
1. SVG distinto del GIF cuando un objeto se reutiliza con aparecer / mover y volver / desaparecer: los movimientos eran relativos y su valor inicial dependía de cuándo GSAP los inicializaba (la vuelta de un
   ciclo se solapaba con la ida del siguiente). Ahora las acciones genéricas parten de la posición nominal del objeto en ese instante (historial de segmentos) con valores absolutos.
2. `pulse` y `spin` compartían transformación con el movimiento y GSAP compensaba la posición según el orden de reproducción: ahora cada objeto tiene una capa exterior (mover, saltar, sacudir, opacidad)
   y una interior (escala, giro).
3. Falso positivo del validador (dos `move` de ida y vuelta se sumaban desde el origen): el validador usa el mismo modelo de posición que el motor.
**Cómo se evitó una regresión.** Antes de cambiar el motor se guardó una base de las 11 escenas; el primer diseño del arreglo la rompió (el bicho de `debugging` saltaba durante su pausa) y se vio en la
comparación. Estado final: las 11 escenas idénticas a la base (0 px) y 13 verificaciones de SVG en OK.
**Añadido.** Validador: aviso de más de 3 objetos, movimientos o poses solapados, `recolor` sin restaurar, bucles de más de 5,5 s, `moveTo` sin coordenadas. Motor: `moveTo`, `recolor`, poses `sad`
(rehecha tras verla: casi no se distinguía de `rest`), `relief` (rehecha) y `hold_r`, 4 colores intermedios. CLI: `sprite-preview`, `templates`, `add-sprite`, `add-gauge`, `clone`, `palette`; `check` avisa de rejilla
obsoleta y `render` borra la vieja. `sprite_tools.py`: `Grid`, `gauge_frames`, `write_sprite`, `cell_to_xy`. Documentación: recetas para temas abstractos sin texto (`STYLE.md`), geometría segura (x del primer objeto = `clawd.x + 120`),
semántica de `move`/`moveTo`/`layer`/`px`, tabla de colores, tiempos medidos (vista previa ~30 s, final ~50 s, verificación ~10 s; seis renders a la vez tardan minutos), aviso de zsh.
**Mantiene la regla de sin texto** (decisión del usuario); lo que más pidieron los agentes fue precisamente texto y etiquetas: queda como limitación conocida de la explicación para principiantes.
**Pendiente / ideas** (no hechas): un `point` con objetivo (el brazo plano solo señala a la derecha); un objeto que "entra" en otro (recorte); trayectorias curvas; poses de Clawd más expresivas (triste/alarma se leen poco);
más plantillas (papelera, bloque de datos, contenedor, engranaje); `new --force`/`reset` (los agentes quisieron rehacer un proyecto y no hay comando).
