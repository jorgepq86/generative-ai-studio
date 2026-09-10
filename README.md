# Generative AI Studio

Aplicación web sobre Amazon Bedrock (Claude + Stable Diffusion) para generación de
imágenes y edición de contenido, con roles básicos, historial y moderación.

Ver el diseño completo en `docs/superpowers/specs/2026-09-10-gen-ai-studio-design.md`.

## Desarrollo local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml  # y rellena los valores reales
streamlit run app.py
```

## Tests

```bash
pytest
```

## Despliegue

### 1. Prerrequisitos AWS

Región usada por defecto: `us-east-1` (Claude 3.5 Sonnet y Stability SDXL están
disponibles ahí; puedes usar otra región cambiando `aws_region` en los secrets,
siempre que los modelos también estén disponibles en esa región).

**Solicitar acceso a los modelos en Bedrock** (una vez, vía consola):
1. Consola de AWS → Amazon Bedrock → Model access.
2. Solicita acceso a "Anthropic Claude 3.5 Sonnet" y "Stability AI Stable Diffusion XL".
3. Espera a que el estado pase a "Access granted" (normalmente inmediato).
4. Verifica el acceso ejecutando `python scripts/check_bedrock_access.py`.

**Crear el bucket S3:**

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="genai-studio-images-${ACCOUNT_ID}"
aws s3api create-bucket --bucket "$BUCKET_NAME" --region us-east-1
aws s3api put-bucket-encryption --bucket "$BUCKET_NAME" \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api put-public-access-block --bucket "$BUCKET_NAME" \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
echo "Bucket creado: $BUCKET_NAME"
```

Usa `$BUCKET_NAME` como valor de `s3_bucket` en los secrets.

**Crear un usuario IAM con permisos mínimos** (en vez de usar una clave de administrador):

```bash
cat > genai-studio-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "bedrock:InvokeModel",
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0",
        "arn:aws:bedrock:us-east-1::foundation-model/stability.stable-diffusion-xl-v1"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject"],
      "Resource": "arn:aws:s3:::$BUCKET_NAME/images/*"
    },
    {
      "Effect": "Allow",
      "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Scan"],
      "Resource": "arn:aws:dynamodb:us-east-1:*:table/content_history"
    }
  ]
}
EOF
aws iam create-user --user-name genai-studio-app
aws iam put-user-policy --user-name genai-studio-app --policy-name genai-studio-policy --policy-document file://genai-studio-policy.json
aws iam create-access-key --user-name genai-studio-app
```

Usa el `AccessKeyId`/`SecretAccessKey` resultantes como `aws_access_key_id`/`aws_secret_access_key`
en los secrets, en vez de una clave de administrador. Esto es necesario para el despliegue en
Streamlit Community Cloud, que no tiene acceso al chain de credenciales por defecto de AWS
(`~/.aws/credentials`, rol de instancia, etc.) disponible en desarrollo local.

**Crear la tabla DynamoDB:**

```bash
aws dynamodb create-table \
  --table-name content_history \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --sse-specification Enabled=true \
  --region us-east-1
```

**Crear un Guardrail en Bedrock** (vía consola — no tiene un único comando CLI simple):
1. Amazon Bedrock → Guardrails → Create guardrail.
2. Nombre: `genai-studio-guardrail`.
3. Content filters: activa todas las categorías (odio, violencia, contenido sexual,
   insultos) en nivel medio o alto.
4. Denied topics: añade "Imitación de estilo de artistas o personajes con derechos de
   autor específicos".
5. PII filters: activa el bloqueo/enmascarado de PII común (email, teléfono, tarjetas).
6. Guarda y anota el Guardrail ID y la versión (usa `DRAFT` para desarrollo, o publica
   una versión numerada para producción).

### 2. Configurar secretos

Copia `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml` (desarrollo local)
y rellena los valores reales: el `s3_bucket` creado arriba, el `guardrail_id`/
`guardrail_version` del guardrail, y contraseñas reales para cada rol.

### 3. Desplegar en Streamlit Community Cloud

1. Sube este repositorio a GitHub.
2. Ve a https://share.streamlit.io → "New app" → selecciona el repo, la rama y
   `app.py` como archivo principal.
3. En "Advanced settings" → "Secrets", pega el contenido completo de tu
   `secrets.toml` real (no el `.example`).
4. Despliega. La URL pública queda disponible en unos minutos.
