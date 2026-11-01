
from flask import Flask, request, jsonify
from database import get_connection, create_table

from services.sentiment import analyze_sentiment
from services.classification import classify_ticket
from services.priority import detect_priority

import math

app = Flask(__name__)

# Database initialize
create_table()

ALLOWED_STATUSES = [
    "Open",
    "In Progress",
    "Resolved"
]


# Ticket analysis function
def analyze_description(description, temperature=None):

    sentiment_result = analyze_sentiment(description)

    category = classify_ticket(description)

    priority = detect_priority(
        description,
        temperature
    )

    return {
        "sentiment": sentiment_result["sentiment"],
        "sentiment_score": sentiment_result["polarity"],
        "category": category,
        "priority": priority
    }


# Get ticket by ID
def get_ticket_by_id(ticket_id):

    connection = get_connection()

    try:

        ticket = connection.execute(
            "SELECT * FROM tickets WHERE id = ?",
            (ticket_id,)
        ).fetchone()

        return dict(ticket) if ticket else None

    finally:
        connection.close()


# HOME API
@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "message": "Customer Support Ticket Analysis API",
        "status": "Running",
        "version": "2.0"
    })


# HEALTH CHECK API
@app.route("/health", methods=["GET"])
def health():

    return jsonify({
        "status": "Healthy",
        "database": "SQLite"
    })


# CREATE TICKET API
@app.route("/api/tickets", methods=["POST"])
def create_ticket():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Valid JSON required"}), 400

    customer_name = data.get("customer_name")
    subject = data.get("subject")
    description = data.get("description")

    if not all(
        isinstance(value, str) and value.strip()
        for value in [customer_name, subject, description]
    ):

        return jsonify({
            "error": "Customer name, subject and description are required"
        }), 400

    customer_name = customer_name.strip()
    subject = subject.strip()
    description = description.strip()

    # Automatic analysis
    analysis = analyze_description(
        subject + " " + description
    )

    connection = get_connection()

    try:

        cursor = connection.execute("""
            INSERT INTO tickets (
                customer_name,
                subject,
                description,
                priority,
                status,
                category,
                sentiment,
                sentiment_score,
                source,
                created_at
            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)

        """, (
            customer_name,
            subject,
            description,
            analysis["priority"],
            "Open",
            analysis["category"],
            analysis["sentiment"],
            analysis["sentiment_score"],
            "Manual"
        ))

        ticket_id = cursor.lastrowid

        connection.commit()

    finally:
        connection.close()

    return jsonify({

        "message": "Ticket created successfully",

        "ticket_id": ticket_id,

        "analysis": analysis

    }), 201


# GET ALL TICKETS API
@app.route("/api/tickets", methods=["GET"])
def get_tickets():

    filters = {
        "status": request.args.get("status"),
        "priority": request.args.get("priority"),
        "category": request.args.get("category"),
        "sentiment": request.args.get("sentiment")
    }

    allowed_filters = {

        "status": ALLOWED_STATUSES,

        "priority": [
            "Low", "Medium", "High", "Critical"
        ],

        "sentiment": [
            "Positive", "Negative", "Neutral"
        ],

        "category": [
            "Technical", "Billing",
            "Account", "Delivery",
            "Service", "General"
        ]
    }

    conditions = []
    values = []

    for field, value in filters.items():

        if value:

            if value not in allowed_filters[field]:

                return jsonify({
                    "error": f"Invalid {field} filter"
                }), 400

            conditions.append(f"{field} = ?")
            values.append(value)

    query = "SELECT * FROM tickets"

    if conditions:

        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY id DESC"

    connection = get_connection()

    try:

        tickets = connection.execute(
            query, values
        ).fetchall()

        return jsonify({

            "count": len(tickets),

            "tickets": [
                dict(ticket) for ticket in tickets
            ]

        })

    finally:
        connection.close()


# GET SINGLE TICKET API
@app.route("/api/tickets/<int:ticket_id>", methods=["GET"])
def get_single_ticket(ticket_id):

    ticket = get_ticket_by_id(ticket_id)

    if not ticket:

        return jsonify({
            "error": "Ticket not found"
        }), 404

    return jsonify(ticket)


# UPDATE TICKET STATUS API
@app.route("/api/tickets/<int:ticket_id>", methods=["PUT"])
def update_ticket(ticket_id):

    data = request.get_json(silent=True)

    if not isinstance(data, dict):

        return jsonify({
            "error": "Valid JSON required"
        }), 400

    status = data.get("status")

    if status not in ALLOWED_STATUSES:

        return jsonify({
            "error": "Invalid status",
            "allowed_statuses": ALLOWED_STATUSES
        }), 400

    connection = get_connection()

    try:

        cursor = connection.execute("""

            UPDATE tickets

            SET status = ?,
                updated_at = CURRENT_TIMESTAMP

            WHERE id = ?

        """, (status, ticket_id))

        connection.commit()

        if cursor.rowcount == 0:

            return jsonify({
                "error": "Ticket not found"
            }), 404

    finally:
        connection.close()

    return jsonify({

        "message": "Ticket updated successfully",

        "ticket_id": ticket_id,

        "status": status

    })


# DELETE TICKET API
@app.route("/api/tickets/<int:ticket_id>", methods=["DELETE"])
def delete_ticket(ticket_id):

    connection = get_connection()

    try:

        cursor = connection.execute(
            "DELETE FROM tickets WHERE id = ?",
            (ticket_id,)
        )

        connection.commit()

        if cursor.rowcount == 0:

            return jsonify({
                "error": "Ticket not found"
            }), 404

    finally:
        connection.close()

    return jsonify({

        "message": "Ticket deleted successfully",

        "ticket_id": ticket_id

    })


