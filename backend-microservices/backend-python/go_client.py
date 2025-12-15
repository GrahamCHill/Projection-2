import httpx
import os

GO_URL = os.getenv("GO_SERVICE_URL")

def fetch_from_go():
    r = httpx.get(f"{GO_URL}/internal")
    return r.json()
