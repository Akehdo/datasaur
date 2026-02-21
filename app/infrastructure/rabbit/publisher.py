import pika
import json
import os
from uuid import UUID

RABBIT_URL = os.getenv("RABBIT_URL", "amqp://guest:guest@rabbitmq:5672/")


def publish_ticket(ticket_id):
    # 🔥 UUID → строка (иначе JSON падает)
    if isinstance(ticket_id, UUID):
        ticket_id = str(ticket_id)
    else:
        ticket_id = str(ticket_id)

    params = pika.URLParameters(RABBIT_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    channel.queue_declare(queue="ticket_queue", durable=True)

    channel.basic_publish(
        exchange="",
        routing_key="ticket_queue",
        body=json.dumps({"ticket_id": ticket_id}),
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type="application/json",
        ),
    )

    connection.close()