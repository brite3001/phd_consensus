from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI()


class LatencyData(BaseModel):
    latencies: List[float]


@app.post("/logs/")
async def upload_latency_data(latency_data: LatencyData):
    """
    Upload a list of latency data.
    """
    with open("latency.txt", "a") as log_file:
        log_file.write(f"{latency_data.latencies}\n")

    print("Received log")
    return {"status": "success"}
