import psycopg2
import os
import json
from datetime import datetime


def audit_log(action, entity=None, entity_id=None, user_id=None, request_ip=None, details=None):
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO audit_log (timestamp, service, user_id, action, entity, entity_id, request_ip, details)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        datetime.utcnow(),
        "backend-python",
        user_id,
        action,
        entity,
        entity_id,
        request_ip,
        json.dumps(details) if details else None
    ))

    conn.commit()
    cur.close()
    conn.close()
