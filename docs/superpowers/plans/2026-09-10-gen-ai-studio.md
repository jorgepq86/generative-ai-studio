# Generative AI Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and deploy a working Streamlit app on Amazon Bedrock that lets designers/writers/approvers generate images (Stable Diffusion) and edit text content (Claude), with basic roles, history, comments and moderation.

**Architecture:** A single Streamlit app (frontend + backend in one Python process) calling Amazon Bedrock via `boto3`. Generated images go to S3, all history/comments/metadata go to DynamoDB. A password+role gate protects the public URL. Bedrock Guardrails handle content moderation inline on every model call.

**Tech Stack:** Python 3.11+, Streamlit >=1.37 (multi-page app, `streamlit.testing.v1.AppTest` for UI tests), boto3/botocore, pytest, moto (S3/DynamoDB mocking), Amazon Bedrock (Claude 3.5 Sonnet + Stability SDXL), Amazon S3, Amazon DynamoDB, Streamlit Community Cloud.

**Spec:** `docs/superpowers/specs/2026-09-10-gen-ai-studio-design.md`

## Global Constraints

- Amazon Bedrock is the unified platform; Claude (text) and Stable Diffusion (images) are both used, never alternatives.
- Deployment target is Streamlit Community Cloud — its disk is not reliably persistent across redeploys, so images go to S3 and metadata to DynamoDB (never local disk).
- Access to the app is gated by a shared password per role (`diseñador`, `redactor`, `aprobador`) read from `st.secrets` — there are no individual user accounts in this prototype; `st.session_state["user"]` equals the role name.
- Content moderation is delegated entirely to Bedrock Guardrails (`guardrailIdentifier`/`guardrailVersion` passed on every `invoke_model` call) — no custom moderation model.
- Encryption at rest uses AWS defaults only (S3 SSE-S3 `AES256`, DynamoDB SSE) — no application-level encryption.
- A shared quota of N generations/edits per user per hour (`quota_per_hour` secret, default 20) is enforced before every Bedrock call.
- Retries with exponential backoff apply only to `ThrottlingException`; `AccessDeniedException` and `ValidationException` never retry.
- Default AWS region is `us-east-1`.
- Out of scope (do not implement): real-time simultaneous multi-user editing, a custom moderation model beyond Guardrails, application-level encryption beyond AWS defaults, deployment to AWS-native infrastructure (Lambda/EC2/Amplify).

---

## File Structure

```
app.py                          # login gate + landing page
lib/
  __init__.py
  auth.py                       # password/role check, session helpers
  bedrock_client.py             # boto3 wrappers for Claude + Stable Diffusion, retries
  storage.py                    # S3 upload / presigned URL
  history.py                    # DynamoDB CRUD: generations, edits, comments, quota
  moderation.py                 # wraps bedrock_client calls, interprets Guardrails result
  clients.py                    # st.cache_resource factories for boto3 clients/table
pages/
  1_Generar_Imagen.py           # image generation UI
  2_Editar_Contenido.py         # content editing UI, version history, revert
  3_Galeria_Historial.py        # gallery + text history + comments (read-only, manual test)
scripts/
  check_bedrock_access.py       # manual smoke test against real Bedrock
tests/
  test_auth.py
  test_bedrock_client.py
  test_storage.py
  test_history.py
  test_moderation.py
  test_app_smoke.py
  test_page_generar_imagen_smoke.py
  test_page_editar_contenido_smoke.py
requirements.txt
conftest.py
.streamlit/secrets.toml.example
README.md
```

---

### Task 1: Project scaffolding + minimal app shell

**Files:**
- Create: `requirements.txt`
- Create: `conftest.py`
- Create: `lib/__init__.py`
- Create: `app.py`
- Create: `.streamlit/secrets.toml.example`
- Create: `README.md`
- Test: `tests/test_app_smoke.py`

**Interfaces:**
- Consumes: nothing (first task)
- Produces: a running `app.py` that later tasks will extend; `requirements.txt` used by every subsequent task's dependencies.

- [ ] **Step 1: Create `requirements.txt`**

```
streamlit>=1.37
boto3>=1.34
botocore>=1.34
pytest>=8.0
moto[s3,dynamodb]>=5.0
```

- [ ] **Step 2: Create `conftest.py` so `lib` is importable from `tests/`**

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
```

- [ ] **Step 3: Create empty `lib/__init__.py`**

```python
```

- [ ] **Step 4: Write the failing test for the app shell**

```python
# tests/test_app_smoke.py
from streamlit.testing.v1 import AppTest


def test_app_loads_and_shows_title():
    at = AppTest.from_file("app.py")
    at.run()
    assert at.title[0].value == "Generative AI Studio"
```

- [ ] **Step 5: Run test to verify it fails**

Run: `pytest tests/test_app_smoke.py -v`
Expected: FAIL (`app.py` does not exist yet, or has no title)

- [ ] **Step 6: Create minimal `app.py`**

```python
import streamlit as st

st.set_page_config(page_title="Generative AI Studio", page_icon="🎨")
st.title("Generative AI Studio")
```

- [ ] **Step 7: Run test to verify it passes**

Run: `pytest tests/test_app_smoke.py -v`
Expected: PASS

- [ ] **Step 8: Create `.streamlit/secrets.toml.example`**

```toml
# Copia este archivo a .streamlit/secrets.toml para desarrollo local,
# o pega su contenido en el panel de Secrets de Streamlit Community Cloud.

password_disenador = "cambia-esta-clave"
password_redactor = "cambia-esta-clave"
password_aprobador = "cambia-esta-clave"

aws_region = "us-east-1"
s3_bucket = "genai-studio-images-CAMBIA-ESTO"
dynamodb_table = "content_history"
guardrail_id = "TU_GUARDRAIL_ID"
guardrail_version = "1"
quota_per_hour = 20

