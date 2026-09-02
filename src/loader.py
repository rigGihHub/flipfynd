import json
from pathlib import Path


def load_data(path: str = "tradera_data.json") -> list:
    file_path = Path(path)

    if not file_path.exists():
        return []

    try:
        with file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError:
        return []
    except OSError:
        return []

    if isinstance(data, list):
        return data

    return []

def load_sold_comps(path: str = "data/sold_comps.json") -> list:
    """Load optional historical sold-comparable records.

    The file is intentionally separate from live Tradera listings so sold
    evidence can never accidentally appear as an active buy candidate.
    """
    return load_data(path)
