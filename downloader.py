
import os
import time
import json
import requests

from datetime import datetime, timedelta, timezone
from io import BytesIO
from PIL import Image


TARGET_RESOLUTION = 2160
TILE_SIZE = 550

BASE_URL = (
    "https://himawari8-dl.nict.go.jp/"
    "himawari8/img/D531106/"
)

OUTPUT = "output/earth.webp"

HISTORY_DIR = "history"
HISTORY_JSON = "history.json"

MAX_HISTORY = 200


def get_nearest_d(resolution):
    levels = [1, 2, 4, 8, 16, 20]
    return min(levels, key=lambda d: abs(d * TILE_SIZE - resolution))


def build_url(t, d, x, y):
    date = t.strftime("%Y/%m/%d")
    timestamp = t.strftime("%H%M%S")

    return (
        BASE_URL
        + f"{d}d/550/"
        + f"{date}/"
        + f"{timestamp}_{x}_{y}.png"
    )


def validate_image(img):
    if img.size != (TILE_SIZE, TILE_SIZE):
        return False

    extrema = img.getextrema()
    max_value = max(v[1] for v in extrema)
    min_value = min(v[0] for v in extrema)

    # 防止No Image占位图或纯黑异常图
    if max_value < 150:
        return False

    if max_value - min_value < 20:
        return False

    return True


def download_tile(t, d, x, y):

    url = build_url(t, d, x, y)

    for i in range(3):

        try:
            r = requests.get(
                url,
                timeout=(10, 30),
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            )

            if r.status_code == 200:

                img = Image.open(
                    BytesIO(r.content)
                ).convert("RGB")

                if validate_image(img):
                    return img

                raise Exception(
                    "Invalid satellite tile"
                )

        except Exception as e:
            print(
                "Tile retry:",
                i + 1,
                e
            )

        time.sleep(2)

    raise Exception(
        "Download failed: " + url
    )


def get_time_candidates():

    now = datetime.now(timezone.utc)

    result = []

    for offset in range(40, 240, 10):

        t = now - timedelta(minutes=offset)

        t = t.replace(
            minute=(t.minute // 10) * 10,
            second=0,
            microsecond=0
        )

        result.append(t)

    return result


def check_time(t, d):

    try:
        # 检查所有tile中的几个关键位置
        positions = [
            (0, 0),
            (d-1, 0),
            (0, d-1),
            (d-1, d-1)
        ]

        for x, y in positions:
            img = download_tile(
                t,
                d,
                x,
                y
            )

            if not validate_image(img):
                return False

        return True

    except Exception:
        return False


def find_latest_time(d):

    print("Searching satellite time...")

    for t in get_time_candidates():

        print(
            "Try:",
            t.strftime("%Y-%m-%d %H:%M")
        )

        if check_time(t, d):

            print("Found:", t)
            return t

    print("No valid satellite image")
    return None


def merge_tiles(t, d):

    size = d * TILE_SIZE

    canvas = Image.new(
        "RGB",
        (size, size)
    )

    for y in range(d):

        for x in range(d):

            print(
                f"Tile {x}_{y}"
            )

            img = download_tile(
                t,
                d,
                x,
                y
            )

            canvas.paste(
                img,
                (
                    x * TILE_SIZE,
                    y * TILE_SIZE
                )
            )

    return canvas


def save_history(img, t):

    os.makedirs(
        HISTORY_DIR,
        exist_ok=True
    )

    filename = (
        "earth_"
        +
        t.strftime("%Y%m%d_%H%M")
        +
        ".webp"
    )

    path = os.path.join(
        HISTORY_DIR,
        filename
    )

    img.save(
        path,
        "WEBP",
        quality=90,
        method=6
    )

    update_history_json(
        path,
        t
    )


def update_history_json(path, t):

    records = []

    if os.path.exists(HISTORY_JSON):

        try:
            with open(
                HISTORY_JSON,
                "r",
                encoding="utf-8"
            ) as f:
                records = json.load(f)

        except Exception:
            records = []

    records = [
        r for r in records
        if r.get("image") != path
    ]

    records.append(
        {
            "image": path,
            "time": t.isoformat()
        }
    )

    cutoff = (
        datetime.now(timezone.utc)
        -
        timedelta(hours=24)
    )

    clean = []

    for r in records:

        try:
            rt = datetime.fromisoformat(
                r["time"]
            )

            if rt >= cutoff:
                clean.append(r)

            else:
                if os.path.exists(r["image"]):
                    os.remove(r["image"])

        except Exception:
            pass

    clean = clean[-MAX_HISTORY:]

    with open(
        HISTORY_JSON,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            clean,
            f,
            indent=2,
            ensure_ascii=False
        )


def generate_earth():

    d = get_nearest_d(
        TARGET_RESOLUTION
    )

    print(
        "Grid:",
        d,
        "x",
        d
    )

    t = find_latest_time(d)

    if t is None:
        return False

    try:

        img = merge_tiles(
            t,
            d
        )

        if not validate_image(
            img.resize(
                (TILE_SIZE, TILE_SIZE)
            )
        ):
            print(
                "Merged image invalid"
            )
            return False

        os.makedirs(
            "output",
            exist_ok=True
        )

        img.save(
            OUTPUT,
            "WEBP",
            quality=90,
            method=6
        )

        save_history(
            img,
            t
        )

        print(
            "Saved:",
            OUTPUT
        )

        return True

    except Exception as e:

        print(
            "Generate failed:",
            e
        )

        return False
