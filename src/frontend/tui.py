import curses

from src.backend.speedtest import SpeedResult
from src.frontend.ascii_art import LOGO, speed_bar, progress_bar, ping_label


SPIN = ["|", "/", "-", "\\"]


class TUI:
    def __init__(self, stdscr, hide_ip=False):
        self.stdscr = stdscr
        self.hide_ip = hide_ip
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_RED, -1)
        curses.init_pair(5, curses.COLOR_WHITE, -1)
        curses.init_pair(6, curses.COLOR_MAGENTA, -1)
        curses.init_pair(7, curses.COLOR_BLUE, -1)
        self.stdscr.nodelay(True)
        self.stdscr.timeout(100)

    def _addstr(self, y, x, text, attr=0):
        h, w = self.stdscr.getmaxyx()
        if 0 <= y < h:
            text = text[:max(0, w - x)]
            try:
                self.stdscr.addstr(y, max(0, x), text, attr)
            except curses.error:
                pass

    def _cx(self, text):
        _, w = self.stdscr.getmaxyx()
        return max(0, (w - len(text)) // 2)

    def draw_logo(self, start_y=1):
        y = start_y
        for line in LOGO:
            self._addstr(y, self._cx(line), line, curses.color_pair(1) | curses.A_BOLD)
            y += 1
        return y

    def draw_dashboard(self, status, result, phase, progress, tick=0):
        h, w = self.stdscr.getmaxyx()
        self.stdscr.erase()

        y = self.draw_logo()
        y += 1

        spin = SPIN[tick % len(SPIN)] if phase != "done" else "*"
        self._addstr(y, 4, spin, curses.color_pair(3) | curses.A_BOLD)
        self._addstr(y, 7, status, curses.color_pair(5))
        if not self.hide_ip and result.client_ip:
            ip_text = f"[{result.client_ip}]"
            self._addstr(y, w - len(ip_text) - 4, ip_text, curses.color_pair(5) | curses.A_DIM)
        y += 2

        self._addstr(y, 4, "-" * (w - 8), curses.color_pair(7))
        y += 1

        self._addstr(y, 4, "PING", curses.color_pair(1) | curses.A_BOLD)
        if result.ping > 0:
            lbl = ping_label(result.ping)
            c = curses.COLOR_GREEN if result.ping < 50 else (curses.COLOR_YELLOW if result.ping < 100 else curses.COLOR_RED)
            ms_text = f"{result.ping:.1f} ms"
            self._addstr(y, w - len(ms_text) - 4, ms_text, curses.color_pair(c) | curses.A_BOLD)
            self._addstr(y + 1, 4, f"  [{lbl}]", curses.color_pair(c))
        else:
            self._addstr(y, w - 10, "--- ms", curses.color_pair(5))
            if phase in ("idle", "searching"):
                self._addstr(y + 1, 4, f"  {SPIN[tick % len(SPIN)]} measuring...", curses.color_pair(3))
        y += 3

        self._addstr(y, 4, "DOWNLOAD", curses.color_pair(1) | curses.A_BOLD)
        if result.download > 0:
            bar = speed_bar(result.download)
            self._addstr(y + 1, 4, f"[{bar}]", curses.color_pair(2))
            speed_text = f"{result.download:.2f} Mbps"
            self._addstr(y + 1, w - len(speed_text) - 4, speed_text, curses.color_pair(2) | curses.A_BOLD)
        elif phase == "download":
            bar = progress_bar(progress)
            self._addstr(y + 1, 4, f"[{bar}]", curses.color_pair(3))
            self._addstr(y + 1, w - 14, "measuring...", curses.color_pair(3))
        else:
            self._addstr(y + 1, 4, "[..............................]", curses.color_pair(5))
            self._addstr(y + 1, w - 12, "--- Mbps", curses.color_pair(5))
        y += 3

        self._addstr(y, 4, "UPLOAD  ", curses.color_pair(1) | curses.A_BOLD)
        if result.upload > 0:
            bar = speed_bar(result.upload)
            self._addstr(y + 1, 4, f"[{bar}]", curses.color_pair(2))
            speed_text = f"{result.upload:.2f} Mbps"
            self._addstr(y + 1, w - len(speed_text) - 4, speed_text, curses.color_pair(2) | curses.A_BOLD)
        elif phase == "upload":
            bar = progress_bar(progress)
            self._addstr(y + 1, 4, f"[{bar}]", curses.color_pair(3))
            self._addstr(y + 1, w - 14, "measuring...", curses.color_pair(3))
        else:
            self._addstr(y + 1, 4, "[..............................]", curses.color_pair(5))
            self._addstr(y + 1, w - 12, "--- Mbps", curses.color_pair(5))
        y += 3

        self._addstr(y, 4, "-" * (w - 8), curses.color_pair(7))
        y += 1

        if result.server_name:
            self._addstr(y, 4, "Server:", curses.color_pair(5) | curses.A_DIM)
            self._addstr(y, 13, result.server_name, curses.color_pair(5))
            y += 1

        footer = "q: quit  |  Ctrl+C: cancel"
        self._addstr(h - 1, self._cx(footer), footer, curses.color_pair(5) | curses.A_DIM)

        self.stdscr.refresh()

    def draw_results(self, result):
        h, w = self.stdscr.getmaxyx()
        self.stdscr.erase()

        y = self.draw_logo()
        y += 1

        title = "============ RESULTS ============"
        self._addstr(y, self._cx(title), title, curses.color_pair(2) | curses.A_BOLD)
        y += 2

        x1, x2 = 6, w - 6
        if x2 - x1 < 30:
            x1, x2 = 2, w - 2

        self._addstr(y, x1, "+" + "-" * (x2 - x1 - 2) + "+", curses.color_pair(2))
        y += 1

        def row(label, value, val_color=curses.color_pair(2)):
            inner_w = x2 - x1 - 2
            line = f"{label}: {value}"
            self._addstr(y, x1, "|" + line.ljust(inner_w) + "|", curses.color_pair(2))
            self._addstr(y, x1 + 1, f"{label}:", curses.color_pair(1) | curses.A_BOLD)
            val_x = x1 + 1 + len(label) + 2
            self._addstr(y, val_x, value, val_color | curses.A_BOLD)
            return y + 1

        y = row("Ping      ", f"{result.ping:.1f} ms [{ping_label(result.ping)}]")
        y = row("Download  ", f"{result.download:.2f} Mbps")
        y = row("Upload    ", f"{result.upload:.2f} Mbps")
        if result.server_name:
            y = row("Server    ", result.server_name)
        if not self.hide_ip and result.client_ip:
            y = row("IP        ", result.client_ip)

        self._addstr(y, x1, "+" + "-" * (x2 - x1 - 2) + "+", curses.color_pair(2))
        y += 2

        footer = "Press any key to exit"
        self._addstr(h - 1, self._cx(footer), footer, curses.color_pair(5) | curses.A_DIM)

        self.stdscr.refresh()

        self.stdscr.nodelay(False)
        self.stdscr.timeout(-1)
        self.stdscr.getch()
