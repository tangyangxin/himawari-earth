import os
import time
import requests

from datetime import datetime, timedelta, timezone
from io import BytesIO
from PIL import Image


# =========================
# 配置
# =========================

TARGET_RESOLUTION = 2160
TILE_SIZE = 550

BASE_URL = (
    "https://himawari8-dl.nict.go.jp/"
    "himawari8/img/D531106/"
)

OUTPUT = "output/earth.webp"


# =========================
# 分辨率选择
# =========================

def get_nearest_d(resolution):
    levels = [1, 2, 4, 8, 16, 20]
    return min(levels, key=lambda d: abs(d * TILE_SIZE - resolution))


# =========================
# 构造 URL
# =========================

def build_url(t, d, x, y):

    date = t.strftime("%Y/%m/%d")
    timestamp = t.strftime("%H%M%S")

    return (
        BASE_URL
        + f"{d}d/550/"
        + f"{date}/"
        + f"{timestamp}_{x}_{y}.png"
    )


# =========================
# 查找候选时间
# =========================

def get_time_candidates():

    now = datetime.now(timezone.utc)

    result = []

    # 最大搜索4小时前
    for offset in range(40, 240, 10):

        t = now - timedelta(minutes=offset)

        t = t.replace(
            minute=(t.minute // 10) * 10,
            second=0,
            microsecond=0
        )

        result.append(t)

    return result



# =========================
# 检查时间是否有效
# =========================

def check_time(t):

    url = build_url(t, 1, 0, 0)

    try:

        r = requests.get(
            url,
            timeout=(5, 15),
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        return r.status_code == 200


    except Exception:

        return False



# =========================
# 找最新卫星图
# =========================

def find_latest_time():

    print("Searching satellite time...")


    for t in get_time_candidates():

        print(
            "Try:",
            t.strftime("%Y-%m-%d %H:%M")
        )


        if check_time(t):

            print("Found:", t)

            return t



    print(
        "No available satellite image found"
    )

    return None



# =========================
# 下载瓦片
# =========================

def download_tile(t, d, x, y):

    url = build_url(t, d, x, y)


    for i in range(3):

        try:

            r = requests.get(
                url,
                timeout=(10,30),
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            )


            if r.status_code == 200:

                return Image.open(
                    BytesIO(r.content)
                ).convert("RGB")



            print(
                "HTTP",
                r.status_code,
                url
            )


        except Exception as e:

            print(
                "Retry:",
                i+1,
                e
            )


        time.sleep(2)



    raise Exception(
        "Download failed:\n" + url
    )



# =========================
# 拼接
# =========================

def merge_tiles(t,d):

    size = d*TILE_SIZE


    canvas = Image.new(
        "RGB",
        (size,size)
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
                    x*TILE_SIZE,
                    y*TILE_SIZE
                )
            )


    return canvas



# =========================
# 生成原图
# =========================

def generate_earth():

    d = get_nearest_d(
        TARGET_RESOLUTION
    )


    print(
        "Using grid:",
        d,
        "x",
        d
    )


    t = find_latest_time()


    # 没有卫星图
    if t is None:

        return False



    print(
        "Satellite time:",
        t
    )


    img = merge_tiles(
        t,
        d
    )


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


    print(
        "Saved:",
        OUTPUT
    )


    return True
