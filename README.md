# Dashboard gerencial de avisos — Equipo 2

Versión visual ajustada a partir de `Dashboard_ENERGY_V2`.

## Cambios de esta versión
- La página **Inicio** reutiliza el diseño corporativo de referencia: hero azul, ficha corporativa y bloques de paleta de colores.
- La barra lateral recupera el logo ENERGY, la navegación vertical, el fondo azul oscuro y el estilo de filtros del dashboard anterior.
- Filtros globales en la barra lateral: **Año**, **Tipo de aviso**, **Departamento** y **Prioridad**. Además, los clics sobre las gráficas filtran por estado, tiempo frente al plazo, situación del pendiente, antigüedad y línea de transmisión.
- Se incorporan nuevamente los autores mostrados en la referencia: Mauricio Guerrero y Daniel Rodriguez.
- `theme.py` y la hoja de estilos `assets/style.css` se toman de la versión de referencia para mantener una única paleta institucional.
- Las visualizaciones del nuevo dashboard utilizan los colores semánticos e institucionales definidos en `theme.py`; los indicadores de cumplimiento, atraso y pendientes mantienen colores diferenciados.

## Secciones analíticas
1. Inicio.
2. Resumen gerencial.
3. Cumplimiento y plazos.
4. Pendientes por cumplir.
5. Territorio y red.

## Ejecución
```bash
pip install -r requirements.txt
python app.py
```
Abrir `http://127.0.0.1:8050/`.

## Estructura del repositorio
```
dashboard-avisos-equipo2/
├── app.py              # tablero Dash (KPI, gráficas, mapa, callbacks)
├── home.py             # página de inicio
├── theme.py            # paleta única de colores
├── data/avisos.csv     # base de avisos
├── assets/             # style.css, logo_energy.png, logo.svg, favicon.ico
├── requirements.txt    # dependencias
├── render.yaml         # configuración de Render (Blueprint)
├── Procfile            # comando de arranque (Render / Railway / Heroku)
└── .python-version     # Python 3.13 en el servidor
```
Los nombres de carpetas y archivos distinguen mayúsculas en el servidor (Linux): deben ser exactamente `data/avisos.csv` y `assets/logo_energy.png`.

## Publicación en línea (GitHub + Render)
1. Subir esta carpeta a un repositorio de GitHub.
2. En https://render.com → **New → Blueprint** → elegir el repositorio. Render lee `render.yaml` y crea el servicio web gratuito.
3. Al terminar la construcción, el tablero queda en `https://dashboard-avisos-equipo2.onrender.com` (o el nombre que asigne Render).
4. Cada `git push` a la rama principal vuelve a publicar el tablero automáticamente.

En el plan gratuito, el servicio se suspende tras 15 minutos sin visitas; la siguiente apertura tarda cerca de un minuto. Conviene abrirlo unos minutos antes de una presentación.

## Datos y alcance
- Base: `data/avisos.csv`.
- Filtro de alcance: `marca = normal`.
- Los avisos abiertos tienen fecha de corte registrada 06-may-2023; no debe interpretarse como fecha real de cierre.
- Los KPI y gráficos analíticos están en `app.py`; la página de inicio de referencia está en `home.py`; la paleta central está en `theme.py`.


## Ajustes de legibilidad — versión 1.2
- Se aumentó el tamaño de títulos, etiquetas, leyendas, ejes y cifras destacadas de las gráficas.
- Los gráficos de dona del resumen gerencial muestran etiquetas y porcentajes con mayor tamaño.
- El gráfico anual compara categorías excluyentes: avisos cerrados frente a avisos abiertos al corte, con valores visibles sobre las barras.
- Se reemplazó el término "cohorte" por una explicación directa: los avisos recibidos en un mes y los cerrados en ese mes no necesariamente son los mismos avisos.

## Ajuste puntual — versión 1.3
La gráfica «Volumen histórico y pendientes actuales por año de aviso» se rediseñó para seguir el estilo de «Comparación del volumen de avisos cerrados y abiertos por tipo»:
- barras agrupadas por año, con azul para cerrados y rojo para abiertos;
- etiquetas numéricas visibles encima de todas las barras, incluidos los valores cero;
- mayor espacio superior para evitar que las etiquetas queden cortadas;
- leyenda y ejes con la tipografía general del dashboard.

