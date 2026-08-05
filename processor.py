from PIL import (
    Image,
    ImageEnhance,
    ImageFilter,
    ImageChops,
    ImageOps
)
import os


INPUT = "output/earth.webp"

PHONE_OUTPUT = "output/earth_phone.webp"
DESKTOP_OUTPUT = "output/earth_desktop.webp"


# ======================
# 输出尺寸
# ======================

PHONE_WIDTH = 1080
PHONE_HEIGHT = 2400

DESKTOP_WIDTH = 2560
DESKTOP_HEIGHT = 1440


# ======================
# 构图参数
# ======================

# 手机版：地球相对小一些，适合竖屏
PHONE_EARTH_MAX_WIDTH_RATIO = 0.66
PHONE_EARTH_MAX_HEIGHT_RATIO = 0.33
PHONE_EARTH_CENTER_X_RATIO = 0.50
PHONE_EARTH_CENTER_Y_RATIO = 0.55

# 桌面版：地球稍大一点，适合横屏
DESKTOP_EARTH_MAX_WIDTH_RATIO = 0.42
DESKTOP_EARTH_MAX_HEIGHT_RATIO = 0.75
DESKTOP_EARTH_CENTER_X_RATIO = 0.50
DESKTOP_EARTH_CENTER_Y_RATIO = 0.53


# ======================
# 轻度增强参数
# ======================

GLOBAL_CONTRAST = 1.05
GLOBAL_COLOR = 1.05
GLOBAL_SHARPNESS = 1.08

EARTH_THRESHOLD = 6


# ======================
# 增强
# ======================

def enhance(img):
    img = ImageEnhance.Contrast(img).enhance(GLOBAL_CONTRAST)
    img = ImageEnhance.Color(img).enhance(GLOBAL_COLOR)
    img = ImageEnhance.Sharpness(img).enhance(GLOBAL_SHARPNESS)

    gray = img.convert("L")

    earth_mask = gray.point(lambda p: 255 if p > EARTH_THRESHOLD else 0)
    earth_mask = earth_mask.filter(ImageFilter.GaussianBlur(15))

    bright = ImageEnhance.Brightness(img).enhance(1.04)
    dark = ImageEnhance.Brightness(img).enhance(0.88)

    night = ImageOps.invert(gray)
    night = night.point(lambda p: 255 if p > 80 else 0)
    night = ImageChops.multiply(night, earth_mask)

    return Image.composite(dark, bright, night)


# ======================
# 缩放
# ======================

def resize_for_canvas(img, canvas_width, canvas_height,
                      max_width_ratio, max_height_ratio):
    max_w = int(canvas_width * max_width_ratio)
    max_h = int(canvas_height * max_height_ratio)

    scale = min(max_w / img.width, max_h / img.height)

    new_size = (
        int(img.width * scale),
        int(img.height * scale)
    )

    return img.resize(new_size, Image.Resampling.LANCZOS)


# ======================
# 贴到画布
# ======================

def place_on_canvas(img, canvas_width, canvas_height,
                    center_x_ratio, center_y_ratio):
    canvas = Image.new("RGB", (canvas_width, canvas_height), (0, 0, 0))

    x = int(canvas_width * center_x_ratio - img.width / 2)
    y = int(canvas_height * center_y_ratio - img.height / 2)

    canvas.paste(img, (x, y))
    return canvas


# ======================
# 手机版
# ======================

def make_phone_wallpaper(img):
    scaled = resize_for_canvas(
        img,
        PHONE_WIDTH,
        PHONE_HEIGHT,
        PHONE_EARTH_MAX_WIDTH_RATIO,
        PHONE_EARTH_MAX_HEIGHT_RATIO
    )

    result = place_on_canvas(
        scaled,
        PHONE_WIDTH,
        PHONE_HEIGHT,
        PHONE_EARTH_CENTER_X_RATIO,
        PHONE_EARTH_CENTER_Y_RATIO
    )

    result.save(
        PHONE_OUTPUT,
        "WEBP",
        quality=92,
        method=6
    )

    print("Saved:", PHONE_OUTPUT)


# ======================
# 桌面版
# ======================

def make_desktop_wallpaper(img):
    scaled = resize_for_canvas(
        img,
        DESKTOP_WIDTH,
        DESKTOP_HEIGHT,
        DESKTOP_EARTH_MAX_WIDTH_RATIO,
        DESKTOP_EARTH_MAX_HEIGHT_RATIO
    )

    result = place_on_canvas(
        scaled,
        DESKTOP_WIDTH,
        DESKTOP_HEIGHT,
        DESKTOP_EARTH_CENTER_X_RATIO,
        DESKTOP_EARTH_CENTER_Y_RATIO
    )

    result.save(
        DESKTOP_OUTPUT,
        "WEBP",
        quality=92,
        method=6
    )

    print("Saved:", DESKTOP_OUTPUT)


# ======================
# 总处理入口
# ======================

def process_outputs():
    if not os.path.exists(INPUT):
        raise FileNotFoundError(f"Input file not found: {INPUT}")

    img = Image.open(INPUT).convert("RGB")
    img = enhance(img)

    make_phone_wallpaper(img)
    make_desktop_wallpaper(img)