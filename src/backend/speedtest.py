import json
import socket
import time
import threading
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class SpeedResult:
    ping: float = 0.0
    download: float = 0.0
    upload: float = 0.0
    server_name: str = ""
    server_country: str = ""
    client_isp: str = ""
    client_ip: str = ""
    download_progress: float = 0.0
    upload_progress: float = 0.0


PING_HOSTS = ["8.8.8.8", "1.1.1.1", "208.67.222.222"]

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

DOWNLOAD_SOURCES = [
    ("Hetzner Falkenstein (DE)", "https://fsn1-speed.hetzner.com/100MB.bin"),
    ("Hetzner Nuremberg (DE)", "https://nbg1-speed.hetzner.com/100MB.bin"),
    ("Hetzner Helsinki (FI)", "https://hel1-speed.hetzner.com/100MB.bin"),
    ("Hetzner Ashburn (US)", "https://ash-speed.hetzner.com/100MB.bin"),
    ("Hetzner Hillsboro (US)", "https://hil-speed.hetzner.com/100MB.bin"),
    ("OVH Gravelines (FR)", "https://gra.proof.ovh.net/files/100Mb.dat"),
    ("OVH Strasbourg (FR)", "https://sbg.proof.ovh.net/files/100Mb.dat"),
    ("OVH Roubaix (FR)", "https://rbx.proof.ovh.net/files/100Mb.dat"),
    ("OVH Singapore (SG)", "https://sgp.proof.ovh.net/files/100Mb.dat"),
    ("OVH Sydney (AU)", "https://syd.proof.ovh.net/files/100Mb.dat"),
    ("OVH Beauharnois (CA)", "https://bhs.proof.ovh.ca/files/100Mb.dat"),
]

UPLOAD_SOURCES = [
    ("httpbin.org", "https://httpbin.org/post"),
    ("postman-echo.com", "https://postman-echo.com/post"),
    ("httpbingo.org", "https://httpbingo.org/post"),
]

SERVER_LABEL_DOWNLOAD = "Hetzner + OVH (global multi-server)"
SERVER_LABEL_UPLOAD = "httpbin / postman-echo / httpbingo"

DL_STREAMS = 6
UL_STREAMS = 4
WARMUP_SECONDS = 2.0
MEASURE_SECONDS = 8.0
UPLOAD_CHUNK_BYTES = 4_000_000