## Versión 1.4 — réplica del estilo de barras agrupadas ENERGY
La gráfica anual ahora reutiliza el patrón técnico de `make_grouped_type_status()` del dashboard ENERGY:
- construcción con `plotly.express.bar`;
- `barmode="group"` y orden fijo de estados Cerrado/Abierto;
- paleta `STATUS_COLORS` del tema original;
- barras con esquinas redondeadas (`cornerradius=7`);
- etiquetas numéricas fuera de las barras y sin recorte;
- leyenda horizontal, márgenes y separación entre barras equivalentes al gráfico de referencia;
- eje Y sin etiquetas numéricas, para conservar el estilo del gráfico original.
Se mantienen todos los años disponibles en la base y se muestran ambas categorías por año, incluso si una de ellas tiene valor cero.

## Versión 1.5 — ajustes de la sección Cumplimiento y plazos
- Se ajustó la gráfica de cumplimiento a tiempo por prioridad para utilizar la escala semántica institucional (rojo, ámbar y verde), con barras redondeadas y etiquetas de porcentaje más legibles.
- Se ajustó la gráfica de proporción de avisos cerrados atrasados por tipo a la escala semántica institucional (verde, ámbar y rojo), con barras horizontales redondeadas y etiquetas porcentuales.
- Se eliminó de esta sección la gráfica «Evolución mensual: avisos recibidos frente a avisos cerrados», que permanece en Resumen gerencial.
- La gráfica «Evolución mensual del cumplimiento de avisos cerrados» ahora ocupa el ancho completo disponible. Se aumentó su altura, grosor de línea y tamaño de marcadores; se mejoraron los ejes, la información emergente y la referencia de meta del 100%.

## Versión 1.6 — paleta y presentación de Pendientes por cumplir
- «Situación de cumplimiento de los pendientes»: se fijaron los colores semánticos de la paleta ENERGY desde `theme.py`: verde para dentro del plazo, rojo para vencido y ámbar para sin clasificación. Se amplió la lectura de las etiquetas.
- «Antigüedad de los avisos abiertos»: se sustituyó el gradiente genérico por colores de la paleta ENERGY ordenados por antigüedad (azules, ámbar, rojo y azul profundo). Se redondearon los bordes superiores de las barras y se mejoraron las etiquetas numéricas.
- «Pendientes por tipo de aviso y situación frente al plazo»: se fijó el mismo mapeo semántico verde/rojo/ámbar y el orden de las situaciones, para mantener consistencia con la gráfica de dona.

## Versión 1.7 — Territorio y tipologías
- El mapa amplía su altura y utiliza límites departamentales de Colombia como capa base; añade marcadores para las capitales departamentales y para los municipios con coordenadas en la base del proyecto.
- Los puntos municipales se dimensionan según el volumen de avisos y se colorean según el porcentaje pendiente (verde, ámbar y rojo).
- La capa GeoJSON departamental MGN 2025 se obtiene desde el repositorio público `ytolosa/mapas-colombia`, que declara derivar sus divisiones político-administrativas del Marco Geoestadístico Nacional del DANE. Se descarga al solicitar el mapa y queda en caché durante la ejecución. Si no hay conexión, el mapa conserva los puntos y capitales sobre la vista geográfica de Plotly, pero no dibuja los límites departamentales.
- La gráfica de departamentos usa rojo para pendientes y ámbar para cierres atrasados, con bordes redondeados.
- Se eliminó de esta sección «Pendientes por tipo de aviso y situación», porque la comparación por tipo ya está disponible en «Pendientes por cumplir».
- La tabla «Municipios con mayor acumulación pendiente» ahora ocupa todo el ancho disponible, con columnas distribuidas y tipografía ampliada.

Fuente cartográfica de referencia: https://github.com/ytolosa/mapas-colombia (archivos GeoJSON derivados de MGN 2025 del DANE).

