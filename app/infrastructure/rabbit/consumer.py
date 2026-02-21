import pika
import json
import os
import sys
from datetime import datetime

from app.core.db import SessionLocal
from app.modules.assignment.service import assign_ticket
from app.modules.tickets.models import Ticket
from app.infrastructure.ai.ollama_client import analyze_ticket
import requests


sys.stdout.reconfigure(line_buffering=True)

RABBIT_URL = os.getenv("RABBIT_URL", "amqp://guest:guest@rabbitmq:5672/")
API_URL = os.getenv("API_URL", "http://app:8000")


def log(msg):
    print(f"[{datetime.utcnow().isoformat()}] {msg}", flush=True)


def nearest_office_via_api(address: str):
    log(f"Calling nearest-office API for address: {address}")
    try:
        r = requests.post(
            f"{API_URL}/nearest-office",
            json={"address": address},
            timeout=10
        )
        r.raise_for_status()
        data = r.json()
        log(f"Nearest office response: {data}")
        return data
    except Exception as e:
        log(f"API error: {e}")
        return None


def callback(ch, method, properties, body):
    log(f"Received message: {body}")

    data = json.loads(body)
    ticket_id = data["ticket_id"]

    session = SessionLocal()

    try:
        ticket = session.get(Ticket, ticket_id)
        log(f"Loaded ticket: {ticket_id}")

        if not ticket:
            log("Ticket not found. ACK.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        if ticket.status == "DONE":
            log("Ticket already DONE. ACK.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # блокируем тикет
        ticket.status = "PROCESSING"
        session.commit()
        log("Ticket marked as PROCESSING")

        # 🔥 LLM
        log("Starting LLM analysis...")
        ai = analyze_ticket(
            desc=ticket.description,
            segment=ticket.segment,
            country=ticket.country,
            region=ticket.region,
        )
        log(f"LLM result: {ai}")

        # 🔥 Адрес
        full_address = ", ".join(
            [ticket.city, ticket.street, ticket.house, ticket.region, ticket.country]
        )

        nearest = nearest_office_via_api(full_address)

        if not nearest:
            log("No nearest office found. Marking FAILED.")
            ticket.status = "FAILED"
            session.commit()
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        office_city = nearest["city"]
        log(f"Assigning ticket to office: {office_city}")

        manager, office = assign_ticket(
            session, ticket, forced_office=office_city
        )

        ticket.assigned_manager_id = manager.id
        ticket.assigned_office = office
        ticket.ticket_type = ai.get("ticket_type")
        ticket.priority = ai.get("priority")
        ticket.language = ai.get("language")
        ticket.summary = ai.get("summary")
        ticket.recommendation = ai.get("recommendation")

        ticket.status = "DONE"
        session.commit()

        ch.basic_ack(delivery_tag=method.delivery_tag)

        log(f"Ticket {ticket_id} processed successfully.")

    except Exception as e:
        session.rollback()
        log(f"ERROR during processing: {e}")
        # не ack → сообщение вернётся в очередь
    finally:
        session.close()


def start_consumer():
    log("Starting RabbitMQ consumer...")

    params = pika.URLParameters(RABBIT_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    channel.queue_declare(queue="ticket_queue", durable=True)
    channel.basic_qos(prefetch_count=1)

    channel.basic_consume(
        queue="ticket_queue",
        on_message_callback=callback,
    )

    log("Waiting for messages...")
    channel.start_consuming()


if __name__ == "__main__":
    start_consumer()