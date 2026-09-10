# Generative AI Studio — Diseño

**Fecha:** 2026-09-10
**Origen:** Caso Práctico Unidad 3 (Generative AI) — Instituto Europeo de Posgrado
**Estado:** Aprobado para pasar a plan de implementación

## 1. Objetivo

Aplicación web funcional (prototipo real, no solo documentado) que permita a diseñadores,
redactores y aprobadores de una empresa de marketing/publicidad:

1. Generar imágenes a partir de descripciones de texto, con selección de estilo, usando
   **Stable Diffusion** vía **Amazon Bedrock**.
2. Editar/mejorar contenido de texto existente (resumir, expandir, corregir, generar
   variaciones) usando **Claude** vía **Amazon Bedrock**.

Amazon Bedrock actúa como plataforma unificada de acceso a ambos modelos; no son
alternativas entre sí, son piezas complementarias del mismo flujo.

## 2. Alcance

**Incluido (bloques 1 y 2 completos):**
- Generación de imágenes con selector de estilo y galería descargable.
- Edición de texto con las 4 acciones del enunciado (resumir, expandir, corregir,
  variar) e historial de versiones con comparación y reversión.

**Incluido (bloques 3 y 4, versión básica):**
- Acceso protegido por contraseña con 3 roles (diseñador, redactor, aprobador) vía
  `st.secrets` — cubre el requisito de "roles y permisos" y además protege el
  presupuesto de AWS al ser la app pública.
- Comentarios sobre cualquier ítem generado (imagen o texto), visibles para todos los
  roles.
- Moderación de contenido y mitigación de sesgos vía **Bedrock Guardrails** (nativo,
  sin modelo de moderación propio).
- Cifrado en reposo por defecto de AWS (S3 SSE-S3, DynamoDB) — sin cifrado aplicativo
  adicional.
- Cuota simple de generaciones por usuario/hora para prevenir abuso de la app pública.

**Fuera de alcance explícito (documentado como trabajo futuro, no se implementa):**
- Edición simultánea en tiempo real entre varios usuarios sobre el mismo ítem.
- Sistema de moderación con modelo propio (más allá de Bedrock Guardrails).
- Cifrado aplicativo adicional al cifrado en reposo nativo de AWS.
- Despliegue en infraestructura AWS propia (Lambda/EC2/Amplify) — se usa Streamlit
  Community Cloud.

## 3. Stack técnico

- **Frontend + backend:** Streamlit (Python), app multi-página. Todo el código corre
  en el servidor de Streamlit; el navegador nunca ve credenciales AWS.
- **Modelos IA:** Amazon Bedrock — Claude (edición de texto) y Stable Diffusion
  (generación de imágenes), invocados vía `boto3`.
- **Almacenamiento de imágenes:** Amazon S3 (necesario porque el disco de Streamlit
  Community Cloud no es persistente de forma fiable entre redeploys).
- **Metadatos/historial/comentarios:** Amazon DynamoDB (tabla única `content_history`).
- **Despliegue:** Streamlit Community Cloud, conectado a este repo de GitHub, URL
  pública. Secretos (contraseñas de rol, credenciales AWS) gestionados vía el panel de
  secrets de Streamlit Cloud (no se commitean).

## 4. Arquitectura

```
Usuario (navegador)
   → Streamlit App (Community Cloud)
       → boto3 → Amazon Bedrock (Claude, Stable Diffusion, Guardrails)
       → boto3 → Amazon S3 (imágenes generadas)
       → boto3 → Amazon DynamoDB (historial, comentarios, metadatos)
```

## 5. Componentes

```
app.py                     # login (contraseña + rol) y navegación
pages/
  1_Generar_Imagen.py      # UI bloque 1
  2_Editar_Contenido.py    # UI bloque 2
  3_Galeria_Historial.py   # UI transversal: galería + historial + comentarios
lib/
  auth.py                  # verificación de contraseña/rol contra st.secrets
  bedrock_client.py        # wrappers boto3: invoke_stable_diffusion(), invoke_claude()
  storage.py                # subir/leer imágenes en S3
  history.py                # leer/escribir registros en DynamoDB
  moderation.py             # aplica Bedrock Guardrails antes de generar/guardar
scripts/
  check_bedrock_access.py  # smoke test manual de acceso a modelos antes de la demo
tests/
  test_bedrock_client.py
  test_storage.py
  test_history.py
  test_moderation.py
```

Responsabilidad de cada módulo `lib/`:
- **`auth.py`** — cotejar contraseña contra `st.secrets`, determinar rol, guardarlo en
  `st.session_state`. El resto de la app consulta el rol para mostrar/ocultar acciones
  (p. ej. solo "aprobador" puede marcar contenido como aprobado).