## Versión 1.8 — ampliación del mapa territorial
- Se ocultó la leyenda de capas («Municipios analizados» y «Capitales departamentales») para recuperar espacio visual. Las dos capas siguen activas: los municipios continúan representados por círculos y las capitales por estrellas con sus etiquetas; sus datos se consultan al pasar el cursor.
- Se amplió la altura del mapa a 620 px y se extendió el dominio geográfico para aprovechar mejor el marco de la tarjeta.
- Se ajustó el encuadre y la escala de la proyección; se reservó únicamente el espacio lateral necesario para la escala de porcentaje pendiente.

## Versión 1.9 — mapa topográfico y altura compacta
- Se sustituyó el mapa Plotly por un mapa interactivo Leaflet/Folium embebido en la tarjeta existente; no se amplía el marco exterior.
- La vista inicial utiliza Esri World Topographic Map, que incluye relieve sombreado, rasgos fisiográficos, hidrografía, carreteras y caminos. Se incorpora OpenStreetMap como mapa base alternativo para revisar calles y caminos.
- Se conservan los límites departamentales, círculos de municipios analizados (tamaño por volumen y color por porcentaje pendiente) y estrellas de capitales departamentales.
- Se redujo la altura de la gráfica de departamentos y se fijó una altura uniforme de 460 px para las dos tarjetas de la fila; el mapa ocupa 370 px dentro de su tarjeta.
- Las capas base requieren conexión a internet. La cartografía de relieve y carreteras es contextual y no certifica transitabilidad, cierres, estado de la vía ni tiempos reales de acceso. Para análisis logístico de detalle se requiere contrastar con información vial oficial y actualizada de INVIAS/autoridades territoriales.

## Versión 1.9.1 — corrección de carga de la sección Territorio
- Se retiró el atributo `loading` del componente `html.Iframe`, para evitar que una versión de Dash que no lo soporte provoque un error de callback al construir la página.
- Se conserva el mapa Folium/Leaflet, sus capas topográficas, las vías, los municipios analizados, las capitales y la altura compacta de las tarjetas.
- Se validó la sintaxis de todos los archivos Python.

## Versión 1.10 — jerarquía visual del mapa y ranking territorial
- Capitales departamentales: se sustituyeron los iconos de estrella por un punto azul pequeño acompañado del nombre de la capital.
- Municipios analizados: se amplió la escala no lineal de los círculos según el número de avisos distintos por municipio. La escala utiliza 4 px para un aviso y puede alcanzar 18 px para los mayores volúmenes, manteniendo el color asociado al porcentaje pendiente.
- Texto de apoyo del mapa: se retiró la referencia a las estrellas.
- Departamentos con mayor concentración: se excluyeron etiquetas vacías, «Sin dato» y equivalentes; se ordenaron los departamentos por volumen combinado de pendientes y cierres atrasados, de mayor a menor.

## Versión 1.11 — tabla compacta y autores
- Se redujeron tamaño de fuente, interlineado y padding vertical de encabezados y filas de la tabla «Municipios con mayor acumulación pendiente». Se conservan las 15 filas y las cinco columnas; no se elimina información.
- Se añadieron a la barra lateral los autores Juan Bojacá (iniciales JB) y Andres Nova (iniciales AN), conservando los autores existentes.

## Versión 1.12 — KPI en una sola fila
- Se modificó exclusivamente la distribución de los KPI de las secciones Resumen Gerencial, Cumplimiento y plazos, y Territorio y tipos.
- En pantallas de escritorio, los seis indicadores se presentan en una sola fila.
- Se compactaron rellenos, tipografía y separación para que las tarjetas aprovechen el ancho disponible sin desbordarse.
- En tabletas y móviles se conserva una distribución adaptable de tres, dos o una columna para evitar tarjetas ilegibles.
- No se modificaron cálculos, indicadores, filtros ni visualizaciones.

## Versión 1.13 — ajustes de visualización de cumplimiento
- Las gráficas «Distribución real de tiempos de atención (Días abierto) según Prioridad» y «Evolución histórica del porcentaje de cumplimiento mensual» se presentan en una misma fila en pantallas de escritorio, con ancho equilibrado y altura de visualización de 390 px. En móviles se apilan para conservar la legibilidad.
- La etiqueta «Umbral esperado: 80%» se separó de la línea punteada y de las etiquetas numéricas de las barras.
- En el anillo de situación de pendientes se excluyen las categorías con cero registros; los colores se asignan por categoría para mantener su significado.
- No se modificaron los cálculos de cumplimiento, tiempos, conteos ni filtros.

