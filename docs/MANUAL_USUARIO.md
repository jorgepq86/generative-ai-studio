# Manual de usuario y cobertura del caso práctico — Generative AI Studio

Este documento tiene dos partes: cómo se usa la interfaz, y una tabla de
trazabilidad que muestra, punto por punto, cómo cada requisito del
enunciado del caso práctico está cubierto por la aplicación.

---

## Parte 1 — Manual de la interfaz

### Acceso

La app pide una contraseña al entrar (`app.py`). No hay usuarios
individuales — hay **una contraseña compartida por rol**:
`diseñador`, `redactor`, `aprobador`. La contraseña que escribas determina
con qué rol entras; no hay un desplegable para elegirlo.

El menú lateral **cambia según el rol** — cada uno ve solo lo que le
corresponde:

| Rol | Páginas visibles |
|---|---|
| `diseñador` | Generar Imagen · Galería e Historial (solo sección de imágenes) |
| `redactor` | Editar Contenido · Galería e Historial (solo sección de textos) |
| `aprobador` | Galería e Historial (ambas secciones, para poder revisar y aprobar cualquier tipo de contenido) |

### Página 1 — 🖼️ Generar Imagen

`pages/1_Generar_Imagen.py`

1. Escribe una descripción detallada en el cuadro de texto ("Describe la
   imagen que quieres generar").
2. Elige un estilo del desplegable: Anime, Pintura al óleo, Realismo
   fotográfico, Boceto a lápiz, Cyberpunk.
3. Pulsa **"Generar"**.
4. La app comprueba primero que no hayas superado la cuota de la hora,
   luego genera la imagen con Stable Diffusion 3.5 Large, la pasa por el
   guardrail de moderación, y si todo está bien la muestra en pantalla con
   un botón **"Descargar imagen"**.
5. Si el guardrail bloquea el contenido, o si Bedrock devuelve un error, se
   muestra un mensaje explicativo en vez de una imagen.
6. La imagen y sus metadatos (prompt, estilo, usuario, resultado de
   moderación) quedan guardados automáticamente en el historial — no hace
   falta hacer nada más para que aparezca en la Galería (página 3).

### Página 2 — ✍️ Editar Contenido

`pages/2_Editar_Contenido.py`

1. Pega o escribe un texto en el área de edición.
2. Elige una acción: **Resumir**, **Expandir**, **Corregir gramática y
   estilo**, o **Generar variación**.
3. Pulsa **"Aplicar"**.
4. Claude procesa el texto (pasando también por el guardrail de
   moderación) y el resultado reemplaza el texto en pantalla.
5. Debajo aparece un desplegable **"Historial de versiones"** con cada
   versión anterior: acción aplicada, fecha, un **diff resaltado en color**
   (verde lo añadido, rojo tachado lo eliminado) frente a la versión
   anterior, y un botón **"Revertir a esta versión"** para volver atrás.
6. Cada edición nueva también queda guardada en el historial automáticamente.

### Página 3 — 🗂️ Galería e Historial

`pages/3_Galeria_Historial.py`

Dos pestañas:

- **Galería de imágenes**: todas las imágenes generadas por cualquier
  usuario, con su prompt, estilo, autor, y un apartado de comentarios
  debajo de cada una.
- **Historial de textos**: todas las ediciones de texto, con su acción,
  autor, fecha, y comentarios.

En ambas pestañas, cada elemento muestra:
- **Estado de aprobación**: "⏳ Pendiente de aprobación" o "✅ Aprobado
  por `<rol>` el `<fecha>`".
- Un botón **"Aprobar"** — pero **solo visible si entraste con la
  contraseña de `aprobador`**. Los roles `diseñador` y `redactor` ven el
  estado pero no el botón.
- Un cuadro de comentarios donde cualquier usuario (de cualquier rol)
  puede añadir una nota, visible para todos.

Esta página lee datos en vivo de AWS al cargar, así que no hace falta
recargar manualmente tras generar contenido en otra pestaña — solo entra o
recarga la página.

---

## Parte 2 — Cobertura del enunciado

La siguiente tabla recorre el enunciado del caso práctico punto por punto.

### 1. Generación de imágenes

| Requisito del enunciado | Estado | Dónde / cómo |
|---|---|---|
| Interfaz intuitiva para descripciones de texto detalladas | ✅ | Página "Generar Imagen" — `st.text_area` |
| Generar imágenes correspondientes utilizando **Stable Diffusion** | ✅* | `stability.sd3-5-large-v1:0` vía Bedrock (`lib/bedrock_client.py: invoke_image`). *Nota: el modelo original pedido, Stable Diffusion XL 1.0, ya no está disponible como serverless en Bedrock (solo vía endpoint de SageMaker con coste fijo por hora); se usa Stable Diffusion 3.5 Large, disponible serverless en `us-west-2` — ver `docs/AWS_SETUP.md` para el detalle completo de la búsqueda. |
| Selección de estilos/ajustes (anime, óleo, realismo...) | ✅ | 5 estilos en el desplegable de la página 1 |
| Galería para ver y descargar imágenes | ✅ | Pestaña "Galería de imágenes" (página 3) + botón "Descargar imagen" en la página 1 |

### 2. Edición de contenido

| Requisito del enunciado | Estado | Dónde / cómo |
|---|---|---|
| Integrar Claude para editar/mejorar texto existente | ✅ | **Claude Haiku 4.5** (`us.anthropic.claude-haiku-4-5-20251001-v1:0`) vía `lib/bedrock_client.py: invoke_claude` |
| Resumir, expandir, corregir gramática/estilo, variaciones | ✅ | Las 4 acciones exactas en el desplegable de la página 2 |
| Historial/seguimiento de cambios | ✅ | `lib/history.py: get_version_chain`, expander "Historial de versiones" |
| Comparar versiones anteriores | ✅ | Diff palabra por palabra (`lib/diffing.py`), coloreado, en cada versión del historial |
| Revertir versiones anteriores | ✅ | Botón "Revertir a esta versión" por cada versión |

### 3. Colaboración y flujo de trabajo

| Requisito del enunciado | Estado | Dónde / cómo |
|---|---|---|
| Múltiples usuarios acceden y trabajan en la app | ✅ (parcial, ver nota) | La app soporta múltiples sesiones concurrentes leyendo/escribiendo el mismo historial compartido en DynamoDB. **No** implementa edición colaborativa en tiempo real sobre el mismo documento (dos personas editando el mismo texto a la vez) — cada acción de generación/edición es independiente y se registra por separado. |
| Sistema de roles y permisos (diseñadores, redactores, aprobadores) | ✅ (con matiz) | 3 roles vía contraseña compartida (`lib/auth.py`) — **no** hay cuentas de usuario individuales. Solo el rol `aprobador` puede aprobar contenido (`lib/history.py: approve_item`, botón condicional en página 3); diseñador/redactor pueden generar/editar pero no aprobar. |
| Comentarios y notas para colaboración | ✅ | Sección de comentarios en cada elemento de la Galería/Historial (página 3), visible y editable por cualquier rol |

### 4. Consideraciones éticas y de seguridad

| Requisito del enunciado | Estado | Dónde / cómo |
|---|---|---|
| Privacidad y seguridad de datos (cifrado de imágenes y contenido) | ✅ | Cifrado en reposo con valores por defecto de AWS: S3 con `ServerSideEncryption=AES256` (`lib/storage.py`), DynamoDB con SSE habilitado (`--sse-specification Enabled=true` en la creación de la tabla) |
| Políticas de uso ético — mitigación de sesgos | ✅ | Denied topic "Contenido discriminatorio o con sesgos" en el guardrail de Bedrock (ver `docs/AWS_SETUP.md`, paso 8) |
| Políticas de uso ético — protección de derechos de autor | ✅ | Denied topic "Imitación de artistas o personajes con derechos de autor" en el mismo guardrail |
| Moderación y filtrado de contenido (imágenes y texto inapropiado/dañino) | ✅ | Bedrock Guardrails aplicado a **ambos** modelos: inline en `invoke_model` para Claude, y vía la API independiente `ApplyGuardrail` para las imágenes generadas (Stable Diffusion no acepta guardrails inline) — `lib/moderation.py`, `lib/bedrock_client.py: apply_guardrail_image`. Contenido bloqueado nunca llega al usuario (`ModerationBlocked`). |

---

## Limitaciones conocidas (transparencia para la memoria del caso)

- **No hay cuentas de usuario individuales.** El "sistema de roles" es una
  contraseña compartida por rol, no autenticación por persona. Es
  suficiente para diferenciar permisos por tipo de usuario, pero no para
  saber *qué persona concreta* hizo una acción dentro de un rol.
- **No hay edición colaborativa en tiempo real** sobre un mismo documento
  (tipo Google Docs). Cada generación/edición es una operación
  independiente que queda registrada; varios usuarios pueden trabajar en
  paralelo sobre elementos distintos sin conflicto.
- **El modelo de imágenes no es literalmente "Stable Diffusion XL"** como
  sugiere el enunciado original, sino Stable Diffusion 3.5 Large (misma
  familia de modelos, mismo proveedor, Stability AI) — la versión pedida
  ya no se ofrece en Bedrock sin un coste fijo de infraestructura
  incompatible con este proyecto. Detalle completo en `docs/AWS_SETUP.md`.
- **Los comentarios tienen una condición de carrera leve**: si dos personas
  comentan lo mismo exactamente al mismo tiempo, uno de los comentarios
  podría perderse. Aceptado como riesgo razonable dado que no hay edición
  simultánea real en esta app.
