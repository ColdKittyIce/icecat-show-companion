"""
network.py — IceCat Show Companion v3.0
NetworkMonitor  : polls TCP connection to stream host
DiscordWebhook  : fires go-live notifications
"""

import socket, threading, time, logging, requests
log = logging.getLogger("icecat.net")


class NetworkMonitor:
    """Polls the stream host every 5 s to detect live status."""

    POLL_INTERVAL = 5.0

    def __init__(self, host: str, port: int):
        self.host      = host
        self.port      = port
        self._connected = False
        self._running   = False
        self._thread    = None
        self._callback  = None   # called with (bool) on state change

    def start(self, on_change=None):
        self._callback = on_change
        self._running  = True
        self._thread   = threading.Thread(
            target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    @property
    def connected(self) -> bool:
        return self._connected

    def _loop(self):
        prev = False
        while self._running:
            cur = self._check()
            if cur != prev:
                self._connected = cur
                prev = cur
                if self._callback:
                    try:
                        self._callback(cur)
                    except Exception:
                        pass
            time.sleep(self.POLL_INTERVAL)

    def _check(self) -> bool:
        try:
            with socket.create_connection(
                    (self.host, self.port), timeout=3.0):
                return True
        except Exception:
            return False


class DiscordWebhook:
    """Sends a simple POST notification to a Discord webhook URL."""

    def fire(self, url: str, message: str, prankcast_url: str = ""):
        if not url:
            return
        text = message.replace("{url}", prankcast_url)
        threading.Thread(
            target=self._send, args=(url, text), daemon=True).start()

    def _send(self, url: str, text: str):
        try:
            requests.post(url, json={"content": text}, timeout=8)
            log.info("Discord webhook fired")
        except Exception as e:
            log.warning(f"Discord webhook error: {e}")