## Versión 1.14 — recuperación de calidad visual en cumplimiento
- Las gráficas «Distribución real de tiempos de atención (Días abierto) según Prioridad» y «Evolución histórica del porcentaje de cumplimiento mensual» vuelven a mostrarse en filas independientes y a ancho completo, como antes del ajuste de dos columnas.
- Se redujo moderadamente la altura de la primera gráfica de 390 a 350 px y de la segunda de 390 a 320 px. Se conserva el ancho de visualización para no comprimir las cajas, puntos, ejes ni etiquetas.
- Se mantienen los demás ajustes de la versión 1.13.

## Versión 2.0 — correcciones de consistencia y mapa de la red de transmisión

### Correcciones
- **Meta única de cumplimiento (80 %)**: la constante `META_SLA` en `app.py` se usa en KPI, barras por prioridad, atraso por tipo (máximo tolerable 20 %), evolución mensual, ranking de líneas y mapa. Antes la evolución mensual usaba 100 %.
- **Color semántico consistente** con una sola función (`sla_color`): verde ≥ 80 %, ámbar 60–79,9 %, rojo < 60 %. «A tiempo» es verde en todas las páginas (antes era azul en el Resumen) y «Cerrados» ya no usa verde en la curva mensual.
- Las prioridades (boxplot) y la antigüedad de pendientes usan escalas ordinales azules (más oscuro = más urgente / más antiguo) en lugar de ámbar y rojo, que quedan reservados para estados de alerta.
- **KPI propios por página**: Resumen conserva los globales; Cumplimiento muestra cumplimiento de prioridades urgentes y de largo plazo, cierres atrasados y tipo más rezagado; Territorio muestra líneas bajo la meta, cumplimiento por CTE (Centro y Suroccidente), torres con vencidos y departamento más crítico. Los KPI de cumplimiento indican la distancia a la meta en puntos.
- **Contexto visible en cada página**: periodo, fecha de corte, criterio `marca = normal` y meta.
- **2023 marcado como año parcial** (avisos hasta mayo) en el gráfico anual y en el filtro de año.
- **Mapa municipal**: el popup separaba mal los conteos (sumaba atrasados abiertos y cerrados bajo «Cerrados atrasados»); ahora muestra pendientes, vencidos y cerrados atrasados por separado. El encuadre se ajusta a los datos y no a todo el país, y las capitales se dibujan solo para los departamentos presentes.

### Mapa de la red de transmisión (página «Territorio y red»)
- Cada una de las 40 líneas se dibuja uniendo, en orden de numeración, las torres que registran avisos (T4 → 4, T120-V → 120). Es un trazado aproximado, no el trazado oficial.
- Color de la línea: cumplimiento de sus cierres frente a la meta; gris si tiene menos de 10 cierres (no evaluable).
- Grosor: avisos pendientes de la línea.
- Puntos rojos: torres con pendientes vencidos (capa activable). Capa opcional con todas las torres con avisos.
- El ranking «líneas de menor cumplimiento» es clicable: al seleccionar una línea se filtra todo el tablero, incluidos los mapas.
- Hallazgo con la base completa: ninguna de las 33 líneas evaluables alcanza la meta del 80 %.

## Versión 2.1 — mapa territorial integrado
- Se incorporó `integrated_map(d)` para reunir en un solo mapa las capas de las antiguas funciones `network_map(d)` y `geo_map(d)`.
- Capas disponibles: líneas de transmisión coloreadas por cumplimiento; torres con pendientes vencidos; todas las torres con avisos (desactivada inicialmente); municipios con volumen y porcentaje pendiente; capitales departamentales; límites departamentales y fondos cartográficos.
- Los tooltips y ventanas emergentes conservan métricas de línea, torre y municipio. El control de capas permite activar o desactivar grupos para evitar saturación visual.
- La sección Territorio y red muestra un solo mapa integrado a ancho completo. Las gráficas de cumplimiento por línea y acumulación departamental se ubican juntas debajo del mapa, seguidas por la tabla de municipios.
- Se conserva el trazado aproximado de líneas según la numeración de las torres; no debe interpretarse como geometría oficial de la infraestructura.

