"""Bounded, ephemeral selection state. No messages, files or personal details."""
import hashlib
import time
from collections import OrderedDict
from threading import RLock


class DialogueContext:
    FIELDS = {"product_id", "quantity", "city", "budget", "family"}

    def __init__(self, clock=time.time, ttl=1800, capacity=1024):
        self.clock, self.ttl, self.capacity = clock, ttl, capacity
        self._entries, self._lock = OrderedDict(), RLock()

    @staticmethod
    def _key(session_id):
        return hashlib.sha256(session_id.encode()).hexdigest()

    def get(self, session_id):
        key, now = self._key(session_id), self.clock()
        with self._lock:
            # Bounded even if sessions are abandoned without another request.
            for expired in [key for key, (at, _) in self._entries.items() if now - at >= self.ttl]:
                self._entries.pop(expired, None)
            item = self._entries.get(key)
            return dict(item[1]) if item else {}

    def update(self, session_id, **values):
        key = self._key(session_id)
        with self._lock:
            state = self.get(session_id)
            state.update({name: value for name, value in values.items() if name in self.FIELDS})
            self._entries[key] = (self.clock(), state)
            self._entries.move_to_end(key)
            while len(self._entries) > self.capacity:
                self._entries.popitem(last=False)
            return dict(state)
