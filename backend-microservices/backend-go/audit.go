package main

import (
    "database/sql"
    "encoding/json"
    _ "github.com/lib/pq"
    "time"
)

func AuditLog(db *sql.DB, action, entity, entityID, userID, requestIP string, details map[string]any) error {
    jsonDetails, _ := json.Marshal(details)

    _, err := db.Exec(`
        INSERT INTO audit_log (timestamp, service, user_id, action, entity, entity_id, request_ip, details)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    `,
        time.Now().UTC(),
        "backend-go",
        userID,
        action,
        entity,
        entityID,
        requestIP,
        jsonDetails,
    )

    return err
}
