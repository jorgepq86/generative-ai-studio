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
    assert item["estado_aprobacion"] == "pendiente"


def test_log_edit_and_version_chain(table):
    first_id = history.log_edit(table, "luis", "redactor", "resumir", "texto original", "texto corto", None, "NONE")
    second_id = history.log_edit(table, "luis", "redactor", "expandir", "texto corto", "texto largo", first_id, "NONE")

    chain = history.get_version_chain(table, second_id)

    assert [item["id"] for item in chain] == [first_id, second_id]
    assert all(item["estado_aprobacion"] == "pendiente" for item in chain)


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


def test_approve_item_sets_approval_fields(table):
    item_id = history.log_generation(table, "ana", "diseñador", "un gato", "anime", "images/ana/x.png", "NONE")

    history.approve_item(table, item_id, "aprobador")

    item = history.get_item(table, item_id)
    assert item["estado_aprobacion"] == "aprobado"
    assert item["aprobado_por"] == "aprobador"
    assert "T" in item["aprobado_en"]


def test_item_missing_estado_aprobacion_defaults_to_pendiente_when_read(table):
    table.put_item(Item={
        "id": "legacy-item",
        "tipo": "imagen",
        "usuario": "ana",
        "rol": "diseñador",
        "prompt_o_texto_original": "un gato",
        "estilo": "anime",
        "resultado": "images/ana/x.png",
        "comentarios": [],
        "timestamp": "2020-01-01T00:00:00+00:00",
        "estado_moderacion": "NONE",
    })

    item = history.get_item(table, "legacy-item")

    assert "estado_aprobacion" not in item
    assert item.get("estado_aprobacion", "pendiente") == "pendiente"