- **`bedrock_client.py`** — único punto de contacto con Bedrock; centraliza reintentos y
  manejo de errores de la API.
- **`storage.py`** — sube/lee binarios de imagen en S3 (`s3://bucket/images/{user}/{uuid}.png`).
- **`history.py`** — CRUD sobre la tabla DynamoDB `content_history`.
- **`moderation.py`** — invoca los modelos con el guardrail configurado y traduce
  respuestas de intervención a mensajes legibles.

## 6. Flujo de datos

**Generación de imagen:**
1. Usuario autenticado rellena prompt + estilo.
2. `bedrock_client.invoke_stable_diffusion(prompt, style)` (con guardrail aplicado) →
   si el guardrail interviene, se muestra el aviso y no se continúa.
3. `storage.save_image()` sube el binario a S3.
4. `history.log_generation()` escribe un ítem en DynamoDB.
5. La UI muestra la imagen devuelta directamente (sin releer de S3).

**Edición de contenido:**
1. Usuario pega/edita texto + elige acción.
2. `bedrock_client.invoke_claude(text, accion)` (con guardrail aplicado) devuelve el
   texto editado.
3. `history.log_edit()` guarda versión anterior + nueva, encadenadas por
   `version_anterior_id`, para permitir comparar y revertir.
4. La UI muestra un diff simple y botones aceptar/descartar/revertir.

## 7. Esquema de datos

**DynamoDB — tabla `content_history`:**
- Partition key: `id` (uuid)
- Atributos: `tipo` (`imagen`|`texto`), `usuario`, `rol`, `prompt_o_texto_original`,
  `resultado` (texto o `s3_key`), `version_anterior_id` (opcional), `comentarios`
  (lista), `timestamp`, `estado_moderacion`.

**S3 — bucket de imágenes:**
- Key pattern: `images/{usuario}/{uuid}.png`
- Cifrado: SSE-S3 por defecto.

## 8. Manejo de errores

- `ThrottlingException` → reintento con backoff exponencial (2-3 intentos) antes de
  mostrar error.
- `AccessDeniedException` (modelo no habilitado) → mensaje explícito indicando que hay
  que solicitar acceso al modelo en la consola de Bedrock.
- `ValidationException` → se informa al usuario para ajustar el prompt; no se loguea
  contenido sensible.
- Fallos de S3/DynamoDB tras una generación exitosa → se muestra igualmente el
  resultado al usuario, con aviso de que no se pudo guardar en el historial (no se
  descarta una respuesta ya pagada a Bedrock).

## 9. Seguridad, roles y moderación

- Acceso a la app protegido por contraseña compartida por rol (`diseñador`,
  `redactor`, `aprobador`), definida en `st.secrets`.
- Moderación de contenido y mitigación de sesgos delegada a **Bedrock Guardrails**
  (configurado una vez en la consola AWS): filtra contenido dañino, PII, y temas
  denegados (incluye un denied-topic orientado a evitar imitación de estilos de
  artistas/personajes protegidos, como control preventivo de derechos de autor — no
  hay detección automática infalible de infracción de copyright).
- Cifrado en reposo nativo de AWS (S3 SSE-S3, DynamoDB) activado por configuración, sin
  cifrado aplicativo adicional.
- Cuota de N generaciones/usuario/hora consultando `history.py` antes de llamar a
  Bedrock, para proteger el presupuesto de la app pública.

## 10. Testing

- `lib/` testeado con `pytest` + `moto` (mock de AWS), sin llamadas reales ni coste.
- `scripts/check_bedrock_access.py`: smoke test manual con una llamada real mínima a
  Claude y a Stable Diffusion, para confirmar el acceso a los modelos antes de la
  demo/entrega.
- UI de Streamlit: verificación manual exploratoria del camino feliz y de los casos de
  error (guardrail bloquea, excepción de Bedrock, cuota excedida) — Streamlit no se
  presta bien a tests automatizados de UI.

## 11. Prerrequisitos de infraestructura (antes de implementar)

1. Verificar/solicitar acceso a los modelos Claude y Stable Diffusion en la consola de
   Amazon Bedrock (región a definir).
2. Crear bucket S3 para imágenes (con cifrado por defecto habilitado).
3. Crear tabla DynamoDB `content_history` (con cifrado por defecto habilitado).
4. Configurar un Guardrail en Bedrock (contenido dañino, PII, denied topics).
5. Repositorio en GitHub conectado a Streamlit Community Cloud, con secrets
   configurados (credenciales AWS, contraseñas de rol).
