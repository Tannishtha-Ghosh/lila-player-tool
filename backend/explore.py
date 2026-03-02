import os
import pyarrow.parquet as pq
import pandas as pd
from collections import defaultdict
import json

DATA_FOLDER = "../player_data/February_10"

# -----------------------------------
# STEP 1: Count files per match
# -----------------------------------
match_counts = defaultdict(int)

for filename in os.listdir(DATA_FOLDER):
    if filename.endswith(".nakama-0"):
        match_id = filename.split("_")[1].replace(".nakama-0", "")
        match_counts[match_id] += 1

best_match = max(match_counts, key=match_counts.get)

print("Match with most players:", best_match)
print("Number of player files:", match_counts[best_match])

# -----------------------------------
# STEP 2: Load full match
# -----------------------------------
frames = []

for filename in os.listdir(DATA_FOLDER):
    if best_match in filename:
        filepath = os.path.join(DATA_FOLDER, filename)

        table = pq.read_table(filepath)
        df = table.to_pandas()

        # Decode event column
        df["event"] = df["event"].apply(
            lambda x: x.decode("utf-8") if isinstance(x, bytes) else x
        )

        frames.append(df)

match_df = pd.concat(frames, ignore_index=True)
match_df = match_df.sort_values("ts")

# -----------------------------------
# STEP 3: Convert timestamps
# -----------------------------------
start_time = match_df["ts"].min()
match_df["seconds_from_start"] = (
    (match_df["ts"] - start_time).dt.total_seconds()
)

duration_seconds = match_df["seconds_from_start"].max()

# -----------------------------------
# STEP 4: World → Minimap Conversion
# -----------------------------------
def world_to_minimap(x, z, map_id):
    map_configs = {
        "AmbroseValley": {"scale": 900, "origin_x": -370, "origin_z": -473},
        "GrandRift": {"scale": 581, "origin_x": -290, "origin_z": -290},
        "Lockdown": {"scale": 1000, "origin_x": -500, "origin_z": -500},
    }

    config = map_configs[map_id]

    u = (x - config["origin_x"]) / config["scale"]
    v = (z - config["origin_z"]) / config["scale"]

    pixel_x = u * 1024
    pixel_y = (1 - v) * 1024

    return pixel_x, pixel_y

# -----------------------------------
# STEP 5: Detect Bots
# -----------------------------------
def is_bot(user_id):
    return user_id.isdigit()

# -----------------------------------
# STEP 6: Build Clean Match Structure
# -----------------------------------
match_data = {
    "match_id": best_match,
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

# -----------------------------------
# STEP 7: Print Summary
# -----------------------------------
print("\n===== CLEAN STRUCTURE SUMMARY =====")
print("Map:", match_data["map"])
print("Duration:", match_data["duration"])
print("Total players:", len(match_data["players"]))

print("\nSample player:")
print(json.dumps(match_data["players"][0], indent=2))