aws_access_key_id = "TU_ACCESS_KEY"
aws_secret_access_key = "TU_SECRET_KEY"
```

- [ ] **Step 9: Create `.gitignore` entry check and `README.md` stub**

Confirm `.gitignore` already excludes `.streamlit/secrets.toml`, `__pycache__/`, `.venv/` (it does, from the design-spec commit). Create `README.md`:

```markdown
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
```

- [ ] **Step 10: Commit**

```bash
git add requirements.txt conftest.py lib/__init__.py app.py .streamlit/secrets.toml.example README.md tests/test_app_smoke.py
git commit -m "chore: project scaffolding and minimal app shell"
```

---

### Task 2: Authentication — password + role gate

**Files:**
- Create: `lib/auth.py`
- Modify: `app.py`
- Test: `tests/test_auth.py`
- Modify: `tests/test_app_smoke.py`

**Interfaces:**
- Consumes: nothing new
- Produces: `auth.check_password(password: str, secrets: Mapping) -> str | None`, `auth.is_authenticated() -> bool`, `auth.login_form() -> None`. Every later page imports `auth.is_authenticated()` to gate access and reads `st.session_state["role"]` / `st.session_state["user"]`.

- [ ] **Step 1: Write failing unit tests for `check_password`**

```python
# tests/test_auth.py
from lib import auth


def test_check_password_returns_role_for_matching_password():
    secrets = {"password_redactor": "clave123", "password_disenador": "otra"}
    assert auth.check_password("clave123", secrets) == "redactor"


def test_check_password_returns_none_for_wrong_password():
    secrets = {"password_redactor": "clave123"}
    assert auth.check_password("incorrecta", secrets) is None


def test_check_password_returns_none_when_secret_missing():
    secrets = {}
    assert auth.check_password("cualquier", secrets) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_auth.py -v`
Expected: FAIL (`lib.auth` does not exist)

- [ ] **Step 3: Implement `lib/auth.py`**

```python
import streamlit as st

ROLE_SECRET_KEYS = {
    "diseñador": "password_disenador",
    "redactor": "password_redactor",
    "aprobador": "password_aprobador",
}


def check_password(password, secrets):
    for role, secret_key in ROLE_SECRET_KEYS.items():
        expected = secrets.get(secret_key)
        if expected and password == expected:
            return role
    return None


def is_authenticated():
    return "role" in st.session_state


def login_form():
    st.title("Acceso — Generative AI Studio")
    password = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        role = check_password(password, st.secrets)
        if role:
            st.session_state["role"] = role
            st.session_state["user"] = role
            st.rerun()
        else:
            st.error("Contraseña incorrecta")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_auth.py -v`
Expected: PASS

- [ ] **Step 5: Wire the login gate into `app.py`**

```python
import streamlit as st

from lib import auth

st.set_page_config(page_title="Generative AI Studio", page_icon="🎨")

if not auth.is_authenticated():
    auth.login_form()
    st.stop()

st.title("Generative AI Studio")
st.write(f"Sesión iniciada como **{st.session_state['role']}**")
st.write("Usa el menú lateral para navegar entre Generar Imagen, Editar Contenido y Galería/Historial.")
```

- [ ] **Step 6: Rewrite `tests/test_app_smoke.py` for the authenticated/unauthenticated flow**

```python
# tests/test_app_smoke.py
from streamlit.testing.v1 import AppTest


def test_shows_login_form_when_not_authenticated():
    at = AppTest.from_file("app.py")
    at.run()
    assert at.title[0].value == "Acceso — Generative AI Studio"
    assert len(at.text_input) == 1


def test_shows_main_title_when_authenticated():
    at = AppTest.from_file("app.py")
    at.session_state["role"] = "redactor"
    at.session_state["user"] = "redactor"
    at.run()
    assert at.title[0].value == "Generative AI Studio"


def test_login_with_correct_password_sets_role():
    at = AppTest.from_file("app.py")
    at.secrets["password_redactor"] = "clave123"
    at.run()
    at.text_input[0].input("clave123").run()
    at.button[0].click().run()
    assert at.session_state["role"] == "redactor"
    assert at.session_state["user"] == "redactor"


def test_login_with_wrong_password_shows_error():
    at = AppTest.from_file("app.py")
    at.secrets["password_redactor"] = "clave123"
    at.run()
    at.text_input[0].input("incorrecta").run()
    at.button[0].click().run()
    assert len(at.error) == 1
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `pytest tests/test_app_smoke.py tests/test_auth.py -v`
Expected: PASS (4 + 3 tests)

- [ ] **Step 8: Commit**

```bash
git add lib/auth.py app.py tests/test_auth.py tests/test_app_smoke.py
git commit -m "feat: add password/role authentication gate"
```

---

### Task 3: Bedrock client — Claude + Stable Diffusion wrappers with retry

**Files:**
- Create: `lib/bedrock_client.py`
- Test: `tests/test_bedrock_client.py`

**Interfaces:**
- Consumes: nothing new
- Produces:
  - `bedrock_client.get_client(region_name: str)` → boto3 `bedrock-runtime` client
  - `bedrock_client.invoke_claude(client, text: str, action: str, model_id=..., guardrail_id=None, guardrail_version=None, sleep_fn=time.sleep) -> tuple[str, dict]` (text, `ResponseMetadata`)
  - `bedrock_client.invoke_stable_diffusion(client, prompt: str, style: str, model_id=..., guardrail_id=None, guardrail_version=None, sleep_fn=time.sleep) -> tuple[bytes, dict]` (image bytes, `ResponseMetadata`)
  - `bedrock_client.BedrockError`, `bedrock_client.ModelAccessError`
  - `moderation.py` (Task 6) consumes all of the above.

- [ ] **Step 1: Write failing tests for success, throttling retry, and access-denied cases**

