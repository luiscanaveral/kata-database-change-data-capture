import os
import json
import logging
import re
import time
from datetime import datetime
from kafka import KafkaConsumer
from azure.storage.blob import BlobServiceClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('cdc-sink')

KAFKA_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
AZURITE_CONN_STR = os.environ.get('AZURITE_CONNECTION_STRING')
CONTAINER_NAME = os.environ.get('BLOB_CONTAINER', 'cdc-events')

OP_MAP = {'c': 'create', 'u': 'update', 'd': 'delete', 'r': 'snapshot'}

TOPIC_PATTERN = re.compile(r'ticketdb\.public\.(\w+)')


def wait_for_blob_service(conn_str, max_retries=30, delay=3):
    for i in range(max_retries):
        try:
            svc = BlobServiceClient.from_connection_string(conn_str)
            svc.get_service_properties()
            logger.info("Connected to Azurite")
            return svc
        except Exception as e:
            if i < max_retries - 1:
                logger.warning(f"Azurite not ready ({e}), retrying in {delay}s... ({i+1}/{max_retries})")
                time.sleep(delay)
            else:
                raise


def ensure_container(blob_service):
    try:
        container_client = blob_service.get_container_client(CONTAINER_NAME)
        container_client.get_container_properties()
        logger.info(f"Container '{CONTAINER_NAME}' already exists")
    except Exception:
        logger.info(f"Creating container '{CONTAINER_NAME}'...")
        blob_service.create_container(CONTAINER_NAME)


def upload_event(blob_service, table_name, operation, event_id, timestamp_ms, data):
    if timestamp_ms:
        dt = datetime.fromtimestamp(timestamp_ms / 1000)
        blob_path = (
            f"{table_name}/{operation}/{dt.strftime('%Y/%m/%d')}/{event_id}_{timestamp_ms}.json"
        )
    else:
        blob_path = f"{table_name}/{operation}/unknown/{event_id}_{int(time.time() * 1000)}.json"

    try:
        blob_client = blob_service.get_blob_client(
            container=CONTAINER_NAME, blob=blob_path
        )
        content = json.dumps(data, indent=2)
        blob_client.upload_blob(content, overwrite=True)
        logger.info(f"Uploaded: {blob_path}")
    except Exception as e:
        logger.error(f"Failed to upload {blob_path}: {e}")


def main():
    logger.info(f"Starting CDC Sink — Kafka: {KAFKA_SERVERS}")

    blob_service = wait_for_blob_service(AZURITE_CONN_STR)
    ensure_container(blob_service)

    consumer = KafkaConsumer(
        bootstrap_servers=KAFKA_SERVERS,
        value_deserializer=lambda v: v.decode('utf-8'),
        key_deserializer=lambda k: k.decode('utf-8') if k else None,
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id='cdc-azurite-sink',
    )

    consumer.subscribe(pattern=r'ticketdb\.public\..*')
    logger.info("Subscribed to ticketdb.public.* topics")

    for msg in consumer:
        try:
            match = TOPIC_PATTERN.match(msg.topic)
            if not match:
                continue
            table_name = match.group(1)

            if not msg.value:
                continue

            event = json.loads(msg.value)
            payload = event.get('payload', {})

            op = payload.get('op', 'r')
            operation = OP_MAP.get(op, op)
            ts_ms = payload.get('ts_ms', int(time.time() * 1000))

            after = payload.get('after')
            before = payload.get('before')
            record = after or before or {}
            event_id = record.get('id', 'unknown')

            upload_event(blob_service, table_name, operation, event_id, ts_ms, event)

        except Exception as e:
            logger.error(f"Error processing message from {msg.topic}: {e}")


if __name__ == '__main__':
    main()
