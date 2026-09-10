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
