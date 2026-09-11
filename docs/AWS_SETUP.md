# Manual de configuración de AWS — Generative AI Studio

Guía completa para crear una cuenta de AWS nueva y dejarla lista para
desplegar Generative AI Studio. Sigue los pasos en orden — cada uno depende
del anterior. Al final tendrás todos los valores que necesitas pegar en
`.streamlit/secrets.toml`.

> Tiempo estimado: 30-45 minutos (la mayoría es esperar confirmaciones por
> correo/consola, no trabajo activo).

---

## 0. Antes de empezar

Necesitas:
- Un correo electrónico que no esté ya asociado a otra cuenta de AWS.
- Una tarjeta de crédito/débito (AWS la pide para crear la cuenta, aunque
  este proyecto cabe cómodamente en la capa gratuita para pruebas).
- Un teléfono para verificación por SMS/llamada.

**Coste esperado**: Bedrock cobra por token/imagen generada (no hay capa
gratuita permanente para los modelos), S3/DynamoDB tienen capa gratuita
generosa. Para uso de pruebas (decenas de generaciones), el coste típico
es de unos pocos dólares al mes. Configura una alerta de facturación (paso 2)
para evitar sorpresas.

---

## 1. Crear la cuenta de AWS

1. Ve a **https://aws.amazon.com/** → "Crear una cuenta de AWS".
2. Introduce tu correo electrónico y elige un nombre para la cuenta (por
   ejemplo, `genai-studio`).
3. Verifica el correo con el código que te envían.
4. Crea una contraseña para el **usuario raíz (root)** — guárdala en un
   gestor de contraseñas, la usarás poco pero es la de más privilegios.
5. Rellena los datos de contacto (tipo de cuenta: "Personal" está bien para
   este caso).
6. Introduce los datos de la tarjeta.
7. Verifica tu identidad por SMS o llamada.
8. Elige el plan de soporte **"Basic support - Free"**.
9. Espera el correo de confirmación de que la cuenta está activa (puede
   tardar unos minutos).

## 2. Asegurar la cuenta y activar alertas de gasto

Con el usuario **root** recién creado, antes de hacer nada más:

1. **Activa MFA (autenticación multifactor) en el usuario root**:
   Consola de AWS → esquina superior derecha (tu nombre de cuenta) →
   "Security credentials" → "Multi-factor authentication (MFA)" → "Assign MFA
   device". Usa una app como Google Authenticator o Authy.
2. **Configura una alerta de facturación**:
   Consola → busca "Billing" → "Billing preferences" → activa "Receive
   Free Tier Usage Alerts" y "Receive Billing Alerts". Luego ve a
   "Budgets" → "Create budget" → "Cost budget" → pon un límite mensual
   (por ejemplo, $20) y tu correo para el aviso.
3. **Elige tu región principal**: este proyecto usa `us-west-2` (Oregón)
   por defecto, porque ahí está disponible **Stable Diffusion 3.5 Large** (el
   modelo de imágenes de Stability AI que usa la app — ver la nota más
   abajo). Claude también es accesible desde esta región vía su inference
   profile multi-región. No cambies de región a menos que hayas verificado
   que Stable Diffusion 3.5 Large también está disponible ahí — si no, la app
   fallará al generar imágenes.

## 3. Instalar y configurar el AWS CLI