```python
# tests/test_bedrock_client.py
import json

import botocore.exceptions
import pytest
from unittest.mock import MagicMock

from lib import bedrock_client


class FakeStreamingBody:
    def __init__(self, data: bytes):
        self._data = data

    def read(self):
        return self._data


def _claude_response(text):
    return {
        "body": FakeStreamingBody(json.dumps({"content": [{"type": "text", "text": text}]}).encode()),
        "ResponseMetadata": {"HTTPHeaders": {}},
    }


def _sd_response(b64_image):
    return {
        "body": FakeStreamingBody(json.dumps({"artifacts": [{"base64": b64_image}]}).encode()),
        "ResponseMetadata": {"HTTPHeaders": {}},
    }


def test_invoke_claude_returns_edited_text():
    fake_client = MagicMock()
    fake_client.invoke_model.return_value = _claude_response("Texto resumido")

    text, metadata = bedrock_client.invoke_claude(fake_client, "Texto largo original", "resumir", sleep_fn=lambda s: None)

    assert text == "Texto resumido"
    assert metadata == {"HTTPHeaders": {}}
    fake_client.invoke_model.assert_called_once()


def test_invoke_claude_retries_on_throttling_then_succeeds():
    fake_client = MagicMock()
    throttle_error = botocore.exceptions.ClientError(
        {"Error": {"Code": "ThrottlingException", "Message": "Too many requests"}}, "InvokeModel"
    )
    fake_client.invoke_model.side_effect = [throttle_error, _claude_response("ok")]
    sleeps = []

    text, _ = bedrock_client.invoke_claude(fake_client, "hola", "resumir", sleep_fn=sleeps.append)

    assert text == "ok"
    assert sleeps == [1]
    assert fake_client.invoke_model.call_count == 2


def test_invoke_claude_raises_model_access_error_without_retry():
    fake_client = MagicMock()
    fake_client.invoke_model.side_effect = botocore.exceptions.ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "no access"}}, "InvokeModel"
    )

    with pytest.raises(bedrock_client.ModelAccessError):
        bedrock_client.invoke_claude(fake_client, "hola", "resumir", sleep_fn=lambda s: None)

    assert fake_client.invoke_model.call_count == 1


def test_invoke_claude_raises_bedrock_error_on_validation_exception():
    fake_client = MagicMock()
    fake_client.invoke_model.side_effect = botocore.exceptions.ClientError(
        {"Error": {"Code": "ValidationException", "Message": "bad payload"}}, "InvokeModel"
    )

    with pytest.raises(bedrock_client.BedrockError):
        bedrock_client.invoke_claude(fake_client, "hola", "resumir", sleep_fn=lambda s: None)

    assert fake_client.invoke_model.call_count == 1


def test_invoke_stable_diffusion_returns_decoded_image_bytes():
    import base64

    fake_client = MagicMock()
    fake_client.invoke_model.return_value = _sd_response(base64.b64encode(b"fake-png-bytes").decode())

    image_bytes, _ = bedrock_client.invoke_stable_diffusion(fake_client, "a red apple", "anime", sleep_fn=lambda s: None)

    assert image_bytes == b"fake-png-bytes"


def test_invoke_passes_guardrail_params_to_invoke_model():
    fake_client = MagicMock()
    fake_client.invoke_model.return_value = _claude_response("ok")

    bedrock_client.invoke_claude(
        fake_client, "hola", "resumir",
        guardrail_id="gr-123", guardrail_version="1", sleep_fn=lambda s: None,
    )

    _, kwargs = fake_client.invoke_model.call_args
    assert kwargs["guardrailIdentifier"] == "gr-123"
    assert kwargs["guardrailVersion"] == "1"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_bedrock_client.py -v`
Expected: FAIL (`lib.bedrock_client` does not exist)

- [ ] **Step 3: Implement `lib/bedrock_client.py`**

```python
import base64
import json
import time

import botocore.exceptions


class BedrockError(Exception):
    """Error genérico al invocar un modelo de Bedrock."""


class ModelAccessError(BedrockError):
    """La cuenta/rol no tiene acceso al modelo solicitado."""


def get_client(region_name):
    import boto3
    return boto3.client("bedrock-runtime", region_name=region_name)


def _invoke_with_retry(client, model_id, body, guardrail_id=None, guardrail_version=None,
                        max_retries=3, sleep_fn=time.sleep):
    kwargs = dict(
        modelId=model_id,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    if guardrail_id:
        kwargs["guardrailIdentifier"] = guardrail_id
        kwargs["guardrailVersion"] = guardrail_version

    last_error = None
    for attempt in range(max_retries):
        try:
            return client.invoke_model(**kwargs)
        except botocore.exceptions.ClientError as error:
            code = error.response["Error"]["Code"]
            if code == "AccessDeniedException":
                raise ModelAccessError(
                    f"Sin acceso al modelo '{model_id}'. Solicita acceso en la consola de Amazon Bedrock."
                ) from error
            if code == "ValidationException":
                raise BedrockError(
                    "La petición al modelo no es válida. Ajusta el contenido e inténtalo de nuevo."
                ) from error
            if code == "ThrottlingException":
                last_error = error
                sleep_fn(2 ** attempt)
                continue
            raise BedrockError(f"Error inesperado de Bedrock: {code}") from error
    raise BedrockError("Bedrock sigue limitando la tasa de peticiones tras varios reintentos.") from last_error


def invoke_claude(client, text, action, model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
                   guardrail_id=None, guardrail_version=None, sleep_fn=time.sleep):
    action_prompts = {
        "resumir": "Resume el siguiente texto manteniendo las ideas clave:",
        "expandir": "Expande el siguiente texto añadiendo más detalle y contexto:",
        "corregir": "Corrige la gramática y el estilo del siguiente texto, sin cambiar su significado:",
        "variar": "Genera una variación del siguiente texto con un tono distinto:",
    }
    instruction = action_prompts[action]
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": f"{instruction}\n\n{text}"}],
    }
    response = _invoke_with_retry(
        client, model_id, body, guardrail_id=guardrail_id, guardrail_version=guardrail_version, sleep_fn=sleep_fn
    )
    payload = json.loads(response["body"].read())
    result_text = payload["content"][0]["text"]
    return result_text, response["ResponseMetadata"]


def invoke_stable_diffusion(client, prompt, style, model_id="stability.stable-diffusion-xl-v1",
                             guardrail_id=None, guardrail_version=None, sleep_fn=time.sleep):
    body = {
        "text_prompts": [{"text": prompt}],
        "style_preset": style,
        "cfg_scale": 10,
        "steps": 30,
    }
    response = _invoke_with_retry(
        client, model_id, body, guardrail_id=guardrail_id, guardrail_version=guardrail_version, sleep_fn=sleep_fn
    )
    payload = json.loads(response["body"].read())
    image_bytes = base64.b64decode(payload["artifacts"][0]["base64"])
    return image_bytes, response["ResponseMetadata"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_bedrock_client.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add lib/bedrock_client.py tests/test_bedrock_client.py
git commit -m "feat: add Bedrock client wrappers for Claude and Stable Diffusion"
```

