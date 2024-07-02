from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Tuple
import json
import os

app = FastAPI()


class DataModel(BaseModel):
    data: List[Tuple[float, float]]


@app.post("/current_latency/")
async def upload_current_latency_data(cl_data: DataModel):
    """
    Upload a list of latency data.
    """
    print(cl_data)
    try:
        # Check if directory exists, create if it doesn't
        if not os.path.exists("data"):
            os.makedirs("data")

        # Define the path to the JSON file
        file_path = os.path.join("tps", "current_latency.json")

        # If the file exists, load the existing data
        if os.path.exists(file_path):
            with open(file_path, "r") as log_file:
                existing_data = json.load(log_file)
        else:
            existing_data = []

        # Append the new data to the existing data
        existing_data.extend(cl_data.data)

        # Save the combined data back to the JSON file
        with open(file_path, "w") as log_file:
            json.dump(existing_data, log_file)

        print("Received log")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An error occurred while saving the data: {e}"
        )


@app.post("/delivered_latency/")
async def upload_latency_data(dl_data: DataModel):
    """
    Upload a list of latency data.
    """
    print(dl_data)
    try:
        # Check if directory exists, create if it doesn't
        if not os.path.exists("data"):
            os.makedirs("data")

        # Define the path to the JSON file
        file_path = os.path.join("tps", "delivered_latency.json")

        # If the file exists, load the existing data
        if os.path.exists(file_path):
            with open(file_path, "r") as log_file:
                existing_data = json.load(log_file)
        else:
            existing_data = []

        # Append the new data to the existing data
        existing_data.extend(dl_data.data)

        # Save the combined data back to the JSON file
        with open(file_path, "w") as log_file:
            json.dump(existing_data, log_file)

        print("Received log")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An error occurred while saving the data: {e}"
        )
