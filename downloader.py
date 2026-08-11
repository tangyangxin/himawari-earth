import os
import time
import json
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

HISTORY_DIR = "history"
HISTORY_JSON = "history.json"

# 最大保险数量
# 实际按24小时删除
MAX_HISTORY = 200



# =========================
# 分辨率
# =========================

def get_nearest_d(resolution):

    levels = [1, 2, 4, 8, 16, 20]

    return min(
        levels,
        key=lambda d: abs(d * TILE_SIZE - resolution)
    )



# =========================
# URL
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
# 时间候选
# =========================

def get_time_candidates():

    now = datetime.now(timezone.utc)

    result = []


    for offset in range(40,240,10):

        t = now - timedelta(minutes=offset)

        t = t.replace(
            minute=(t.minute//10)*10,
            second=0,
            microsecond=0
        )

        result.append(t)


    return result



# =========================
# 检查时间
# =========================

def check_time(t):

    url = build_url(
        t,
        1,
        0,
        0
    )

    try:

        r=requests.get(
            url,
            timeout=(5,15),
            headers={
                "User-Agent":"Mozilla/5.0"
            }
        )


        return r.status_code == 200


    except Exception:

        return False



# =========================
# 查找最新帧
# =========================

def find_latest_time():

    print(
        "Searching satellite time..."
    )


    for t in get_time_candidates():

        print(
            "Try:",
            t.strftime("%Y-%m-%d %H:%M")
        )


        if check_time(t):

            print(
                "Found:",
                t
            )

            return t



    print(
        "No satellite image"
    )

    return None



# =========================
# 下载瓦片
# =========================

def download_tile(t,d,x,y):

    url = build_url(
        t,
        d,
        x,
        y
    )


    for i in range(3):

        try:

            r=requests.get(
                url,
                timeout=(10,30),
                headers={
                    "User-Agent":"Mozilla/5.0"
                }
            )


            if r.status_code==200:
                
                img = Image.open(
                    BytesIO(r.content)
                ).convert("RGB")

                # 防止NICT返回No Image占位图
                if img.getbbox() is None:
                    raise Exception("Empty tile")

                return img

        except Exception as e:

            print(
                "Retry:",
                i+1,
                e
            )


        time.sleep(2)



    raise Exception(
        "Download failed "
        + url
    )



# =========================
# 拼接
# =========================

def merge_tiles(t,d):

    size=d*TILE_SIZE


    canvas=Image.new(
        "RGB",
        (size,size)
    )


    for y in range(d):

        for x in range(d):

            print(
                f"Tile {x}_{y}"
            )


            img=download_tile(
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
# 保存历史
# =========================

def save_history(img,t):

    os.makedirs(
        HISTORY_DIR,
        exist_ok=True
    )


    filename=(
        "earth_"
        +
        t.strftime("%Y%m%d_%H%M")
        +
        ".webp"
    )


    path=os.path.join(
        HISTORY_DIR,
        filename
    )


    # 防止重复帧

    if os.path.exists(path):

        print(
            "Already exists:",
            path
        )

        return



    img.save(
        path,
        "WEBP",
        quality=90,
        method=6
    )


    print(
        "Saved history:",
        path
    )


    update_history_json(
        path,
        t
    )



# =========================
# history管理
# =========================

def update_history_json(path,t):

    records=[]


    if os.path.exists(HISTORY_JSON):

        try:

            with open(
                HISTORY_JSON,
                "r",
                encoding="utf-8"
            ) as f:

                records=json.load(f)


        except Exception:

            records=[]



    item={

        "image":path,

        "time":t.isoformat()

    }



    records=[
        r for r in records
        if r.get("image") != path
    ]


    records.append(item)



    # 时间排序

    records.sort(
        key=lambda x:x["time"]
    )



    # =====================
    # 删除24小时前文件
    # =====================

    cutoff=(
        datetime.now(timezone.utc)
        -
        timedelta(hours=24)
    )


    clean=[]


    for r in records:

        try:

            rt=datetime.fromisoformat(
                r["time"]
            )


            if rt >= cutoff:

                clean.append(r)


            else:

                old=r["image"]


                if os.path.exists(old):

                    os.remove(old)

                    print(
                        "Removed:",
                        old
                    )


        except Exception:

            pass



    records=clean



    # 最后保险限制

    records=records[-MAX_HISTORY:]



    with open(
        HISTORY_JSON,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            records,
            f,
            indent=2,
            ensure_ascii=False
        )


    print(
        "history frames:",
        len(records)
    )



# =========================
# 主流程
# =========================

def generate_earth():

    d=get_nearest_d(
        TARGET_RESOLUTION
    )


    print(
        "Grid:",
        d,
        "x",
        d
    )



    t=find_latest_time()


    if t is None:

        return False



    print(
        "Satellite:",
        t
    )



    img=merge_tiles(
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



    save_history(
        img,
        t
    )


    return True
