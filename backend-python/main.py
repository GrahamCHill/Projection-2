from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import httpx
import os
import psycopg2
from audit import audit_log
from s3_storage import upload_diagram, download_diagram, delete_diagram, get_presigned_url
from datetime import datetime
import uuid

GO_SERVICE_URL = os.getenv("GO_SERVICE_URL")
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://app.test", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for diagrams
class DiagramCreate(BaseModel):
    title: str
    description: Optional[str] = None
    content: str
    created_by: Optional[str] = None
    tags: Optional[List[str]] = None

class DiagramResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    s3_key: str
    diagram_type: str
    created_at: str
    updated_at: str
    created_by: Optional[str]
    tags: Optional[List[str]]
    content_url: Optional[str] = None

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

@app.get("/ping")
def ping():
    return {"message": "Python backend up"}

@app.get("/go-data")
def call_go():
    r = httpx.get(f"{GO_SERVICE_URL}/internal")
    return {"go_response": r.json()}

@app.post("/api/diagrams", response_model=DiagramResponse)
def create_diagram(diagram: DiagramCreate):
    """Save a new diagram to S3 and store metadata in PostgreSQL"""
    try:
        # Upload to S3
        s3_key = upload_diagram(diagram.content)
        
        # Store metadata in database
        conn = get_db_connection()
        cur = conn.cursor()
        
        diagram_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO diagrams (id, title, description, s3_key, created_by, tags)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, title, description, s3_key, diagram_type, created_at, updated_at, created_by, tags
        """, (diagram_id, diagram.title, diagram.description, s3_key, diagram.created_by, diagram.tags))
        
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        return DiagramResponse(
            id=str(row[0]),
            title=row[1],
            description=row[2],
            s3_key=row[3],
            diagram_type=row[4],
            created_at=row[5].isoformat(),
            updated_at=row[6].isoformat(),
            created_by=row[7],
            tags=row[8],
            content_url=get_presigned_url(s3_key)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/diagrams", response_model=List[DiagramResponse])
def list_diagrams(limit: int = 50, offset: int = 0):
    """List all diagrams with pagination"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, title, description, s3_key, diagram_type, created_at, updated_at, created_by, tags
            FROM diagrams
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        return [
            DiagramResponse(
                id=str(row[0]),
                title=row[1],
                description=row[2],
                s3_key=row[3],
                diagram_type=row[4],
                created_at=row[5].isoformat(),
                updated_at=row[6].isoformat(),
                created_by=row[7],
                tags=row[8],
                content_url=get_presigned_url(row[3])
            )
            for row in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/diagrams/{diagram_id}", response_model=DiagramResponse)
def get_diagram(diagram_id: str, include_content: bool = False):
    """Get a specific diagram by ID"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, title, description, s3_key, diagram_type, created_at, updated_at, created_by, tags
            FROM diagrams
            WHERE id = %s
        """, (diagram_id,))
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Diagram not found")
        
        response = DiagramResponse(
            id=str(row[0]),
            title=row[1],
            description=row[2],
            s3_key=row[3],
            diagram_type=row[4],
            created_at=row[5].isoformat(),
            updated_at=row[6].isoformat(),
            created_by=row[7],
            tags=row[8],
            content_url=get_presigned_url(row[3])
        )
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/diagrams/{diagram_id}/content")
def get_diagram_content(diagram_id: str):
    """Get the actual diagram content from S3"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT s3_key FROM diagrams WHERE id = %s", (diagram_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Diagram not found")
        
        content = download_diagram(row[0])
        return {"content": content}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/diagrams/{diagram_id}")
def update_diagram_endpoint(diagram_id: str, diagram: DiagramCreate):
    """Update an existing diagram"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if diagram exists
        cur.execute("SELECT s3_key FROM diagrams WHERE id = %s", (diagram_id,))
        row = cur.fetchone()
        
        if not row:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Diagram not found")
        
        old_s3_key = row[0]
        
        # Upload new content to S3 (generates new key)
        s3_key = upload_diagram(diagram.content)
        
        # Delete old S3 file
        delete_diagram(old_s3_key)
        
        # Update database
        cur.execute("""
            UPDATE diagrams 
            SET title = %s, description = %s, s3_key = %s, 
                tags = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (diagram.title, diagram.description, s3_key, diagram.tags, diagram_id))
        
        conn.commit()
        
        # Fetch updated record
        cur.execute("""
            SELECT id, title, description, s3_key, diagram_type, 
                   created_at, updated_at, created_by, tags
            FROM diagrams WHERE id = %s
        """, (diagram_id,))
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        presigned_url = get_presigned_url(row[3])
        
        return {
            "id": str(row[0]),
            "title": row[1],
            "description": row[2],
            "s3_key": row[3],
            "diagram_type": row[4],
            "created_at": row[5].isoformat(),
            "updated_at": row[6].isoformat(),
            "created_by": row[7],
            "tags": row[8],
            "content_url": presigned_url
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/diagrams/{diagram_id}")
def delete_diagram_endpoint(diagram_id: str):
    """Delete a diagram from S3 and database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT s3_key FROM diagrams WHERE id = %s", (diagram_id,))
        row = cur.fetchone()
        
        if not row:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Diagram not found")
        
        # Delete from S3
        delete_diagram(row[0])
        
        # Delete from database
        cur.execute("DELETE FROM diagrams WHERE id = %s", (diagram_id,))
        conn.commit()
        cur.close()
        conn.close()
        
        return {"message": "Diagram deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    response = await call_next(request)

    audit_log(
        action="http_request",
        entity="route",
        entity_id=str(request.url.path),
        user_id=request.headers.get("X-User-ID"),
        request_ip=request.client.host,
        details={"method": request.method, "status": response.status_code}
    )

    return response