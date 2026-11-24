"""تاریخ شمسی و اعداد فارسی"""
from datetime import date, datetime

MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
          "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
WEEKDAYS = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]


def g2j(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2, gm2, gd2 = gy - 1600, gm - 1, gd - 1
    g_day = 365 * gy2 + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400
    g_day += g_d_m[gm2] + gd2
    if gm > 2 and ((gy % 4 == 0 and gy % 100 != 0) or gy % 400 == 0):
        g_day += 1
    j_day = g_day - 79
    j_np = j_day // 12053
    j_day %= 12053
    jy = 979 + 33 * j_np + 4 * (j_day // 1461)
    j_day %= 1461
    if j_day >= 366:
        jy += (j_day - 1) // 365
        j_day = (j_day - 1) % 365
    jm = 12
    for i in range(11):
        mdays = 31 if i < 6 else 30
        if j_day < mdays:
            jm = i + 1
            break
        j_day -= mdays
    return jy, jm, j_day + 1


def to_jalali(value, fmt: str = "short") -> str:
    if not value:
        return "—"
    if isinstance(value, datetime):
        value = value.date()
    if not isinstance(value, date):
        return str(value)
    jy, jm, jd = g2j(value.year, value.month, value.day)
    if fmt == "long":
        return f"{jd} {MONTHS[jm - 1]} {jy}"
    if fmt == "full":
        return f"{WEEKDAYS[value.weekday()]} {jd} {MONTHS[jm - 1]} {jy}"
    return f"{jy}/{jm:02d}/{jd:02d}"


def jalali_month(value) -> str:
    if isinstance(value, datetime):
        value = value.date()
    jy, jm, _ = g2j(value.year, value.month, value.day)
    return f"{MONTHS[jm - 1]}"


def fa_digits(value) -> str:
    return str(value).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