1. Instala el AWS CLI v2:
   - macOS: `brew install awscli` (o el instalador oficial en
     https://aws.amazon.com/cli/)
   - Verifica: `aws --version`
2. **No crees credenciales de administrador en tu máquina.** Para los
   comandos de este manual (crear bucket, tabla, etc.) usa en su lugar
   **AWS CloudShell**, que corre en el navegador ya autenticado con tu
   sesión de consola — sin generar ningún access key de administrador:
   - Inicia sesión en la consola de AWS.
   - Arriba a la derecha, icono de terminal → **CloudShell**.
   - Espera unos segundos a que arranque — ya tienes AWS CLI instalado y
     configurado con tu identidad de consola.
   - Ejecuta ahí mismo, en la terminal de CloudShell, todos los comandos
     `aws ...` de este manual (secciones 5, 6, 7).
3. Verifica que funciona:
   ```bash
   aws sts get-caller-identity
   ```
   Deberías ver tu `Account`, `UserId` y `Arn`.

> No necesitas instalar el AWS CLI en tu propio equipo para seguir este
> manual — solo lo necesitarás localmente más adelante para desarrollo
> (paso 11), donde sí usarás las credenciales limitadas del usuario
> `genai-studio-app` (paso 5), nunca credenciales de administrador.

## 4. Activar los modelos de Bedrock

AWS retiró la pantalla manual de "Model access": los modelos serverless de
Bedrock (Claude, Stable Diffusion 3.5 Large) se activan automáticamente en toda
cuenta la primera vez que se invocan — no hay nada que aprobar de antemano.
La primera vez que invocas Claude desde una cuenta nueva, puede pedirte que
rellenes un breve formulario de "caso de uso" — ocurre automáticamente, no
hay que activarlo por separado.

**Cómo probarlos en la práctica** — usa el Playground de la consola (no
necesitas el usuario IAM de la app todavía para esto):

1. Consola de AWS → Amazon Bedrock → confirma que estás en `us-west-2`.
2. Menú lateral → "Chat / Text playground" → abre **Claude Haiku 4.5** →
   envía un mensaje de prueba ("hola") — si aparece el formulario de caso
   de uso, rellénalo brevemente y reenvía.
3. Menú lateral → "Image playground" (o "Model catalog" → pestaña
   "Serverless" → filtra por "Output modalities = Image" → busca **Stable
   Image Core**) → genera una imagen de prueba con cualquier prompt.
4. No hace falta esperar "Access granted" en ninguna pantalla — si el
   playground responde, el modelo ya está activo para la cuenta.

> **Nota sobre el modelo de imágenes:** el enunciado original de este caso
> práctico pide Stable Diffusion. Otras opciones descartadas durante la
> búsqueda, por si te sirve de referencia:
> - **Stable Diffusion XL 1.0**: ya no se ofrece como modelo serverless de
>   Bedrock — solo vía AWS Marketplace, desplegado como endpoint dedicado
>   de SageMaker con coste fijo por hora (`ml.p5.48xlarge` a partir de
>   ~$137/hora **de software**, corriendo esté en uso o no).
> - **Amazon Nova Canvas**: serverless y sin coste fijo, pero está marcado
>   "Legacy" y AWS revoca el acceso a modelos legacy sin uso activo en los
>   últimos 30 días — no es fiable para un proyecto que no se usa a diario.
> - **Stable Image Core/Ultra**: serverless, de Stability AI, sin marca
>   "Legacy" — funcionan bien, pero no se llaman literalmente "Stable
>   Diffusion".
>
> La app usa **Stable Diffusion 3.5 Large** (`stability.sd3-5-large-v1:0`),
> serverless y disponible en `us-west-2` — por eso el proyecto usa esa
> región en vez de `us-east-1`.

> **Nota sobre Claude e inference profiles:** los modelos Anthropic más
> recientes en Bedrock ya no se pueden invocar por su ID de modelo directo —
> AWS devuelve `ValidationException: ... on-demand throughput isn't
> supported`. Hay que usar el **"inference profile"** correspondiente, cuyo
> ID lleva un prefijo de región (`us.` para EE.UU.):
> `us.anthropic.claude-haiku-4-5-20251001-v1:0`. Ya está puesto así en
> `lib/bedrock_client.py`. Si en el futuro cambias de modelo de Claude,
> confírmalo en Bedrock → "Cross-region inference" antes de asumir que el
> ID directo funciona.

> **Nota sobre guardrails y modelos de imagen:** Stable Diffusion 3.5 Large (y los
> modelos de generación de imágenes de Bedrock en general) **no aceptan**
> un guardrail dentro de `invoke_model` — AWS devuelve
> `ValidationException: Guardrail is not supported with the chosen model`.
> Por eso la app genera la imagen primero y la evalúa después con la API
> independiente `ApplyGuardrail` (`lib/bedrock_client.py:
> apply_guardrail_image`). Esto requiere el permiso IAM
> `bedrock:ApplyGuardrail` además de `bedrock:InvokeModel` (ya incluido en
> la política del paso 5).

## 5. Crear el usuario IAM de la aplicación (permisos mínimos)

Este es el usuario cuyas credenciales pegarás en los secrets de la app.
Ejecuta esto en **CloudShell** (no en tu máquina — ver paso 3):

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="genai-studio-images-${ACCOUNT_ID}"

cat > genai-studio-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "bedrock:InvokeModel",
      "Resource": [
        "arn:aws:bedrock:us-west-2:${ACCOUNT_ID}:inference-profile/us.anthropic.claude-haiku-4-5-20251001-v1:0",
        "arn:aws:bedrock:us-*::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0",
        "arn:aws:bedrock:us-west-2::foundation-model/stability.sd3-5-large-v1:0"
      ]
    },
    {
      "Effect": "Allow",
      "Action": "bedrock:ApplyGuardrail",
      "Resource": "arn:aws:bedrock:us-west-2:${ACCOUNT_ID}:guardrail/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject"],
      "Resource": "arn:aws:s3:::${BUCKET_NAME}/images/*"
    },
    {
      "Effect": "Allow",
      "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Scan"],
      "Resource": "arn:aws:dynamodb:us-west-2:${ACCOUNT_ID}:table/content_history"
    }
  ]
}
EOF