# REANALYZE EXISTING TICKET
@app.route("/api/tickets/<int:ticket_id>/analyze", methods=["POST"])
def reanalyze_ticket(ticket_id):

    ticket = get_ticket_by_id(ticket_id)

    if not ticket:

        return jsonify({
            "error": "Ticket not found"
        }), 404

    analysis = analyze_description(
        ticket["subject"] + " " + ticket["description"],
        ticket["temperature"]
    )

    connection = get_connection()

    try:

        connection.execute("""

            UPDATE tickets

            SET category = ?,
                sentiment = ?,
                sentiment_score = ?,
                priority = ?,
                updated_at = CURRENT_TIMESTAMP

            WHERE id = ?

        """, (

            analysis["category"],
            analysis["sentiment"],
            analysis["sentiment_score"],
            analysis["priority"],
            ticket_id

        ))

        connection.commit()

    finally:
        connection.close()

    return jsonify({

        "message": "Ticket reanalyzed successfully",

        "ticket_id": ticket_id,

        "analysis": analysis

    })


# IOT SENSOR ALERT API
@app.route("/api/iot/alerts", methods=["POST"])
def iot_alert():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):

        return jsonify({
            "error": "Valid JSON required"
        }), 400

    device_id = data.get("device_id")
    temperature = data.get("temperature")

    if not isinstance(device_id, str) or not device_id.strip():

        return jsonify({
            "error": "Valid device_id required"
        }), 400

    try:

        temperature = float(temperature)

    except (ValueError, TypeError):

        return jsonify({
            "error": "Temperature must be numeric"
        }), 400

    if not math.isfinite(temperature) or not (-50 <= temperature <= 200):

        return jsonify({
            "error": "Invalid temperature value"
        }), 400

    device_id = device_id.strip()

    if temperature <= 50:

        return jsonify({

            "message": "Temperature is normal",

            "device_id": device_id,

            "temperature": temperature

        }), 200

    connection = get_connection()

    try:

        # Duplicate alert check
        existing = connection.execute("""

            SELECT id FROM tickets

            WHERE device_id = ?
            AND source = 'IoT'
            AND status != 'Resolved'

            ORDER BY id DESC

            LIMIT 1

        """, (device_id,)).fetchone()

        if existing:

            return jsonify({

                "message": "An active alert already exists",

                "ticket_id": existing["id"],

                "device_id": device_id

            }), 200

        description = (

            f"IoT device {device_id} reported "

            f"high temperature of {temperature} Celsius"

        )

        analysis = analyze_description(
            description,
            temperature
        )

        cursor = connection.execute("""

            INSERT INTO tickets (

                customer_name,
                subject,
                description,
                priority,
                status,
                category,
                sentiment,
                sentiment_score,
                device_id,
                temperature,
                source,
                created_at

            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)

        """, (

            f"IoT Device {device_id}",
            "High Temperature Alert",
            description,
            analysis["priority"],
            "Open",
            analysis["category"],
            analysis["sentiment"],
            analysis["sentiment_score"],
            device_id,
            temperature,
            "IoT"

        ))

        ticket_id = cursor.lastrowid

        connection.commit()

    finally:
        connection.close()

    return jsonify({

        "message": "IoT alert ticket created",

        "ticket_id": ticket_id,

        "device_id": device_id,

        "temperature": temperature,

        "analysis": analysis

    }), 201


# TICKET ANALYTICS API
@app.route("/api/analysis", methods=["GET"])
def analyze_tickets():

    connection = get_connection()

    try:

        total = connection.execute(
            "SELECT COUNT(*) FROM tickets"
        ).fetchone()[0]

        resolved = connection.execute("""

            SELECT COUNT(*) FROM tickets

            WHERE status = 'Resolved'

        """).fetchone()[0]

        pending = connection.execute("""

            SELECT COUNT(*) FROM tickets

            WHERE status != 'Resolved'

        """).fetchone()[0]

        priority_data = connection.execute("""

            SELECT priority, COUNT(*) AS total

            FROM tickets

            GROUP BY priority

        """).fetchall()

        category_data = connection.execute("""

            SELECT category, COUNT(*) AS total

            FROM tickets

            GROUP BY category

        """).fetchall()

        sentiment_data = connection.execute("""

            SELECT sentiment, COUNT(*) AS total

            FROM tickets

            GROUP BY sentiment

        """).fetchall()

        source_data = connection.execute("""

            SELECT source, COUNT(*) AS total

            FROM tickets

            GROUP BY source

        """).fetchall()

        return jsonify({

            "total_tickets": total,

            "resolved_tickets": resolved,

            "pending_tickets": pending,

            "resolution_rate": round(
                (resolved / total) * 100, 2
            ) if total else 0,

            "priority_distribution": {
                row["priority"]: row["total"]
                for row in priority_data
            },

            "category_distribution": {
                row["category"]: row["total"]
                for row in category_data
            },

            "sentiment_distribution": {
                row["sentiment"]: row["total"]
                for row in sentiment_data
            },

            "source_distribution": {
                row["source"]: row["total"]
                for row in source_data
            }

        })

    finally:
        connection.close()


if __name__ == "__main__":

    app.run(debug=True)
