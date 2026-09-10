import uuid
from datetime import datetime, timedelta, timezone

from boto3.dynamodb.conditions import Attr


def get_table(region_name, table_name, aws_access_key_id=None, aws_secret_access_key=None):
    import boto3
    resource = boto3.resource(
        "dynamodb",
        region_name=region_name,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )
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
        "estado_aprobacion": "pendiente",
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
        "estado_aprobacion": "pendiente",
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


def approve_item(table, item_id, approved_by):
    table.update_item(
        Key={"id": item_id},
        UpdateExpression="SET estado_aprobacion = :estado, aprobado_por = :por, aprobado_en = :en",
        ExpressionAttributeValues={
            ":estado": "aprobado",
            ":por": approved_by,
            ":en": _now_iso(),
        },
    )


def get_item(table, item_id):
    response = table.get_item(Key={"id": item_id})
    return response.get("Item")


def list_items(table, tipo=None):
    kwargs = {}
    if tipo:
        kwargs["FilterExpression"] = Attr("tipo").eq(tipo)
    items = []
    while True:
        response = table.scan(**kwargs)
        items.extend(response.get("Items", []))
        if "LastEvaluatedKey" not in response:
            break
        kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
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
    items = []
    kwargs = {"FilterExpression": Attr("usuario").eq(user) & Attr("timestamp").gte(since_iso_timestamp)}
    while True:
        response = table.scan(**kwargs)
        items.extend(response.get("Items", []))
        if "LastEvaluatedKey" not in response:
            break
        kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
    return len(items)
