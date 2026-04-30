import uuid

class CounterService:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.counter = 0

    def increment(self):
        self.counter += 1
        return self.counter