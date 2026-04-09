import redis
import pandas as pd
import json
from tqdm import tqdm

# ========================
# CONFIG
# ========================
BATCH_SIZE = 5000

r = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True
)

# ========================
# 1. IMPORT EVENTS
# ========================
def import_events(file_path):
    print(" Importing events...")

    for chunk in pd.read_csv(file_path, chunksize=BATCH_SIZE):
        pipe = r.pipeline()

        for _, row in chunk.iterrows():
            visitor = int(row["visitorid"])
            item = int(row["itemid"])

            event = {
                "itemid": item,
                "event": row["event"],
                "timestamp": int(row["timestamp"])
            }

            # user history
            pipe.rpush(f"user:{visitor}:events", json.dumps(event))

            # item → users (phục vụ recommendation)
            pipe.sadd(f"item:{item}:users", visitor)

        pipe.execute()

    print(" Done events")


# ========================
# 2. IMPORT ITEM PROPERTIES (2 FILE)
# ========================
def import_item_properties(file_path):
    print(f" Importing {file_path} ...")

    for chunk in pd.read_csv(file_path, chunksize=BATCH_SIZE,
                             usecols=["itemid", "property", "value"]):

        pipe = r.pipeline()

        for _, row in chunk.iterrows():
            item = int(row["itemid"])
            prop = row["property"]
            value = row["value"]

            #  chỉ giữ property quan trọng (giảm 90% data)
            if prop in ["categoryid", "available"]:
                pipe.hset(f"item:{item}:props", prop, value)

        pipe.execute()

    print(f" Done {file_path}")


# ========================
# 3. IMPORT CATEGORY TREE
# ========================
def import_category_tree(file_path):
    print(" Importing category tree...")

    df = pd.read_csv(file_path)

    pipe = r.pipeline()

    for _, row in df.iterrows():
        cat = int(row["categoryid"])
        parent = row["parentid"]

        pipe.hset(
            f"category:{cat}",
            mapping={
                "parent": int(parent) if not pd.isna(parent) else -1
            }
        )

    pipe.execute()

    print(" Done category tree")


# ========================
# MAIN
# ========================
if __name__ == "__main__":

    # sửa đúng path file của bạn
    import_events("F:/archive/events.csv")

    import_item_properties("F:/archive/item_properties_part1.csv")
    import_item_properties("F:/archive/item_properties_part2.csv")

    import_category_tree("F:/archive/category_tree.csv")

    print("IMPORT SUCCESS ")