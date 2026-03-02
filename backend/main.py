from fastapi.middleware.cors import CORSMiddleware
import os
import pyarrow.parquet as pq
import pandas as pd
from fastapi import FastAPI
from collections import defaultdict

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DATA_FOLDER = "../player_data"

MAP_CONFIGS = {
    "AmbroseValley": {"scale": 900, "origin_x": -370, "origin_z": -473},
    "GrandRift": {"scale": 581, "origin_x": -290, "origin_z": -290},
    "Lockdown": {"scale": 1000, "origin_x": -500, "origin_z": -500},
}


# -----------------------------
# Utility functions
# -----------------------------
def world_to_minimap(x, z, map_id):
    config = MAP_CONFIGS[map_id]

    u = (x - config["origin_x"]) / config["scale"]
    v = (z - config["origin_z"]) / config["scale"]

    pixel_x = u * 1024
    pixel_y = (1 - v) * 1024

    return pixel_x, pixel_y


def is_bot(user_id):
    return user_id.isdigit()


def find_all_matches():
    match_index = defaultdict(lambda: {"date": None, "player_count": 0})

    for date_folder in os.listdir(BASE_DATA_FOLDER):
        full_path = os.path.join(BASE_DATA_FOLDER, date_folder)

        if not os.path.isdir(full_path):
            continue

        for filename in os.listdir(full_path):
            if filename.endswith(".nakama-0"):
                match_id = filename.split("_")[1].replace(".nakama-0", "")
                match_index[match_id]["date"] = date_folder
                match_index[match_id]["player_count"] += 1

    return match_index


def load_match(match_id):
    frames = []

    for date_folder in os.listdir(BASE_DATA_FOLDER):
        full_path = os.path.join(BASE_DATA_FOLDER, date_folder)

        if not os.path.isdir(full_path):
            continue

        for filename in os.listdir(full_path):
            if match_id in filename:
                filepath = os.path.join(full_path, filename)

                table = pq.read_table(filepath)
                df = table.to_pandas()

                df["event"] = df["event"].apply(
                    lambda x: x.decode("utf-8") if isinstance(x, bytes) else x
                )

                frames.append(df)

    if not frames:
        return None

    match_df = pd.concat(frames, ignore_index=True)
    match_df = match_df.sort_values("ts")

    start_time = match_df["ts"].min()
    match_df["seconds_from_start"] = (
        (match_df["ts"] - start_time).dt.total_seconds()
    )

    duration_seconds = match_df["seconds_from_start"].max()

    match_data = {
        "match_id": match_id,
        "map": match_df["map_id"].iloc[0],
        "duration": duration_seconds,
        "players": []
    }

    grouped = match_df.groupby("user_id")

    for user_id, player_df in grouped:

        player_data = {
            "user_id": user_id,
            "is_bot": is_bot(user_id),
            "events": []
        }

        for _, row in player_df.iterrows():

            px, py = world_to_minimap(row["x"], row["z"], row["map_id"])

            event_data = {
                "type": row["event"],
                "x": round(px, 2),
                "y": round(py, 2),
                "time": round(row["seconds_from_start"], 3)
            }

            player_data["events"].append(event_data)

        match_data["players"].append(player_data)

    return match_data


# -----------------------------
# API Endpoints
# -----------------------------
@app.get("/")
def root():
    return {"message": "LILA Player Journey API Running"}


@app.get("/matches")
def list_matches():
    match_index = find_all_matches()

    results = []

    for match_id, info in match_index.items():
        results.append({
            "match_id": match_id,
            "date": info["date"],
            "player_count": info["player_count"]
        })

    return results


@app.get("/match/{match_id}")
def get_match(match_id: str):
    match_data = load_match(match_id)

    if not match_data:
        return {"error": "Match not found"}

    return match_data