from datetime import datetime
import os

class Fifo:
    def __init__(self):
        self.capacity = 100
        self.queue = []
        self.log_file = "fifo_log.txt"  # Define the log file name
        # Ensure the file exists
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as file:
                file.write("")

    def add(self, item):
        if not isinstance(item, str):
            raise ValueError("Only strings can be added to the FIFO")
        if len(self.queue) >= self.capacity:
            self.queue.pop(0)  # Remove the oldest item to maintain capacity
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.queue.append((item, timestamp))
        self.log_to_file(item, timestamp)  # Log addition to file

    def log_to_file(self, item, timestamp):
        with open(self.log_file, 'a') as file:
            file.write(f"{timestamp} - {item}\n")  # Append the new item and timestamp to the log file

    def prompt(self):
        return "\n".join([f"{time} - {text}" for text, time in reversed(self.queue)])  # Display most recent first
