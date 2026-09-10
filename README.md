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
