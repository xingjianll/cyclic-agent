from datetime import datetime


class Fifo:
    def __init__(self):
        self.capacity = 100
        self.queue = []

    def add(self, item):
        if not isinstance(item, str):
            raise ValueError("Only strings can be added to the FIFO")
        if len(self.queue) >= self.capacity:
            self.queue.pop(0)  # Remove the oldest item to maintain capacity
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.queue.append((item, timestamp))

    def prompt(self):
        return "\n".join([f"{time} - {text}" for text, time in self.queue])
