# Pytter

A terminal-based internet speed test with a live TUI dashboard — measures ping, download, and upload throughput using multiple parallel connections against globally distributed servers.

![status](https://img.shields.io/badge/status-active-brightgreen) ![python](https://img.shields.io/badge/python-3.8%2B-blue)

## Features

- **Live dashboard** — animated ping/download/upload readout rendered with `curses`, updated in real time.
- **Accurate high-speed measurement** — uses parallel TCP streams and a duration-based measurement window (not a single-file timer), so results stay accurate on fast connections (100+ Mbps) instead of being skewed by TCP slow-start and connection setup overhead.
- **Global, provider-agnostic servers** — download traffic is spread across Hetzner and OVH endpoints in Europe, North America, Asia, and Oceania; upload traffic rotates across multiple independent echo services. If one provider throttles or blocks a request, the affected connection automatically rotates to the next server — no manual configuration required.
- **No external dependencies** — built entirely on the Python standard library (except on Windows, see below).
- **Cancelable at any time** — press `q` to stop a running test early.
- **Optional IP privacy** — hide your public IP from the display with a single flag.

## Requirements

- Python 3.8 or newer
- **Linux / macOS:** no extra packages needed — `curses` ships with the standard library.
- **Windows:** the standard library does not include `curses`. Install:

  ```bash
  pip install windows-curses
  ```

## Installation

```bash
git clone <repository-url>
cd pytter
```

No further setup is required — there is no `requirements.txt` because the project has no third-party dependencies (aside from `windows-curses` on Windows).

## Usage

Run the test:

```bash
python3 main.py
```

Hide your IP address from the results screen:

```bash
python3 main.py -hideip
```

**Controls**

| Key       | Action                    |
|-----------|---------------------------|
| `q` / `Q` | Cancel the running test   |
| `Ctrl+C`  | Force-quit immediately    |
| any key   | Dismiss the results screen|

## How the measurement works

Naively timing a single download of a small file produces misleading results on fast connections: most of the elapsed time is spent in TCP connection setup and slow-start rather than steady-state transfer. Pytter avoids this the same way tools like fast.com and speedtest.net do:

1. **Parallel streams** — several TCP connections run concurrently (6 for download, 4 for upload) instead of one.
2. **Warm-up phase** — the first ~2 seconds of traffic are discarded so TCP windows have time to ramp up.
3. **Fixed measurement window** — bytes transferred across all streams are summed over a steady ~8 second window.
4. **Throughput** = total bytes transferred × 8 ÷ measured elapsed time.

### Servers used

| Phase    | Providers                                                                 |
|----------|----------------------------------------------------------------------------|
| Download | Hetzner (Falkenstein, Nuremberg, Helsinki, Ashburn, Hillsboro), OVH (Gravelines, Strasbourg, Roubaix, Singapore, Sydney, Beauharnois) |
| Upload   | httpbin.org, postman-echo.com, httpbingo.org                              |
| Ping     | Public DNS resolvers (Google, Cloudflare, OpenDNS) via TCP handshake timing |

Each worker thread iterates over its provider list independently; if a request to one server fails, that thread moves on to the next entry without interrupting the rest of the test.

## Project structure

```
.
├── main.py                    # Entry point, curses event loop
└── src/
    ├── backend/
    │   └── speedtest.py       # SpeedTester: ping/download/upload measurement
    └── frontend/
        ├── ascii_art.py       # Logo, progress bars, ping labels
        └── tui.py             # TUI: dashboard and results rendering
```

## License

MIT