---

### Task 4: S3 image storage

**Files:**
- Create: `lib/storage.py`
- Test: `tests/test_storage.py`

**Interfaces:**
- Consumes: nothing new
- Produces:
  - `storage.get_client(region_name: str)` → boto3 `s3` client
  - `storage.save_image(client, bucket: str, user: str, image_bytes: bytes) -> str` (returns `s3_key`)
  - `storage.get_image_url(client, bucket: str, s3_key: str, expires_in: int = 3600) -> str`
  - Consumed by `pages/1_Generar_Imagen.py` (Task 7) and `pages/3_Galeria_Historial.py` (Task 9).

- [ ] **Step 1: Write failing tests using moto**

```python
# tests/test_storage.py
import boto3
from moto import mock_aws

from lib import storage


@mock_aws
def test_save_image_uploads_to_s3_and_returns_key():
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket="test-bucket")

    key = storage.save_image(client, "test-bucket", "redactor", b"fake-png-bytes")

    assert key.startswith("images/redactor/")
    assert key.endswith(".png")
    obj = client.get_object(Bucket="test-bucket", Key=key)
    assert obj["Body"].read() == b"fake-png-bytes"


@mock_aws
def test_save_image_sets_server_side_encryption():
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket="test-bucket")

    key = storage.save_image(client, "test-bucket", "redactor", b"data")

    head = client.head_object(Bucket="test-bucket", Key=key)
    assert head["ServerSideEncryption"] == "AES256"


@mock_aws
def test_get_image_url_returns_url_containing_bucket_and_key():
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket="test-bucket")
    key = storage.save_image(client, "test-bucket", "redactor", b"data")

    url = storage.get_image_url(client, "test-bucket", key)

    assert "test-bucket" in url
    assert key in url
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL (`lib.storage` does not exist)

- [ ] **Step 3: Implement `lib/storage.py`**

```python
import uuid


def get_client(region_name):
    import boto3
    return boto3.client("s3", region_name=region_name)


def save_image(client, bucket, user, image_bytes):
    key = f"images/{user}/{uuid.uuid4()}.png"
    client.put_object(
        Bucket=bucket, Key=key, Body=image_bytes, ContentType="image/png", ServerSideEncryption="AES256"
    )
    return key


def get_image_url(client, bucket, s3_key, expires_in=3600):
    return client.generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": s3_key}, ExpiresIn=expires_in
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_storage.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add lib/storage.py tests/test_storage.py
git commit -m "feat: add S3 image storage helpers"
```

---

### Task 5: DynamoDB history — generations, edits, comments, quota

**Files:**
- Create: `lib/history.py`
- Test: `tests/test_history.py`

**Interfaces:**
- Consumes: nothing new
- Produces:
  - `history.get_table(region_name: str, table_name: str)` → boto3 DynamoDB `Table`
  - `history.log_generation(table, user, role, prompt, style, s3_key, moderation_status) -> str` (item id)
  - `history.log_edit(table, user, role, action, original_text, result_text, previous_version_id, moderation_status) -> str` (item id)
  - `history.add_comment(table, item_id, user, comment) -> None`
  - `history.get_item(table, item_id) -> dict | None`
  - `history.list_items(table, tipo=None) -> list[dict]` (newest first)
  - `history.get_version_chain(table, item_id) -> list[dict]` (oldest first)
  - `history.count_recent_generations(table, user, since_iso_timestamp) -> int`
  - `history.hour_ago_iso() -> str`
  - Consumed by `pages/1_Generar_Imagen.py`, `pages/2_Editar_Contenido.py`, `pages/3_Galeria_Historial.py` (Tasks 7-9).

- [ ] **Step 1: Write failing tests using moto**

```python
# tests/test_history.py
import boto3
import pytest
from moto import mock_aws

from lib import history