## Versión 2.2 — detalle municipal y optimización visual
- Los popups municipales amplían los indicadores de gestión: avisos totales, cerrados, pendientes, vencidos, pendientes dentro del plazo, cierres a tiempo y tardíos, porcentaje de pendientes, porcentaje de cierres a tiempo, antigüedad mediana y máxima de pendientes, tiempo mediano de cierre, líneas, torres, tipo y prioridad predominantes y CTE.
- El mapa integrado reduce su altura de 520 a 450 px.
- La gráfica de cumplimiento por línea reduce su altura de 440 a 350 px y la gráfica departamental de 370 a 320 px, manteniendo la tipografía y las etiquetas.
- Los títulos identifican el contenido de cada visualización; los resultados y conclusiones se trasladan a los textos descriptivos inferiores.
- Se elimina la tabla Top 15 de municipios prioritarios de la sección Territorio y red.

## Versión 2.3.0 — ventanas de gestión para torres y municipios
- Se consolidan los marcadores de torres en una sola capa visible y un único filtro: **Torres · gestión total**. Se eliminan las capas duplicadas de torres vencidas y todas las torres.
- Cada torre presenta una ficha única con línea, municipio, departamento, avisos totales, cerrados, pendientes, pendientes dentro del plazo, vencidos, cierres a tiempo y atrasados, cumplimiento, antigüedad mediana y máxima de pendientes, tiempo mediano de cierre, tipo y prioridad predominantes y CTE.
- La ficha municipal ampliada pasa a mostrarse en el tooltip de consulta directa, en lugar de dejar los indicadores completos únicamente en una ventana emergente de clic.
- La estructura de agregación de torres se valida contra la base `avisos.csv`; se compila `app.py` sin errores de sintaxis.

## Versión 2.3.1 — posición uniforme de fichas en el mapa
- Las fichas de líneas, torres y municipios se muestran a la derecha del elemento consultado, con un desplazamiento uniforme.
- Se incorpora un estilo común de lectura: fondo blanco, ancho controlado, texto ajustable y desplazamiento interno para contenidos extensos.
- Se agrega un ajuste automático del encuadre del mapa cuando una ficha se aproxima a los bordes, para mantenerla dentro del área visible.
- Se conserva el contenido y la lógica de los indicadores de gestión de cada ficha.

## Versión 2.3.2 — corrección del mapa en blanco

Se corrigió el orden de ejecución del JavaScript de posicionamiento de las fichas emergentes. El evento `tooltipopen` ahora se registra de forma diferida, una vez que Folium/Leaflet ha creado el objeto del mapa. En la versión anterior, el código podía intentar ejecutar `map.on(...)` antes de que existiera la variable del mapa y detener la inicialización, dejando visible únicamente la leyenda.

Se mantienen las fichas orientadas a la derecha para líneas, torres y municipios, con ajuste automático para mantenerlas dentro del área visible.

Antes de publicar, ejecutar localmente y comprobar que carguen las teselas, líneas, torres y municipios. La verificación de esta entrega incluye compilación sintáctica de Python y comprobación del orden del JavaScript generado en una instancia Folium mínima; el entorno de revisión no dispone de Dash para levantar el tablero completo.

## Versión 2.4.0 — etiquetas sin superposición y mapa con lectura filtrable

### Línea de meta sin tapar etiquetas
- Nueva regla común `labels_clear_of_meta()`: si una barra termina justo antes de la meta, su etiqueta exterior quedaría cruzada por la línea punteada. En ese caso la cifra se escribe dentro de la barra, en blanco. Si la barra es muy corta, se escribe justo después de la línea. Ejemplo: «Seis años · 74,8 %» en el cumplimiento por prioridad.
- El rótulo «Meta 80 %» se ubica fuera del área de datos (`meta_label_outside()`), en el margen derecho de las gráficas verticales y en el margen superior de las horizontales, para que no tape barras ni puntos.
- La línea de meta se dibuja detrás de las barras (`layer="below"`).
- Se aplica a: cumplimiento por prioridad, atraso por tipo (máximo tolerable 20 %), cumplimiento por línea y evolución mensual.