class SpeedTester:
    def __init__(self):
        self._result = SpeedResult()
        self._lock = threading.Lock()
        self._cancel = False
        self.on_status: Optional[Callable[[str], None]] = None
        self.on_update: Optional[Callable[[SpeedResult], None]] = None

    def _notify(self, msg):
        if self.on_status:
            self.on_status(msg)

    def _snapshot(self) -> SpeedResult:
        with self._lock:
            r = self._result
            return SpeedResult(
                ping=r.ping, download=r.download, upload=r.upload,
                server_name=r.server_name, server_country=r.server_country,
                client_isp=r.client_isp, client_ip=r.client_ip,
                download_progress=r.download_progress,
                upload_progress=r.upload_progress,
            )

    def _update(self):
        if self.on_update:
            self.on_update(self._snapshot())

    def cancel(self):
        self._cancel = True

    def _fetch_ip(self):
        for url in ["https://ifconfig.me/ip", "https://jsonip.com", "https://httpbin.org/ip"]:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                resp = urllib.request.urlopen(req, timeout=4)
                raw = resp.read().decode().strip()
                try:
                    ip = json.loads(raw).get("ip", raw)
                except Exception:
                    ip = raw
                if ip:
                    with self._lock:
                        self._result.client_ip = ip
                    return
            except Exception:
                pass

    def _measure_ping(self) -> float:
        times = []
        for host in PING_HOSTS:
            if self._cancel:
                return 0
            for _ in range(3):
                if self._cancel:
                    return 0
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(2)
                    t0 = time.perf_counter()
                    s.connect((host, 53))
                    ms = (time.perf_counter() - t0) * 1000
                    s.close()
                    times.append(ms)
                except Exception:
                    pass
        if not times:
            return 0
        times.sort()
        return times[len(times) // 2]

    def _download_worker(self, stop_event, counter, counter_lock, start_index):
        sources = DOWNLOAD_SOURCES
        idx = start_index % len(sources)
        while not stop_event.is_set():
            name, url = sources[idx]
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                resp = urllib.request.urlopen(req, timeout=10)
                while not stop_event.is_set():
                    chunk = resp.read(262144)
                    if not chunk:
                        break
                    with counter_lock:
                        counter[0] += len(chunk)
            except Exception:
                if stop_event.is_set():
                    break
                idx = (idx + 1) % len(sources)
                time.sleep(0.2)

    def _upload_worker(self, stop_event, counter, counter_lock, start_index):
        sources = UPLOAD_SOURCES
        idx = start_index % len(sources)
        payload = b"\x00" * UPLOAD_CHUNK_BYTES
        while not stop_event.is_set():
            name, url = sources[idx]
            try:
                req = urllib.request.Request(
                    url, data=payload, method="POST",
                    headers={"User-Agent": UA, "Content-Type": "application/octet-stream"},
                )
                urllib.request.urlopen(req, timeout=15)
                with counter_lock:
                    counter[0] += len(payload)
            except Exception:
                if stop_event.is_set():
                    break
                idx = (idx + 1) % len(sources)
                time.sleep(0.2)

    def _run_phase(self, worker_fn, streams, progress_attr) -> float:
        stop_event = threading.Event()
        counter = [0]
        counter_lock = threading.Lock()

        threads = [
            threading.Thread(target=worker_fn, args=(stop_event, counter, counter_lock, i), daemon=True)
            for i in range(streams)
        ]
        for t in threads:
            t.start()

        total_duration = WARMUP_SECONDS + MEASURE_SECONDS
        start = time.perf_counter()

        while time.perf_counter() - start < WARMUP_SECONDS:
            if self._cancel:
                stop_event.set()
                for t in threads:
                    t.join(timeout=1)
                return 0
            elapsed = time.perf_counter() - start
            with self._lock:
                setattr(self._result, progress_attr, min((elapsed / total_duration) * 0.9, 0.9))
            self._update()
            time.sleep(0.1)

        with counter_lock:
            counter[0] = 0
        measure_start = time.perf_counter()

        while time.perf_counter() - measure_start < MEASURE_SECONDS:
            if self._cancel:
                break
            time.sleep(0.15)
            elapsed_total = (time.perf_counter() - start)
            with self._lock:
                setattr(self._result, progress_attr, min((elapsed_total / total_duration) * 0.9, 0.9))
            self._update()

        measured_elapsed = time.perf_counter() - measure_start
        stop_event.set()
        for t in threads:
            t.join(timeout=2)

        with counter_lock:
            total_bytes = counter[0]

        with self._lock:
            setattr(self._result, progress_attr, 1.0)
        self._update()

        if measured_elapsed <= 0 or total_bytes == 0:
            return 0
        return (total_bytes * 8) / (measured_elapsed * 1_000_000)

    def _measure_download(self) -> float:
        return self._run_phase(self._download_worker, DL_STREAMS, "download_progress")

    def _measure_upload(self) -> float:
        return self._run_phase(self._upload_worker, UL_STREAMS, "upload_progress")

    def run(self) -> SpeedResult:
        self._cancel = False
        with self._lock:
            self._result = SpeedResult(server_name=SERVER_LABEL_DOWNLOAD)

        self._notify("Fetching IP...")
        self._fetch_ip()
        self._update()

        if self._cancel:
            return self._snapshot()

        self._notify("Measuring ping...")
        ping = self._measure_ping()
        with self._lock:
            self._result.ping = ping
        self._update()

        if self._cancel:
            return self._snapshot()

        self._notify("Measuring download...")
        dl = self._measure_download()
        with self._lock:
            self._result.download = dl
            self._result.download_progress = 1.0
        self._update()

        if self._cancel:
            return self._snapshot()

        self._notify("Measuring upload...")
        with self._lock:
            self._result.server_name = SERVER_LABEL_UPLOAD
        ul = self._measure_upload()
        with self._lock:
            self._result.upload = ul
            self._result.upload_progress = 1.0
        self._update()

        self._notify("Test completed")
        return self._snapshot()

    def run_threaded(self, callback=None):
        self.on_update = callback or self.on_update
        t = threading.Thread(target=self.run, daemon=True)
        t.start()
        return t