@pytest.fixture
def table():
    with mock_aws():
        resource = boto3.resource("dynamodb", region_name="us-east-1")
        resource.create_table(
            TableName="content_history",
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield resource.Table("content_history")


def test_log_generation_creates_item(table):
    item_id = history.log_generation(table, "ana", "diseñador", "un gato", "anime", "images/ana/x.png", "NONE")

    item = history.get_item(table, item_id)
    assert item["tipo"] == "imagen"
    assert item["usuario"] == "ana"
    assert item["resultado"] == "images/ana/x.png"
    assert item["comentarios"] == []


def test_log_edit_and_version_chain(table):
    first_id = history.log_edit(table, "luis", "redactor", "resumir", "texto original", "texto corto", None, "NONE")
    second_id = history.log_edit(table, "luis", "redactor", "expandir", "texto corto", "texto largo", first_id, "NONE")

    chain = history.get_version_chain(table, second_id)

    assert [item["id"] for item in chain] == [first_id, second_id]


def test_add_comment_appends_to_list(table):
    item_id = history.log_generation(table, "ana", "diseñador", "un gato", "anime", "images/ana/x.png", "NONE")

    history.add_comment(table, item_id, "luis", "Me gusta el resultado")

    item = history.get_item(table, item_id)
    assert item["comentarios"][0]["comentario"] == "Me gusta el resultado"
    assert item["comentarios"][0]["usuario"] == "luis"


def test_list_items_filters_by_tipo_and_sorts_newest_first(table):
    history.log_generation(table, "ana", "diseñador", "prompt1", "anime", "k1.png", "NONE")
    history.log_edit(table, "luis", "redactor", "resumir", "texto1", "texto2", None, "NONE")

    only_images = history.list_items(table, tipo="imagen")
    all_items = history.list_items(table)

    assert len(only_images) == 1
    assert only_images[0]["tipo"] == "imagen"
    assert len(all_items) == 2


def test_count_recent_generations_filters_by_user_and_time(table):
    history.log_generation(table, "ana", "diseñador", "prompt1", "anime", "k1.png", "NONE")
    history.log_generation(table, "otro", "diseñador", "prompt2", "anime", "k2.png", "NONE")

    count = history.count_recent_generations(table, "ana", "2000-01-01T00:00:00+00:00")

    assert count == 1


def test_hour_ago_iso_returns_iso_timestamp_string():
    result = history.hour_ago_iso()
    assert "T" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_history.py -v`
Expected: FAIL (`lib.history` does not exist)

- [ ] **Step 3: Implement `lib/history.py`**

```python
import uuid
from datetime import datetime, timedelta, timezone

from boto3.dynamodb.conditions import Attr


def get_table(region_name, table_name):
    import boto3
    resource = boto3.resource("dynamodb", region_name=region_name)
    return resource.Table(table_name)


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def hour_ago_iso():
    return (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()


def log_generation(table, user, role, prompt, style, s3_key, moderation_status):
    item_id = str(uuid.uuid4())
    table.put_item(Item={
        "id": item_id,
        "tipo": "imagen",
        "usuario": user,
        "rol": role,
        "prompt_o_texto_original": prompt,
        "estilo": style,
        "resultado": s3_key,
        "comentarios": [],
        "timestamp": _now_iso(),
        "estado_moderacion": moderation_status,
    })
    return item_id


def log_edit(table, user, role, action, original_text, result_text, previous_version_id, moderation_status):
    item_id = str(uuid.uuid4())
    item = {
        "id": item_id,
        "tipo": "texto",
        "usuario": user,
        "rol": role,
        "accion": action,
        "prompt_o_texto_original": original_text,
        "resultado": result_text,
        "comentarios": [],
        "timestamp": _now_iso(),
        "estado_moderacion": moderation_status,
    }
    if previous_version_id:
        item["version_anterior_id"] = previous_version_id
    table.put_item(Item=item)
    return item_id


def add_comment(table, item_id, user, comment):
    item = get_item(table, item_id)
    comentarios = item.get("comentarios", [])
    comentarios.append({"usuario": user, "comentario": comment, "timestamp": _now_iso()})
    table.update_item(
        Key={"id": item_id},
        UpdateExpression="SET comentarios = :c",
        ExpressionAttributeValues={":c": comentarios},
    )


def get_item(table, item_id):
    response = table.get_item(Key={"id": item_id})
    return response.get("Item")


def list_items(table, tipo=None):
    if tipo:
        response = table.scan(FilterExpression=Attr("tipo").eq(tipo))
    else:
        response = table.scan()
    items = response.get("Items", [])
    return sorted(items, key=lambda i: i["timestamp"], reverse=True)


def get_version_chain(table, item_id):
    chain = []
    current = get_item(table, item_id)
    while current:
        chain.append(current)
        previous_id = current.get("version_anterior_id")
        current = get_item(table, previous_id) if previous_id else None
    return list(reversed(chain))


def count_recent_generations(table, user, since_iso_timestamp):
    response = table.scan(
        FilterExpression=Attr("usuario").eq(user) & Attr("timestamp").gte(since_iso_timestamp)
    )
    return len(response.get("Items", []))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_history.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add lib/history.py tests/test_history.py
git commit -m "feat: add DynamoDB history, comments and quota tracking"
```

---

### Task 6: Moderation — Guardrails-aware wrappers

**Files:**
- Create: `lib/moderation.py`
- Test: `tests/test_moderation.py`

**Interfaces:**
- Consumes: `bedrock_client.invoke_stable_diffusion`, `bedrock_client.invoke_claude` (Task 3)
- Produces:
  - `moderation.ModerationBlocked(Exception)`
  - `moderation.generate_image_moderated(client, prompt, style, guardrail_id, guardrail_version, sleep_fn=time.sleep) -> tuple[bytes, str]` (image bytes, moderation status)
  - `moderation.edit_text_moderated(client, text, action, guardrail_id, guardrail_version, sleep_fn=time.sleep) -> tuple[str, str]` (result text, moderation status)
  - Consumed by `pages/1_Generar_Imagen.py` and `pages/2_Editar_Contenido.py` (Tasks 7-8).

- [ ] **Step 1: Write failing tests, mocking `bedrock_client` functions**

```python
# tests/test_moderation.py
import pytest

from lib import moderation


def test_generate_image_moderated_returns_bytes_when_not_intervened(monkeypatch):
    def fake_invoke(client, prompt, style, guardrail_id=None, guardrail_version=None, sleep_fn=None):
        return b"image-bytes", {"HTTPHeaders": {"x-amzn-bedrock-guardrailaction": "NONE"}}

    monkeypatch.setattr(moderation.bedrock_client, "invoke_stable_diffusion", fake_invoke)

    image_bytes, status = moderation.generate_image_moderated(
        client=object(), prompt="un gato", style="anime", guardrail_id="gr-1", guardrail_version="1"
    )

    assert image_bytes == b"image-bytes"
    assert status == "NONE"


def test_generate_image_moderated_raises_when_intervened(monkeypatch):
    def fake_invoke(client, prompt, style, guardrail_id=None, guardrail_version=None, sleep_fn=None):
        return b"", {"HTTPHeaders": {"x-amzn-bedrock-guardrailaction": "INTERVENED"}}

    monkeypatch.setattr(moderation.bedrock_client, "invoke_stable_diffusion", fake_invoke)

    with pytest.raises(moderation.ModerationBlocked):
        moderation.generate_image_moderated(
            client=object(), prompt="contenido prohibido", style="anime", guardrail_id="gr-1", guardrail_version="1"
        )


def test_edit_text_moderated_returns_text_when_not_intervened(monkeypatch):
    def fake_invoke(client, text, action, guardrail_id=None, guardrail_version=None, sleep_fn=None):
        return "texto editado", {"HTTPHeaders": {"x-amzn-bedrock-guardrailaction": "NONE"}}

    monkeypatch.setattr(moderation.bedrock_client, "invoke_claude", fake_invoke)

    result_text, status = moderation.edit_text_moderated(
        client=object(), text="texto", action="resumir", guardrail_id="gr-1", guardrail_version="1"
    )

    assert result_text == "texto editado"
    assert status == "NONE"


def test_edit_text_moderated_raises_when_intervened(monkeypatch):
    def fake_invoke(client, text, action, guardrail_id=None, guardrail_version=None, sleep_fn=None):
        return "", {"HTTPHeaders": {"x-amzn-bedrock-guardrailaction": "INTERVENED"}}

    monkeypatch.setattr(moderation.bedrock_client, "invoke_claude", fake_invoke)

    with pytest.raises(moderation.ModerationBlocked):
        moderation.edit_text_moderated(
            client=object(), text="texto prohibido", action="resumir", guardrail_id="gr-1", guardrail_version="1"
        )


def test_guardrail_status_defaults_to_none_when_header_missing():
    status = moderation._guardrail_status({"HTTPHeaders": {}})
    assert status == "NONE"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_moderation.py -v`
Expected: FAIL (`lib.moderation` does not exist)

- [ ] **Step 3: Implement `lib/moderation.py`**

```python
import time

from lib import bedrock_client


class ModerationBlocked(Exception):
    def __init__(self, message="El contenido fue bloqueado por las políticas de uso."):
        super().__init__(message)


def _guardrail_status(response_metadata):
    headers = response_metadata.get("HTTPHeaders", {})
    return headers.get("x-amzn-bedrock-guardrailaction", "NONE")


def generate_image_moderated(client, prompt, style, guardrail_id, guardrail_version, sleep_fn=time.sleep):
    image_bytes, metadata = bedrock_client.invoke_stable_diffusion(
        client, prompt, style, guardrail_id=guardrail_id, guardrail_version=guardrail_version, sleep_fn=sleep_fn
    )
    status = _guardrail_status(metadata)
    if status == "INTERVENED":
        raise ModerationBlocked()
    return image_bytes, status


def edit_text_moderated(client, text, action, guardrail_id, guardrail_version, sleep_fn=time.sleep):
    result_text, metadata = bedrock_client.invoke_claude(
        client, text, action, guardrail_id=guardrail_id, guardrail_version=guardrail_version, sleep_fn=sleep_fn
    )
    status = _guardrail_status(metadata)
    if status == "INTERVENED":
        raise ModerationBlocked()
    return result_text, status
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_moderation.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add lib/moderation.py tests/test_moderation.py
git commit -m "feat: add Guardrails-aware moderation wrappers"
```

---

### Task 7: Image generation page

**Files:**
- Create: `lib/clients.py`
- Create: `pages/1_Generar_Imagen.py`
- Test: `tests/test_page_generar_imagen_smoke.py`

**Interfaces:**
- Consumes: `auth.is_authenticated` (Task 2), `bedrock_client.get_client` (Task 3), `storage.get_client`/`save_image` (Task 4), `history.get_table`/`hour_ago_iso`/`count_recent_generations`/`log_generation` (Task 5), `moderation.generate_image_moderated`/`ModerationBlocked` (Task 6)
- Produces: `clients.get_bedrock_client()`, `clients.get_s3_client()`, `clients.get_history_table()` (cached factories reused by Tasks 8-9)

- [ ] **Step 1: Create `lib/clients.py` (cached AWS resource factories)**

```python
import streamlit as st

from lib import bedrock_client, storage, history


@st.cache_resource
def get_bedrock_client():
    return bedrock_client.get_client(st.secrets["aws_region"])


@st.cache_resource
def get_s3_client():
    return storage.get_client(st.secrets["aws_region"])


@st.cache_resource
def get_history_table():
    return history.get_table(st.secrets["aws_region"], st.secrets["dynamodb_table"])
```

There is no dedicated pytest file for `clients.py`: it is a thin Streamlit-caching wrapper around already-tested functions, and exercising `st.cache_resource` meaningfully requires a live Streamlit run — it is covered indirectly by the page smoke tests below.

- [ ] **Step 2: Write the failing smoke tests for the page**

```python
# tests/test_page_generar_imagen_smoke.py
from streamlit.testing.v1 import AppTest


def test_page_shows_warning_when_not_authenticated():
    at = AppTest.from_file("pages/1_Generar_Imagen.py")
    at.run()
    assert len(at.warning) == 1


def test_page_renders_form_when_authenticated():
    at = AppTest.from_file("pages/1_Generar_Imagen.py")
    at.session_state["role"] = "diseñador"
    at.session_state["user"] = "diseñador"
    at.run()
    assert at.title[0].value == "Generar Imagen"
    assert len(at.text_area) == 1
    assert len(at.selectbox) == 1
    assert len(at.button) == 1
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_page_generar_imagen_smoke.py -v`
Expected: FAIL (`pages/1_Generar_Imagen.py` does not exist)

- [ ] **Step 4: Implement `pages/1_Generar_Imagen.py`**

```python
import streamlit as st

from lib import auth, clients, history, moderation, storage

st.set_page_config(page_title="Generar Imagen", page_icon="🖼️")

if not auth.is_authenticated():
    st.warning("Debes iniciar sesión desde la página principal.")
    st.stop()

st.title("Generar Imagen")

STYLE_PRESETS = {
    "Anime": "anime",
    "Pintura al óleo": "cinematic",
    "Realismo fotográfico": "photographic",
    "Boceto a lápiz": "line-art",
    "Cyberpunk": "neon-punk",
}

prompt = st.text_area("Describe la imagen que quieres generar")
style_label = st.selectbox("Estilo", list(STYLE_PRESETS.keys()))

if st.button("Generar"):
    if not prompt.strip():
        st.error("Escribe una descripción antes de generar.")
        st.stop()

    table = clients.get_history_table()
    quota_limit = st.secrets.get("quota_per_hour", 20)
    used = history.count_recent_generations(table, st.session_state["user"], history.hour_ago_iso())
    if used >= quota_limit:
        st.error(f"Has alcanzado el límite de {quota_limit} generaciones por hora. Inténtalo más tarde.")
        st.stop()

    bedrock = clients.get_bedrock_client()
    try:
        with st.spinner("Generando imagen..."):
            image_bytes, moderation_status = moderation.generate_image_moderated(
                bedrock, prompt, STYLE_PRESETS[style_label],
                guardrail_id=st.secrets["guardrail_id"],
                guardrail_version=st.secrets["guardrail_version"],
            )
    except moderation.ModerationBlocked:
        st.error("La imagen no se pudo generar: el contenido incumple las políticas de uso.")
        st.stop()
    except Exception as error:
        st.error(f"No se pudo generar la imagen: {error}")
        st.stop()

    s3_client = clients.get_s3_client()
    try:
        s3_key = storage.save_image(s3_client, st.secrets["s3_bucket"], st.session_state["user"], image_bytes)
        history.log_generation(
            table, st.session_state["user"], st.session_state["role"], prompt, style_label, s3_key, moderation_status
        )
    except Exception:
        st.warning("La imagen se generó pero no se pudo guardar en el historial.")

    st.image(image_bytes, caption=prompt)
    st.download_button("Descargar imagen", data=image_bytes, file_name="imagen_generada.png", mime="image/png")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_page_generar_imagen_smoke.py -v`
Expected: PASS (2 tests — no AWS calls happen because the "Generar" button is never clicked in these tests)

- [ ] **Step 6: Commit**

```bash
git add lib/clients.py pages/1_Generar_Imagen.py tests/test_page_generar_imagen_smoke.py
git commit -m "feat: add image generation page"
```

---

### Task 8: Content editing page with version history and revert

**Files:**
- Create: `pages/2_Editar_Contenido.py`
- Test: `tests/test_page_editar_contenido_smoke.py`

**Interfaces:**
- Consumes: `auth.is_authenticated` (Task 2), `clients.get_bedrock_client`/`get_history_table` (Task 7), `history.hour_ago_iso`/`count_recent_generations`/`log_edit`/`get_version_chain` (Task 5), `moderation.edit_text_moderated`/`ModerationBlocked` (Task 6)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Write the failing smoke tests for the page**

```python
# tests/test_page_editar_contenido_smoke.py
from streamlit.testing.v1 import AppTest


def test_page_shows_warning_when_not_authenticated():
    at = AppTest.from_file("pages/2_Editar_Contenido.py")
    at.run()
    assert len(at.warning) == 1


def test_page_renders_form_when_authenticated():
    at = AppTest.from_file("pages/2_Editar_Contenido.py")
    at.session_state["role"] = "redactor"
    at.session_state["user"] = "redactor"
    at.run()
    assert at.title[0].value == "Editar Contenido"
    assert len(at.text_area) == 1
    assert len(at.selectbox) == 1
    assert len(at.button) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_page_editar_contenido_smoke.py -v`
Expected: FAIL (`pages/2_Editar_Contenido.py` does not exist)

- [ ] **Step 3: Implement `pages/2_Editar_Contenido.py`**

```python
import streamlit as st

from lib import auth, clients, history, moderation

st.set_page_config(page_title="Editar Contenido", page_icon="✍️")

if not auth.is_authenticated():
    st.warning("Debes iniciar sesión desde la página principal.")
    st.stop()

st.title("Editar Contenido")

ACTIONS = {
    "resumir": "Resumir",
    "expandir": "Expandir",
    "corregir": "Corregir gramática y estilo",
    "variar": "Generar variación",
}

DRAFT_KEY = "draft_text"
if DRAFT_KEY not in st.session_state:
    st.session_state[DRAFT_KEY] = ""

st.text_area("Pega o escribe el texto a editar", height=200, key=DRAFT_KEY)
action_key = st.selectbox("Acción", list(ACTIONS.keys()), format_func=lambda k: ACTIONS[k])

if st.button("Aplicar"):
    current_text = st.session_state[DRAFT_KEY]
    if not current_text.strip():
        st.error("Escribe un texto antes de aplicar una acción.")
        st.stop()

    table = clients.get_history_table()
    quota_limit = st.secrets.get("quota_per_hour", 20)
    used = history.count_recent_generations(table, st.session_state["user"], history.hour_ago_iso())
    if used >= quota_limit:
        st.error(f"Has alcanzado el límite de {quota_limit} ediciones por hora. Inténtalo más tarde.")
        st.stop()

    bedrock = clients.get_bedrock_client()
    try:
        with st.spinner("Aplicando edición..."):
            result_text, moderation_status = moderation.edit_text_moderated(
                bedrock, current_text, action_key,
                guardrail_id=st.secrets["guardrail_id"],
                guardrail_version=st.secrets["guardrail_version"],
            )
    except moderation.ModerationBlocked:
        st.error("El texto no se pudo procesar: el contenido incumple las políticas de uso.")
        st.stop()
    except Exception as error:
        st.error(f"No se pudo aplicar la edición: {error}")
        st.stop()

    try:
        new_id = history.log_edit(
            table, st.session_state["user"], st.session_state["role"], action_key,
            current_text, result_text, st.session_state.get("last_edit_id"), moderation_status,
        )
        st.session_state["last_edit_id"] = new_id
    except Exception:
        st.warning("La edición se aplicó pero no se pudo guardar en el historial.")

    st.session_state[DRAFT_KEY] = result_text
    st.rerun()

if st.session_state.get("last_edit_id"):
    table = clients.get_history_table()
    chain = history.get_version_chain(table, st.session_state["last_edit_id"])
    with st.expander("Historial de versiones"):
        for version in chain:
            st.write(f"**{ACTIONS.get(version['accion'], version['accion'])}** — {version['timestamp']}")
            st.caption(version["resultado"][:200])
            if st.button("Revertir a esta versión", key=f"revert_{version['id']}"):
                st.session_state[DRAFT_KEY] = version["resultado"]
                st.session_state["last_edit_id"] = version.get("version_anterior_id")
                st.rerun()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_page_editar_contenido_smoke.py -v`
Expected: PASS (2 tests — no AWS calls happen because "Aplicar" is never clicked and `last_edit_id` is unset in these tests)

- [ ] **Step 5: Commit**

```bash
git add pages/2_Editar_Contenido.py tests/test_page_editar_contenido_smoke.py
git commit -m "feat: add content editing page with version history and revert"
```

---

### Task 9: Gallery, text history and comments page

**Files:**
- Create: `pages/3_Galeria_Historial.py`

**Interfaces:**
- Consumes: `auth.is_authenticated` (Task 2), `clients.get_history_table`/`get_s3_client` (Task 7), `history.list_items`/`add_comment` (Task 5), `storage.get_image_url` (Task 4)
- Produces: nothing consumed by later tasks

This page reads live data from DynamoDB/S3 as soon as it loads (there is no button gating the read, unlike Tasks 7-8), so it cannot be smoke-tested with `AppTest` without a real or mocked AWS backend wired into the running app process — per the spec, this page's UI is verified manually rather than with automated tests.

- [ ] **Step 1: Implement `pages/3_Galeria_Historial.py`**

```python
import streamlit as st

from lib import auth, clients, history, storage

st.set_page_config(page_title="Galería e Historial", page_icon="🗂️")

if not auth.is_authenticated():
    st.warning("Debes iniciar sesión desde la página principal.")
    st.stop()

st.title("Galería e Historial")

table = clients.get_history_table()
items = history.list_items(table)

tab_gallery, tab_history = st.tabs(["Galería de imágenes", "Historial de textos"])


def _comment_section(item):
    with st.expander("Comentarios"):
        for comentario in item.get("comentarios", []):
            st.write(f"**{comentario['usuario']}**: {comentario['comentario']}")
        new_comment = st.text_input("Añadir comentario", key=f"comment_{item['id']}")
        if st.button("Comentar", key=f"btn_comment_{item['id']}"):
            if new_comment.strip():
                history.add_comment(table, item["id"], st.session_state["user"], new_comment)
                st.rerun()


with tab_gallery:
    image_items = [item for item in items if item["tipo"] == "imagen"]
    if not image_items:
        st.info("Todavía no se han generado imágenes.")
    for item in image_items:
        s3_client = clients.get_s3_client()
        url = storage.get_image_url(s3_client, st.secrets["s3_bucket"], item["resultado"])
        st.image(url, caption=f"{item['prompt_o_texto_original']} ({item['estilo']}) — {item['usuario']}")
        _comment_section(item)

with tab_history:
    text_items = [item for item in items if item["tipo"] == "texto"]
    if not text_items:
        st.info("Todavía no se han editado textos.")
    for item in text_items:
        st.write(f"**{item['accion']}** por {item['usuario']} — {item['timestamp']}")
        st.caption(item["resultado"][:300])
        _comment_section(item)
```

- [ ] **Step 2: Manual verification checklist**

With the app running locally (`streamlit run app.py`) against either real AWS resources or a temporary local DynamoDB/S3 setup:
1. Log in, generate at least one image (page 1) and one text edit (page 2).
2. Open "Galería e Historial" — confirm the generated image appears in the gallery tab with its prompt/style/user caption.
3. Confirm the edited text appears in the history tab with its action/user/timestamp.
4. Add a comment on the image and on the text item — confirm it appears immediately after the page reruns.
5. Log in as a different role in a second browser session and confirm the same items/comments are visible (shared history, not per-role).

- [ ] **Step 3: Commit**

```bash
git add pages/3_Galeria_Historial.py
git commit -m "feat: add gallery, history and comments page"
```

---

### Task 10: Manual Bedrock access smoke-test script

**Files:**
- Create: `scripts/check_bedrock_access.py`

**Interfaces:**
- Consumes: `bedrock_client.get_client`/`invoke_claude`/`invoke_stable_diffusion`/`ModelAccessError`/`BedrockError` (Task 3)
- Produces: nothing consumed by other tasks — this is a standalone operator tool

- [ ] **Step 1: Implement `scripts/check_bedrock_access.py`**

```python
"""Smoke test manual: confirma que Claude y Stable Diffusion están accesibles en Bedrock.

Uso: python scripts/check_bedrock_access.py
Requiere credenciales AWS configuradas (variables de entorno o ~/.aws/credentials)
y opcionalmente la variable AWS_REGION (por defecto: us-east-1).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib import bedrock_client


def main():
    region = os.environ.get("AWS_REGION", "us-east-1")
    client = bedrock_client.get_client(region)

    print(f"Región: {region}")

    print("\nProbando Claude...")
    try:
        text, _ = bedrock_client.invoke_claude(client, "Hola, responde con una sola palabra.", "resumir")
        print(f"OK — respuesta: {text[:100]}")
    except bedrock_client.ModelAccessError as error:
        print(f"SIN ACCESO a Claude: {error}")
    except bedrock_client.BedrockError as error:
        print(f"ERROR con Claude: {error}")

    print("\nProbando Stable Diffusion...")
    try:
        image_bytes, _ = bedrock_client.invoke_stable_diffusion(client, "a red apple on a white table", "photographic")
        print(f"OK — imagen recibida ({len(image_bytes)} bytes)")
    except bedrock_client.ModelAccessError as error:
        print(f"SIN ACCESO a Stable Diffusion: {error}")
    except bedrock_client.BedrockError as error:
        print(f"ERROR con Stable Diffusion: {error}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it manually to verify model access**

Run: `AWS_REGION=us-east-1 python scripts/check_bedrock_access.py`
Expected: either `OK` for both models, or a clear `SIN ACCESO` message naming exactly which model still needs access requested in the Bedrock console — this resolves the open question about whether Bedrock model access is already enabled on the account.

- [ ] **Step 3: Commit**

```bash
git add scripts/check_bedrock_access.py
git commit -m "chore: add manual Bedrock access smoke-test script"
```

---

### Task 11: AWS infrastructure runbook and deployment docs

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: nothing (documentation only)
- Produces: nothing (terminal task)

- [ ] **Step 1: Append the deployment runbook to `README.md`**

```markdown

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
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add AWS infrastructure and Streamlit Cloud deployment runbook"
```