### Mapa integrado: leyenda interactiva
- La leyenda fija se reemplaza por el panel **«Filtrar la lectura del mapa»**, dentro del mapa. Cada categoría es una casilla que muestra u oculta sus elementos, sin recargar el tablero:
  - Líneas: crítica (< 60 %), en riesgo (60–79,9 %), cumple (≥ 80 %), no evaluable (< 10 cierres).
  - Torres: con pendientes vencidos, con pendientes no vencidos, sin pendientes.
  - Municipios: alto (≥ 67 % pendiente), medio (34–66 %), bajo (≤ 33 %).
  - Referencias: capitales y límites departamentales.
- Cada categoría muestra cuántos elementos tiene con los filtros vigentes; las vacías aparecen atenuadas.
- Vistas rápidas: «Ver todo», «Solo lo crítico» (solo lo rojo y las referencias) y «Ocultar todo». Cada familia tiene una casilla general.
- El panel se puede plegar. En pantallas angostas inicia plegado. En escritorio, el encuadre inicial deja libre la franja que ocupa el panel.
- Orden de dibujo: municipios al fondo, luego líneas y torres encima, para que los círculos municipales no tapen la red. Dentro de cada familia, lo crítico queda encima.
- El control de capas de Leaflet (arriba a la derecha) queda solo para elegir el fondo: relieve y vías, fondo claro o calles.
- Altura del mapa: 560 px (antes 450 px), para alojar el panel.

### Guía «¿Cómo leer este mapa?»
- Bloque desplegable sobre el mapa, con cuatro tarjetas en lenguaje sencillo: líneas, torres, municipios y cómo usar el panel. Incluye un ejemplo de lectura.

Verificación: compilación de Python, ejecución de `integrated_map()` sobre `avisos.csv` con bibliotecas simuladas (40 líneas: 28 críticas, 5 en riesgo, 0 cumplen, 7 no evaluables; 1.430 torres; 149 municipios) y prueba del panel en Chrome sin interfaz con un Leaflet simulado. El entorno de revisión no tiene Dash, Plotly ni Folium, así que antes de publicar hay que levantar el tablero localmente y revisarlo a simple vista.

## Versión 2.4.1 — ajustes de la línea de meta y escala de tiempos
- **Rótulo de la meta en «Cumplimiento por prioridad»**: «Meta 80 %» se ubica justo encima de la línea punteada, sobre la última barra, y ya no en el margen derecho. Si la última barra superara la meta, el rótulo pasa sobre la primera barra (`meta_label_above_line()`).
- **Línea de meta por encima de las barras** (`meta_line()`): la línea se dibuja sobre las barras en cumplimiento por prioridad, atraso por tipo, cumplimiento por línea y evolución mensual. Un trazo blanco debajo de la línea punteada la hace visible sobre cualquier color de barra.
- **«Distribución real de tiempos de atención según prioridad»**: la escala ya no se corta en el percentil 95. Ahora llega hasta el caso más largo (+4 %), de modo que las cajas de Tres años y Seis años (hasta unos 3.700 días) se ven completas, con bigotes y puntos atípicos. La altura pasa de 350 a 380 px y las marcas del eje van cada 500 días.

## Versión 2.4.2 — etiquetas dentro del recuadro y sin iconos
- **«Acumulación de pendientes y cierres tardíos por departamento»**: el eje X se fija desde 0 hasta el total máximo (+6 %). Antes el rango automático podía empezar en negativo, lo que separaba los nombres de sus barras y los sacaba del recuadro.
- Nueva función `left_margin_for()`: calcula el margen izquierdo según el nombre más largo del eje. Se aplica a departamentos, atraso por tipo y cumplimiento por línea.
- Se retiraron los iconos y símbolos decorativos: 💡 y 🔎 del aviso de filtros, ↺ de «Restablecer filtros», ☰ del botón «Filtros» en el celular y ▴/▾ del panel del mapa, donde ahora dice «ocultar» o «mostrar».

