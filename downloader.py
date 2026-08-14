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

# HTTP 请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# 单个瓦片下载重试次数
TILE_RETRIES = 3

# NICT 的 No Image 占位图通常为：
# 黑色背景 + 中央一小块灰色 “No Image” 文本。
# 下面参数用于识别这种占位图，而不是简单判断“是否为纯黑图”。
NO_IMAGE_PIXEL_THRESHOLD = 10
NO_IMAGE_MAX_BRIGHT_RATIO = 0.08
NO_IMAGE_MAX_BBOX_WIDTH_RATIO = 0.60
NO_IMAGE_MAX_BBOX_HEIGHT_RATIO = 0.25
NO_IMAGE_CENTER_TOLERANCE_X = 0.20
NO_IMAGE_CENTER_TOLERANCE_Y = 0.20


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
# No Image 占位图检测
# =========================

def is_no_image(img):

    """
    检测 NICT 返回的 “No Image” 占位图。

    旧方法 img.getbbox() is None 只能检测纯黑图。
    NICT 的占位图虽然背景接近黑色，但中央存在灰色文字，
    因此 getbbox() 并不会返回 None。

    当前方法判断：
    1. 图像是否几乎全黑；
    2. 非黑像素是否只集中在中央的一小块区域。

    这样可以识别 “黑底 + 中央 No Image 文本”，同时尽量避免
    把正常的太空背景或地球边缘瓦片误判为缺图。
    """

    if img.mode != "RGB":
        img = img.convert("RGB")

    gray = img.convert("L")

    # 将亮度高于阈值的像素视为“有效非黑像素”
    mask = gray.point(
        lambda p: 255 if p > NO_IMAGE_PIXEL_THRESHOLD else 0
    )

    bbox = mask.getbbox()

    # 完全没有非黑像素：肯定不是有效卫星图
    if bbox is None:
        return True

    width, height = gray.size
    x0, y0, x1, y1 = bbox

    bbox_width = x1 - x0
    bbox_height = y1 - y0

    # 统计非黑像素比例
    histogram = mask.histogram()
    bright_pixels = histogram[255]
    total_pixels = width * height
    bright_ratio = bright_pixels / total_pixels

    # “No Image” 文字应当只占整张 tile 很小一部分
    if bright_ratio > NO_IMAGE_MAX_BRIGHT_RATIO:
        return False

    # 非黑区域如果太大，更像正常卫星图，而不是中央提示文字
    if bbox_width > width * NO_IMAGE_MAX_BBOX_WIDTH_RATIO:
        return False

    if bbox_height > height * NO_IMAGE_MAX_BBOX_HEIGHT_RATIO:
        return False

    # 判断这块小区域是否位于 tile 中央附近
    bbox_center_x = (x0 + x1) / 2
    bbox_center_y = (y0 + y1) / 2

    image_center_x = width / 2
    image_center_y = height / 2

    centered_x = (
        abs(bbox_center_x - image_center_x)
        <= width * NO_IMAGE_CENTER_TOLERANCE_X
    )

    centered_y = (
        abs(bbox_center_y - image_center_y)
        <= height * NO_IMAGE_CENTER_TOLERANCE_Y
    )

    return centered_x and centered_y


# =========================
# 时间候选
# =========================

def get_time_candidates():

    now = datetime.now(timezone.utc)

    result = []
    seen = set()

    # 从约20分钟前开始向前搜索。
    # 如果最近一帧尚未发布，会自动继续尝试30、40分钟以前的帧。
    for offset in range(20, 240, 10):

        t = now - timedelta(minutes=offset)

        t = t.replace(
            minute=(t.minute // 10) * 10,
            second=0,
            microsecond=0
        )

        # 防止因为取整产生重复时间
        if t not in seen:
            seen.add(t)
            result.append(t)

    return result


# =========================
# 检查时间
# =========================

def check_time(t):

    """
    用 1d/550 的完整圆盘缩略图检查这个观测时间是否真的有图。

    不能只判断 HTTP 200：
    NICT 在没有有效图像时也可能返回 HTTP 200，
    内容却是 “No Image” 占位图。
    """

    url = build_url(
        t,
        1,
        0,
        0
    )

    try:

        r = requests.get(
            url,
            timeout=(5, 15),
            headers=HEADERS
        )

        if r.status_code != 200:

            print(
                "Unavailable:",
                t.strftime("%Y-%m-%d %H:%M"),
                "HTTP",
                r.status_code
            )

            return False

        img = Image.open(
            BytesIO(r.content)
        ).convert("RGB")

        if is_no_image(img):

            print(
                "No Image placeholder:",
                t.strftime("%Y-%m-%d %H:%M")
            )

            return False

        return True

    except Exception as e:

        print(
            "Check failed:",
            t.strftime("%Y-%m-%d %H:%M"),
            e
        )

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

def download_tile(t, d, x, y):

    url = build_url(
        t,
        d,
        x,
        y
    )

    last_error = None

    for i in range(TILE_RETRIES):

        try:

            r = requests.get(
                url,
                timeout=(10, 30),
                headers=HEADERS
            )

            if r.status_code != 200:

                raise Exception(
                    f"HTTP {r.status_code}"
                )

            img = Image.open(
                BytesIO(r.content)
            ).convert("RGB")

            # 不对单个高分辨率 tile 使用 is_no_image()。
            # 4d 边角 tile 本身可能大部分都是黑色太空背景，
            # 启发式检测会把正常的 3_3 等边角瓦片误判为 No Image。
            # 这里只确保图像可以被 PIL 正常解码。
            img.load()

            return img

        except Exception as e:

            last_error = e

            print(
                "Retry:",
                i + 1,
                f"tile={x}_{y}",
                e
            )

            if i < TILE_RETRIES - 1:
                time.sleep(2)

    raise Exception(
        "Download failed "
        + url
        + " | "
        + str(last_error)
    )


# =========================
# 拼接
# =========================

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


# =========================
# 保存历史
# =========================

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

    item = {
        "image": path,
        "time": t.isoformat()
    }

    records = [
        r for r in records
        if r.get("image") != path
    ]

    records.append(item)

    # 时间排序
    records.sort(
        key=lambda x: x["time"]
    )

    # =====================
    # 删除24小时前文件
    # =====================

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

                old = r["image"]

                if os.path.exists(old):

                    os.remove(old)

                    print(
                        "Removed:",
                        old
                    )

        except Exception:

            pass

    records = clean

    # 最后保险限制
    records = records[-MAX_HISTORY:]

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

    d = get_nearest_d(
        TARGET_RESOLUTION
    )

    print(
        "Grid:",
        d,
        "x",
        d
    )

    t = find_latest_time()

    if t is None:

        return False

    print(
        "Satellite:",
        t
    )

    try:

        img = merge_tiles(
            t,
            d
        )

    except Exception as e:

        # check_time 已经排除了整张 No Image，
        # 这里再防止高分辨率某个单独 tile 缺失。
        # 只要拼接不完整，就绝不覆盖 output，也不写入 history。
        print(
            "Satellite frame incomplete:",
            e
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

    print(
        "Saved:",
        OUTPUT
    )

    save_history(
        img,
        t
    )

    return True