aws iam create-user --user-name genai-studio-app
aws iam put-user-policy --user-name genai-studio-app \
  --policy-name genai-studio-policy --policy-document file://genai-studio-policy.json
aws iam create-access-key --user-name genai-studio-app
```

El último comando imprime un `AccessKeyId` y `SecretAccessKey` — **guárdalos
ahora**, el `SecretAccessKey` no se puede volver a consultar después. Estos
son los valores para `aws_access_key_id`/`aws_secret_access_key` en los
secrets de Streamlit (paso 9).

> El ARN del `inference-profile` para Claude y el rango `us-*` en el ARN del
> `foundation-model` son la mejor aproximación disponible sin acceso a un
> entorno real — los inference profiles multi-región pueden reenviar la
> petición a varias regiones de EE.UU. bajo el capó. Si al ejecutar
> `check_bedrock_access.py` (paso 9) ves `AccessDeniedException` para
> Claude, es que la política necesita un ajuste aquí — el detalle real del
> error (gracias al script) te dirá exactamente qué ARN falta.

## 6. Crear el bucket S3

> `--create-bucket-configuration` es obligatorio para cualquier región
> distinta de `us-east-1` — si lo omites, AWS devuelve
> `IllegalLocationConstraintException`.

```bash
aws s3api create-bucket --bucket "$BUCKET_NAME" --region us-west-2 \
  --create-bucket-configuration LocationConstraint=us-west-2
aws s3api put-bucket-encryption --bucket "$BUCKET_NAME" \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api put-public-access-block --bucket "$BUCKET_NAME" \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
echo "Bucket creado: $BUCKET_NAME"
```

Guarda el valor de `$BUCKET_NAME` — es el `s3_bucket` de los secrets.

## 7. Crear la tabla DynamoDB

```bash
aws dynamodb create-table \
  --table-name content_history \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --sse-specification Enabled=true \
  --region us-west-2
```

Verifica que quedó activa (puede tardar unos segundos):
```bash
aws dynamodb describe-table --table-name content_history --query "Table.TableStatus"
```
Debe decir `"ACTIVE"`.

## 8. Crear un Guardrail en Bedrock

No hay un único comando CLI simple para esto — se hace en la consola:

1. Consola de AWS → Amazon Bedrock → menú lateral "Guardrails" → "Create
   guardrail".
2. Nombre: `genai-studio-guardrail`.
3. **Content filters** ("Configure content filters"): activa "Configure
   harmful categories filters" y para cada categoría (Hate, Insults,
   Sexual, Violence, Misconduct) marca **tanto "Text" como "Image"** (esta
   app modera texto vía Claude e imágenes vía Stable Diffusion 3.5 Large con el
   mismo guardrail — si dejas solo "Text", las imágenes generadas no pasarían
   por el filtro). "Misconduct" normalmente solo ofrece "Text", eso es
   normal. Acción: **Block**. Umbral: **Medium** o superior.
4. **Denied topics**: acción **Block** (no "Detect" — el código de la app
   asume que el guardrail bloquea de verdad; un modo que solo detecta sin
   bloquear dejaría pasar el contenido igual). Añade al menos estos dos
   (cubren directamente "mitigación de sesgos" y "protección de derechos
   de autor" del enunciado):
   - **Imitación de artistas o personajes con derechos de autor** — definición:
     "Solicitudes para generar imágenes o texto que imiten el estilo
     distintivo de un artista específico, o que representen personajes,
     marcas o personajes de ficción protegidos por derechos de autor."
     Frases de ejemplo: "genera esto al estilo de [artista]", "haz un
     dibujo de [personaje de una franquicia]", "imita el logo de [marca]".
   - **Contenido discriminatorio o con sesgos** — definición: "Solicitudes
     que promuevan estereotipos, discriminación o trato desigual basado en
     raza, género, religión, orientación sexual, discapacidad u otras
     características protegidas." Frases de ejemplo: "muestra a [grupo]
     como inferior", "genera un anuncio que asuma que solo [género] hace
     [tarea]".

   Opcionalmente, para una herramienta de marketing puedes añadir también
   "Afirmaciones publicitarias engañosas o no verificadas" (afirmaciones
   médicas/financieras sin respaldo) y "Contenido político o electoral" —
   no los exige el enunciado, pero son razonables para este caso de uso.
5. **PII filters**: activa el bloqueo/enmascarado de PII común (email,
   teléfono, tarjetas de crédito).
6. Guarda el guardrail.
7. Anota el **Guardrail ID** (aparece en la página del guardrail) y crea
   una **versión** publicada (Bedrock también permite usar `DRAFT` para
   pruebas, pero una versión numerada es más estable para producción):
   en la página del guardrail → "Create version".

## 9. Verificar el acceso antes de configurar la app

Esto sí se ejecuta en tu máquina local (no en CloudShell), con las
credenciales del usuario `genai-studio-app` del paso 5 exportadas como
variables de entorno, y el Guardrail ID del paso 8:

```bash
export AWS_ACCESS_KEY_ID="<AccessKeyId del paso 5>"
export AWS_SECRET_ACCESS_KEY="<SecretAccessKey del paso 5>"
export AWS_REGION="us-west-2"
export GUARDRAIL_ID="<Guardrail ID del paso 8>"
export GUARDRAIL_VERSION="1"   # o el número de versión que hayas publicado

