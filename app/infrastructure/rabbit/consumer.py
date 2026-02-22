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
        log(f"GEO API ERROR: {e}")
        return None


def safe_join_address(ticket: Ticket) -> str:
    return ", ".join(
        filter(None, [
            ticket.city,
            ticket.street,
            ticket.house,
            ticket.region,
            ticket.country
        ])
    )


def callback(ch, method, properties, body):
    log(f"Received message: {body}")

    session = SessionLocal()

    try:
        data = json.loads(body)
        ticket_id = data.get("ticket_id")

        if not ticket_id:
            log("No ticket_id in message. ACK.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        ticket = session.get(Ticket, ticket_id)

        if not ticket:
            log("Ticket not found. ACK.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        if ticket.status in ["DONE", "FAILED"]:
            log(f"Ticket already {ticket.status}. ACK.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # -----------------------------
        # LOCK TICKET
        # -----------------------------
        ticket.status = "PROCESSING"
        session.commit()
        log("Ticket marked as PROCESSING")

        # -----------------------------
        # LLM
        # -----------------------------
        try:
            log("Starting LLM analysis...")
            ai = analyze_ticket(
                desc=ticket.description,
                segment=ticket.segment,
                country=ticket.country,
                region=ticket.region,
            )
            log(f"LLM result: {ai}")
        except Exception as e:
            raise Exception(f"AI_FAILED: {e}")

        # -----------------------------
        # GEO
        # -----------------------------
        full_address = safe_join_address(ticket)

        if not full_address:
            raise Exception("ADDRESS_EMPTY")

        nearest = nearest_office_via_api(full_address)

        if not nearest:
            raise Exception("GEO_FAILED")

        office_city = nearest.get("city")
        if not office_city:
            raise Exception("OFFICE_CITY_MISSING")

        log(f"Assigning ticket to office: {office_city}")

        # -----------------------------
        # ASSIGN
        # -----------------------------
        try:
            manager, office = assign_ticket(
                session, ticket, forced_office=office_city
            )
        except Exception as e:
            raise Exception(f"ASSIGN_FAILED: {e}")

        # -----------------------------
        # SAVE RESULT
        # -----------------------------
        ticket.assigned_manager_id = manager.id
        ticket.assigned_office = office
        ticket.ticket_type = ai.get("ticket_type")
        ticket.priority = ai.get("priority")
        ticket.language = ai.get("language")
        ticket.summary = ai.get("summary")
        ticket.recommendation = ai.get("recommendation")
        ticket.status = "DONE"

        session.commit()

        log(f"Ticket {ticket_id} processed successfully.")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        session.rollback()
        log(f"ERROR during processing: {e}")

        try:
            ticket = session.get(Ticket, ticket_id)
            if ticket:
                ticket.status = "FAILED"
                ticket.error_message = str(e)
                session.commit()
        except Exception as inner:
            log(f"Failed to update ticket status: {inner}")

        ch.basic_ack(delivery_tag=method.delivery_tag)

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