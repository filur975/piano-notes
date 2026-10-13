"""Word-list storage for Glosor: one JSON file with all lists."""
import json
import os
import shutil
import sys
import tempfile

FROZEN = getattr(sys, "frozen", False)  # True when running as a PyInstaller .exe


def _data_file():
    if not FROZEN:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "lists.json")
    # Packaged app: keep word lists in the user's profile so they survive updates.
    root = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(root, "Glosor", "lists.json")


DATA_FILE = _data_file()

EXAMPLE_DATA = {
    "lists": [
        {
            "id": "exempel",
            "name": "Exempellista: Djur",
            "words": [
                {"sv": "hund", "en": "dog", "correct": 0, "wrong": 0},
                {"sv": "katt", "en": "cat", "correct": 0, "wrong": 0},
                {"sv": "häst", "en": "horse", "correct": 0, "wrong": 0},
                {"sv": "fisk", "en": "fish", "correct": 0, "wrong": 0},
                {"sv": "fågel", "en": "bird", "correct": 0, "wrong": 0},
                {"sv": "ko", "en": "cow", "correct": 0, "wrong": 0},
            ],
        }
    ]
}


def load_data():
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or not isinstance(data.get("lists"), list):
            raise ValueError("bad structure")
        return data
    except FileNotFoundError:
        pass
    except (ValueError, OSError):
        # Corrupt file: keep a backup and start fresh.
        try:
            shutil.copy(DATA_FILE, DATA_FILE + ".bak")
        except OSError:
            pass
    data = json.loads(json.dumps(EXAMPLE_DATA))
    save_data(data)
    return data


def save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(DATA_FILE), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)


def clean_words(raw, existing=None):
    """Drop empty rows and keep the counters of words that didn't change."""
    old = {(w["sv"], w["en"]): w for w in (existing or [])}
    words = []
    for item in raw:
        sv = str(item.get("sv", "")).strip()
        en = str(item.get("en", "")).strip()
        if not sv or not en:
            continue
        prev = old.get((sv, en), {})
        words.append({"sv": sv, "en": en,
                      "correct": int(prev.get("correct", 0)),
                      "wrong": int(prev.get("wrong", 0))})
    return words
