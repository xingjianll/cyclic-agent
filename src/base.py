import threading
import time
from abc import ABC


class Cycle(ABC):
    def __init__(self, time_interval: int):
        self.running = False
        self.lock = threading.Lock()
        self.time_interval = time_interval
        self.killed = False

    def start(self):
        if not self.running:
            self.running = True
            threading.Thread(target=self._main_loop_stub).start()

    def pause(self):
        with self.lock:
            self.running = False

    def resume(self):
        with self.lock:
            self.running = True

    def _main_loop_stub(self):
        while True:
            if self.killed:
                return

            if self.running:
                self.evoke()
                time.sleep(self.time_interval)

    def evoke(self):
        ...


if __name__ == "__main__":
    cycle = Cycle(1)
    cycle.start()
    time.sleep(5)
    cycle.pause()