# Agente Shurman 007

Entrega del 19 de octubre de 2026. La web está en `public/index.html`: se puede abrir directamente en un navegador. No requiere instalación. El primer cero está tachado visualmente; el nombre accesible conserva los tres dígitos.

## Estado verificado

Se recuperó el Markdown adjunto de la conversación; los ZIP anteriores no estaban accesibles. Se reconstruyó la web. Se validó una petición HTTPS independiente, sin cookies ni login, al endpoint que declara el HTML oficial: 367 registros recibidos, tantos como recordsFiltered y recordsTotal. No se ha ejecutado todavía desde GitHub Actions ni se ha publicado una web remota. No existe garantía de disponibilidad futura de esa interfaz interna.

La entrega muestra el histórico importado y su fecha, sin fingir conexión en directo. Cuatro pruebas automatizadas cubren clasificación de eventos, duplicados, truncamiento y anuncios de acciones futuras. La auditoría textual del paquete no encontró el número objetivo. El histórico bruto y el informe privado no se incluyen en el paquete desplegable.

## Publicar gratis con GitHub Pages

1. Crear un repositorio nuevo y público con nombre neutro. GitHub Free ofrece Pages para repositorios públicos. No reutilizar un repositorio que haya contenido la identidad anterior: el historial conserva borrados. La cuenta propietaria será visible; no se garantiza anonimato del titular.
2. Subir el contenido de este paquete, incluyendo `.github/workflows/update.yml`. No subir archivos privados, el Markdown original ni informes. La carpeta `public` es lo único que se sube como artefacto de Pages.
3. En Settings → Pages → Build and deployment, seleccionar GitHub Actions.
4. En Settings → Secrets and variables → Actions, crear el secreto `TARGET_NUMBER` con el número real. No escribirlo en código, nombres de archivos, mensajes de commit ni variables públicas. El motor no requiere el secreto para calcular estadísticas generales.
5. Tras valorar las condiciones de la fuente, crear la variable `SOURCE_ENABLED` con valor `true`. Por defecto la tarea está desactivada. Ejecutar Actions → Actualizar informe → Run workflow para verificar la conexión desde GitHub. Si falla, revisar el estado sin imprimir variables o respuestas completas.
6. Mantener `PUBLISH_COARSE_FORECAST` sin definir para máxima privacidad. Para publicar únicamente el mes o meses estimados, establecerla en `true`, aceptando el riesgo de inferencia explicado abajo. La estimación se calcula exclusivamente en Python durante Actions.
7. Tras una ejecución correcta, abrir la URL que muestra el paso Publicar. El horario configurado es 21:17 UTC de lunes a jueves: 23:17 en Madrid durante horario de verano y 22:17 en invierno. Son dos solicitudes por ejecución: página y JSON, sin reintentos. No depende del número de visitantes.

Las tareas programadas pueden retrasarse; GitHub puede desactivar programaciones por inactividad. Revisar Actions periódicamente. Si la fuente devuelve un error, exige login, cambia de estructura o supera los 2.000 mensajes solicitados, la tarea falla y no reemplaza la publicación. No aumentar consultas repetidamente ni sortear restricciones. Una consulta parcial nunca se publica como histórico completo.

Si se desea solo alojamiento estático, se puede subir exclusivamente `public` mediante Cloudflare Pages Direct Upload. Esa alternativa no actualiza sola: el flujo incluido está preparado para GitHub Pages. Los planes y límites pueden cambiar.

## Uso privado y predicción

Para generar un informe privado, ejecutar el motor en un equipo de confianza con `TARGET_NUMBER` en el entorno y `PRIVATE_REPORT` apuntando a una ruta fuera de `public`. Comando: `python3 server/engine.py /ruta/al/historico.md public`. No guardar ese informe como artefacto de un repositorio público. Para introducir el secreto local sin dejarlo en el historial del terminal, usar entrada oculta o un gestor de secretos; no pegarlo en una orden.

