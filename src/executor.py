import threading
import time

from src.state import State


class CyclicExecutor:
    def __init__(self, default_time_interval: float):
        self.running = False
        self.lock = threading.Lock()
        self.default_time_interval = default_time_interval
        self.killed = False
        self.thread = None

    def start(self, initial_state: State) -> None:
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._main_loop, args=(initial_state,))
            self.thread.start()

    def pause(self):
        with self.lock:
            self.running = False

    def resume(self):
        with self.lock:
            self.running = True

    def kill(self):
        with self.lock:
            self.killed = True
            self.running = False
        if self.thread:
            self.thread.join()

    def _main_loop(self, state: State) -> None:
        while True:
            if self.killed:
                return

            if self.running:
                state = state.run()
                time.sleep(self.time_interval)


class Timer:
    ...
