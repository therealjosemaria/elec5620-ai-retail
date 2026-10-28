"""Explicit offline recovery after a validator fix. This command cannot call a model."""
import argparse
import json
import os
from pathlib import Path
import sqlite3
from uuid import UUID

from dotenv import load_dotenv
from backend.recommendation_store import RecommendationStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request_id", type=UUID)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    load_dotenv(root / ".env")
    path = os.getenv("DATABASE_PATH", str(root / "data/retail.sqlite3"))
    result = RecommendationStore(lambda: sqlite3.connect(path), mode="offline", daily_limit=0).revalidate(args.request_id)
    print(json.dumps({"request_id":str(result.request_id),"outcome":result.outcome,
        "model_provider":result.model_provider,"revalidated_offline":True,"model_calls":0}))


if __name__ == "__main__":
    main()