La predicción emplea el avance de numeración de jornadas cerradas. Los cuartiles del ritmo diario producen dos escenarios; se convierten a fechas suponiendo sesiones de lunes a miércoles e incluyendo los jueves de noviembre anunciados en el histórico. Solo se exporta mes/año. No es una probabilidad calibrada. Falta validar un calendario oficial completo, festivos, segundos llamamientos, atrasos y cambios de tribunal. Si el objetivo ya ha sido alcanzado por la numeración, no se afirma que esa persona se haya examinado.

No se fuerza una fecha precisa ni se reconstruye una cifra exacta de ausentes. Las retiradas se cuentan separadas de los terminados; las exclusiones también. Una entrada con retirada inmediata pertenece a ambas categorías. Se deduplica por notificación y por persona/jornada. Las incorporaciones a sala, listas de presentes, convocatorias y notas no son entradas al ejercicio. Los anuncios «cuando finalice» no son finales.

Las medias usan jornadas con apertura y cierre explícitos; la jornada abierta queda fuera. El avance es la diferencia entre máximos observados de jornadas consecutivas, incluyendo un llamamiento explícito sin presencia. Se excluye el primer avance por falta de referencia previa. Este indicador puede reflejar huecos y no equivale a exámenes realizados. Una ausencia explícita en un llamamiento tampoco prueba una ausencia definitiva. El motor no resuelve cambios de llamamiento ni numeraciones reiniciadas: revisar antes de seguir utilizándolo en otra fase.

## Privacidad

El navegador recibe exclusivamente fecha de cobertura, último ejercicio con desenlace, medias, número de jornadas y el texto de predicción permitido. No recibe objetivo, distancia, porcentaje, nombres, notas, temas, listas ni mensajes originales. No hace peticiones a Registradores. No usa analítica ni fuentes externas.

El secreto por sí solo no garantiza anonimato: incluso un mes estimado combinado con el ritmo y la lista pública puede acotar candidatos; sucesivas publicaciones pueden aumentar ese riesgo. Por eso el modo inicial no publica ninguna predicción dependiente del objetivo. Para compartir una estimación sensible, utilizar acceso autenticado real, nunca una contraseña en JavaScript o una URL supuestamente secreta. `noindex` es una petición a buscadores, no protección de acceso. GitHub Pages es público aunque el código fuente fuese privado según el plan.

El motor oculta el último número si coincide con el secreto y bloquea salidas que contengan sus dígitos. Este control es defensa adicional, no demostración de anonimato. No guardar registros de depuración ni subir el entorno completo. Revisar cambios del motor antes de ejecutarlos con secretos; personas con permisos para modificar workflows pueden intentar extraerlos. Limitar colaboradores.

## Condiciones y limitaciones de la fuente

El aviso legal reserva derechos y restringe la reproducción, transformación y puesta a disposición pública de contenidos sin autorización escrita. También prohíbe cargas desproporcionadas. El bajo volumen de consultas reduce carga, pero no concede una licencia. No se ha acreditado autorización de reutilización ni una API pública con garantías. Se recomienda aclarar el uso previsto con el Colegio antes de activar publicación y consultas periódicas; este documento no ofrece una conclusión jurídica sobre la licitud de las estadísticas derivadas.

Se intentó consultar robots.txt: la respuesta observada redirigió a una página de acceso, por lo que no se verificó una política robots utilizable. No se interpreta como permiso. No se reutilizan logos ni se retransmite íntegramente el seguimiento. La web identifica su carácter independiente y enlaza la fuente.

## Referencias consultadas

- Fuente: https://www.registradores.org/el-colegio/oposiciones/seguimiento-oposicion?idOposicion=6
- Condiciones: https://www.registradores.org/aviso-legal
- GitHub Pages y workflows: https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
- Secretos: https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets
- Cloudflare Direct Upload: https://developers.cloudflare.com/pages/get-start/direct-upload/
- Límites: https://developers.cloudflare.com/pages/platform/limits/
