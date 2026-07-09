LOGO = [
    "______  __    __  _________  _________  _______   _______ ",
    "|   _  \\|  |  |  ||___   ___||___   ___||   ____| |   _  \\",
    "|  |_)  |  |__|  |    |  |       |  |   |  |__    |  |_)  |",
    "|   ___/ \\____   |    |  |       |  |   |   __|   |      / ",
    "|  |          |  |    |  |       |  |   |  |____  |  |\\  \\ ",
    "|__|          |__|    |__|       |__|   |_______| |__| \\__\\",
]


def speed_bar(speed, max_speed=100.0, width=30):
    if speed > max_speed:
        max_speed = speed * 1.15
    if max_speed <= 0:
        max_speed = 100
    filled = int((speed / max_speed) * width)
    filled = min(filled, width)
    empty = width - filled
    return "#" * filled + "." * empty


def progress_bar(progress, width=30):
    filled = int(progress * width)
    empty = width - filled
    return "#" * filled + "." * empty


def ping_label(ping):
    if ping < 20:
        return "EXCELLENT"
    elif ping < 50:
        return "GOOD"
    elif ping < 100:
        return "FAIR"
    else:
        return "SLOW"
