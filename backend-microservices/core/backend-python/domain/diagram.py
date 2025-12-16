from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
import uuid

@dataclass(frozen=True)
class DiagramId:
    value: str

    @staticmethod
    def new() -> "DiagramId":
        return DiagramId(str(uuid.uuid4()))


@dataclass
class Diagram:
    id: DiagramId
    title: str
    description: Optional[str]
    s3_key: str
    diagram_type: str = "diagram"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    tags: Optional[List[str]] = None

    def rename(self, new_title: str):
        if not new_title or not new_title.strip():
            raise ValueError("Diagram title cannot be empty")
        self.title = new_title
        self.updated_at = datetime.utcnow()

    def retag(self, tags: Optional[List[str]]):
        self.tags = tags
        self.updated_at = datetime.utcnow()
