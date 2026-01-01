import threading
from collections import OrderedDict

class StockCache:
    def __init__(self, max_size=50):
        self.cache = OrderedDict()
        self.lock = threading.Lock()
        self.max_size = max_size

    def get(self, key):
        with self.lock:
            data = self.cache.get(key)
            if data:
                self.cache.move_to_end(key)
            return data

    def set(self, key, value):
        with self.lock:
            self.cache[key] = value
            self.cache.move_to_end(key)
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)