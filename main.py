import sys
import time
import curses
from src.backend.speedtest import SpeedTester, SpeedResult
from src.frontend.tui import TUI

def parse_args():
    return "-hideip" in sys.argv
    
def main(stdscr):
    hide_ip = parse_args()
    tui = TUI(stdscr, hide_ip=hide_ip)
    tester = SpeedTester()
    phase = ["idle"]
    status = ["Starting..."]
    result = [SpeedResult()]
    progress = [0.0]
    tick = [0]

    def on_status(msg):
        status[0] = msg
        lowered = msg.lower()
        if "download" in lowered:
            phase[0] = "download"
            progress[0] = 0.0
        elif "upload" in lowered:
            phase[0] = "upload"
            progress[0] = 0.0
        elif "completed" in lowered:
            phase[0] = "done"
        else:
            phase[0] = "searching"

    def on_update(res):
        result[0] = res

    tester.on_status = on_status
    tester.on_update = on_update

    thread = tester.run_threaded()

    while thread.is_alive():
        key = stdscr.getch()
        if key in (ord("q"), ord("Q")):
            tester.cancel()
            break

        tick[0] += 1

        if phase[0] == "download" and result[0].download == 0:
            progress[0] = min(progress[0] + 0.015, 0.95)
        elif phase[0] == "upload" and result[0].upload == 0:
            progress[0] = min(progress[0] + 0.015, 0.95)
        else:
            progress[0] = min(progress[0] + 0.008, 0.95)

        tui.draw_dashboard(status[0], result[0], phase[0], progress[0], tick[0])
        time.sleep(0.1)

    if phase[0] != "done" and (result[0].download > 0 or result[0].upload > 0):
        progress[0] = 1.0
        tui.draw_dashboard(status[0], result[0], phase[0], progress[0], tick[0])
        time.sleep(0.3)

    if result[0].download > 0 or result[0].upload > 0 or result[0].ping > 0:
        tui.draw_results(result[0])
    else:
        tui.draw_dashboard("Cancelled", result[0], "idle", 0, tick[0])
        time.sleep(2)

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        print("\nTest cancelled.")
        sys.exit(0)
