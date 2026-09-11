# Generative AI Studio

Aplicación web sobre Amazon Bedrock (Claude + Amazon Nova Canvas) para generación de
imágenes y edición de contenido, con roles básicos, historial y moderación.

> El enunciado original pide Stable Diffusion; se sustituyó por Nova Canvas porque
> Stable Diffusion ya no está disponible como modelo serverless en Bedrock — solo vía
> un endpoint de SageMaker con coste fijo por hora (~$137+/hora). Ver el detalle en
> [`docs/AWS_SETUP.md`](docs/AWS_SETUP.md#4-activar-los-modelos-de-bedrock).

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

Guía completa paso a paso (crear la cuenta de AWS, activar los modelos,
crear el bucket/tabla/guardrail, y desplegar en Streamlit Community Cloud):
ver **[`docs/AWS_SETUP.md`](docs/AWS_SETUP.md)**.

Resumen rápido si ya tienes la cuenta de AWS configurada:

1. Copia `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml` y
   rellena los valores reales (región, bucket S3, tabla DynamoDB,
   guardrail, credenciales del usuario IAM de la app, contraseñas de rol).
2. Verifica el acceso a los modelos: `python scripts/check_bedrock_access.py`
   (requiere `GUARDRAIL_ID` como variable de entorno — ver el script).
3. Sube el repositorio a GitHub → https://share.streamlit.io → "New app" →
   selecciona el repo, la rama y `app.py` como archivo principal.
4. En "Advanced settings" → "Secrets", pega el contenido completo de tu
   `secrets.toml` real (no el `.example`) → despliega.