## Versión 2.5.0 — hallazgos en «Pendientes por cumplir»
- Nueva función `pending_findings()`: calcula los hallazgos del backlog con los filtros vigentes y los muestra como en las demás páginas (título con el hallazgo y texto de análisis bajo cada gráfica).
  - **Situación de los pendientes**: vencidos frente al total, atraso mediano y máximo sobre el plazo, y prioridad que más aporta vencidos.
  - **Envejecimiento**: el título indica el % de pendientes con más de un año abierto. El texto da el grupo más numeroso, los avisos con más de 4 años y cómo cambia la proporción vencida con la antigüedad (solo si la diferencia es relevante).
  - **Tipología**: el título indica los dos tipos que concentran el backlog. El texto da el tipo con más vencidos y los tipos pequeños con mayoría vencida (cierres puntuales).
- Nueva tarjeta **«Síntesis del backlog para la toma de decisiones»** (magnitud, envejecimiento y prioridad de intervención), con el mismo formato del Resumen gerencial.
- Las frases se ajustan a cada filtro: sin datos, solo vencidos, solo dentro del plazo, etc. Se omiten las cláusulas con cero casos. Se probaron 48 combinaciones de filtros sin errores.

## Versión 2.5.1 — hallazgos en el «Resumen gerencial»
- Nueva función `summary_findings()`: análisis bajo cada gráfica, calculado con los filtros vigentes.
  - **Estado de los avisos**: cerrados frente a abiertos (y vencidos), y en qué año la tasa de cierre por año de aviso baja de la meta.
  - **Cumplimiento de cierres**: cierres fuera de plazo, mejor y peor año de cierre (años con 30 cierres o más) y cuántos años alcanzan la meta.
  - **Ritmo mensual**: el título pasa a ser un hallazgo (ingresos promedio frente a cierres promedio por mes). El texto da los meses con más ingresos que cierres, el mayor pico y cuántos avisos se cerraron ese mes, y el balance de los últimos 12 meses. El balance se omite si hay un filtro de estado activo, porque no sería representativo.
  - **Abiertos por año**: qué parte de los abiertos proviene de los tres años más recientes y cuántos quedan de años anteriores.
- La «Síntesis ejecutiva» usa el mismo formato que en Pendientes (etiqueta en negrita, sin viñeta duplicada) y suma el punto «Ritmo de atención».
- Se probaron 75 combinaciones de filtros sin errores.

## Versión 2.5.2 — publicación en GitHub y Render
- `render.yaml` actualizado al formato vigente (`runtime: python`, plan gratuito, despliegue automático) y arranque con `gunicorn app:server --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`, adecuado para los 512 MB del plan gratuito y para la primera carga del mapa.
- `.python-version` fija Python 3.13 en el servidor.
- `requirements.txt` con límites superiores de versión (por ejemplo, `dash>=4.0,<5`) para que una versión mayor futura no cambie el tablero sin aviso.
- `.gitignore` excluye cachés de Python, entornos virtuales y configuraciones del editor.
- El logo de la barra lateral se redujo de 950 KB a 130 KB (400 px) para cargar más rápido en el celular, y se añadió `assets/favicon.ico` con el emblema ENERGY.
- No se modificaron cálculos, gráficas, filtros ni textos del tablero. Se probaron 40 combinaciones de página y filtros sin errores.

## Versión 2.6.0 — menú de navegación desplegable en celular
- **Corrección**: en pantallas de hasta 760 px la barra lateral quedaba oculta y una regla posterior de `style.css` también ocultaba el botón para abrirla, por lo que en el celular no había forma de cambiar de página.
- Nueva **barra superior fija** en celular con el emblema ENERGY, el nombre de la página actual y el botón **Menú**.
- El botón despliega un **menú completo de ancho total** bajo la barra: navegación entre las cinco páginas (con áreas táctiles amplias), filtros de gestión y autores. El fondo del tablero se oscurece mientras el menú está abierto.
- El menú se cierra solo al elegir una página, con el botón **Cerrar** o con **Ver tablero** (debajo de los filtros), para ver el resultado del filtrado.
- En escritorio no cambia nada: la barra lateral sigue fija a la izquierda.