python scripts/check_bedrock_access.py
```

Deberías ver `OK` para Claude, para la generación con Stable Diffusion 3.5 Large, y
para el `ApplyGuardrail` sobre la imagen generada, con la acción del
guardrail impresa (normalmente `NONE`, que significa "no
intervenido" — es el resultado correcto para un prompt inofensivo).

Si ves `SIN ACCESO`, vuelve al paso 4: el acceso al modelo no está concedido
todavía en esa cuenta/región.

## 10. Configurar los secretos de la app

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edita `.streamlit/secrets.toml` y rellena con los valores reales que ya
tienes de los pasos anteriores:

| Campo en secrets.toml       | De dónde sale                              |
|------------------------------|---------------------------------------------|
| `aws_region`                 | `us-west-2` (o la región que hayas elegido) |
| `s3_bucket`                   | `$BUCKET_NAME` del paso 6                   |
| `dynamodb_table`              | `content_history` (nombre fijo del paso 7)  |
| `guardrail_id`                | Guardrail ID del paso 8                     |
| `guardrail_version`           | Versión publicada del paso 8                |
| `aws_access_key_id`           | `AccessKeyId` del paso 5                    |
| `aws_secret_access_key`       | `SecretAccessKey` del paso 5                |
| `password_disenador`, `password_redactor`, `password_aprobador` | Elige tres contraseñas distintas para cada rol |
| `quota_per_hour`              | Déjalo en `20` salvo que quieras otro límite |

`.streamlit/secrets.toml` está en `.gitignore` — nunca lo subas a GitHub.

## 11. Probar en local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Abre la URL local que imprime Streamlit, inicia sesión con una de las tres
contraseñas de rol, y prueba generar una imagen y editar un texto.

## 12. Desplegar en Streamlit Community Cloud

1. Sube este repositorio a GitHub (si aún no lo has hecho) — asegúrate de
   que `.streamlit/secrets.toml` **no** esté incluido (revisa `.gitignore`).
2. Ve a **https://share.streamlit.io** → inicia sesión con tu cuenta de
   GitHub → "New app".
3. Selecciona el repositorio, la rama (`master`) y `app.py` como archivo
   principal.
4. Antes de desplegar, ve a "Advanced settings" → "Secrets" → pega el
   contenido **completo** de tu `.streamlit/secrets.toml` real (no el
   `.example`).
5. "Deploy". La primera vez tarda unos minutos en instalar dependencias.
6. Cuando termine, tendrás una URL pública — compártela con los roles
   diseñador/redactor/aprobador junto con sus contraseñas respectivas.

## 13. Limpieza opcional

Como usaste CloudShell para los comandos de administración, no queda
ningún access key de administrador que limpiar. El usuario
`genai-studio-app` debe permanecer — es el que usa la app en producción.

---

## Resumen de lo que necesitas tener a mano al terminar

- `AccessKeyId` / `SecretAccessKey` del usuario `genai-studio-app`
- Nombre del bucket S3 (`genai-studio-images-<ACCOUNT_ID>`)
- Nombre de la tabla DynamoDB (`content_history`)
- Guardrail ID y versión
- Región (`us-west-2`)
- Tres contraseñas de rol que hayas elegido

Con eso, `.streamlit/secrets.toml` queda completo y la app está lista para
correr en local o desplegarse en Streamlit Community Cloud.
