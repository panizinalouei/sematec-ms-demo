from django import template

from lms.utils.jalali import fa_digits, to_jalali

register = template.Library()


@register.filter(name="fa")
def fa(value):
    if value is None:
        return ""
    return fa_digits(value)


@register.filter(name="money")
def money(value):
    try:
        return fa_digits(f"{int(value):,}".replace(",", "٬")) + " تومان"
    except (TypeError, ValueError):
        return value


@register.filter(name="jdate")
def jdate(value, fmt="short"):
    return fa_digits(to_jalali(value, fmt))


@register.filter(name="percent")
def percent(value):
    try:
        return fa_digits(round(float(value))) + "٪"
    except (TypeError, ValueError):
        return "۰٪"


@register.filter(name="hours")
def hours(value):
    return fa_digits(value) + " ساعت"


@register.filter(name="initials")
def initials(obj):
    if hasattr(obj, "initials"):
        return obj.initials
    return "؟"


@register.filter(name="mul")
def mul(value, arg):
    try:
        return round(float(value) * float(arg))
    except (TypeError, ValueError):
        return 0


@register.filter(name="status_badge")
def status_badge(status):
    return {
        "active": "badge-blue", "completed": "badge-green",
        "pending": "badge-gold", "cancelled": "badge-red",
        "submitted": "badge-blue", "graded": "badge-green",
        "late": "badge-gold", "present": "badge-green",
        "absent": "badge-red", "excused": "badge-gray",
    }.get(status, "badge-gray")
