import threading
import time
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

StateType = TypeVar('StateType')


class Cycle(ABC, Generic[StateType]):
    def __init__(self, time_interval: float):
        self.running = False
        self.lock = threading.Lock()
        self.time_interval = time_interval
        self.killed = False
        self.thread = None

    def start(self, start_state: StateType) -> None:
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._main_loop, args=(start_state,))
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

    def _main_loop(self, start_state: StateType) -> None:
        while True:
            if self.killed:
                return

            if self.running:
                self.evoke(start_state)
                time.sleep(self.time_interval)

    @abstractmethod
    def evoke(self, state: StateType):
        raise NotImplementedError

