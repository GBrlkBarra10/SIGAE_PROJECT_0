_FNV_OFFSET = 2166136261
_FNV_PRIME = 16777619


def _is_prime(n):
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    d = 3
    while d * d <= n:
        if n % d == 0:
            return False
        d += 2
    return True


def _next_prime(n):
    while not _is_prime(n):
        n += 1
    return n


class _Entry:
    __slots__ = ("key", "value", "next")

    def __init__(self, key, value, nxt):
        self.key = key
        self.value = value
        self.next = nxt


class HashTable:
    def __init__(self, initial_capacity=7, max_load=0.75):
        self.capacity = _next_prime(initial_capacity)
        self.max_load = max_load
        self.buckets = [None] * self.capacity
        self.count = 0
        self.collisions = 0
        self.resize_log = []
        self.lookups = 0
        self.probes = 0

    def hash(self, key):
        h = _FNV_OFFSET
        for byte in str(key).encode("utf-8"):
            h ^= byte
            h = (h * _FNV_PRIME) & 0xFFFFFFFF
        return h % self.capacity

    def _find(self, key):
        self.lookups += 1
        e = self.buckets[self.hash(key)]
        while e is not None:
            self.probes += 1
            if e.key == key:
                return e
            e = e.next
        return None

    def average_probes(self):
        return self.probes / self.lookups if self.lookups else 0.0

    def put(self, key, value):
        idx = self.hash(key)
        e = self.buckets[idx]
        while e is not None:
            if e.key == key:
                e.value = value
                return False
            e = e.next
        if self.buckets[idx] is not None:
            self.collisions += 1
        self.buckets[idx] = _Entry(key, value, self.buckets[idx])
        self.count += 1
        if self.count / self.capacity > self.max_load:
            self._resize()
        return True

    def get(self, key, default=None):
        e = self._find(key)
        return default if e is None else e.value

    def contains(self, key):
        return self._find(key) is not None

    def remove(self, key):
        idx = self.hash(key)
        prev = None
        e = self.buckets[idx]
        while e is not None:
            if e.key == key:
                if prev is None:
                    self.buckets[idx] = e.next
                else:
                    prev.next = e.next
                self.count -= 1
                return True
            prev = e
            e = e.next
        return False

    def _resize(self):
        old = self.buckets
        old_cap = self.capacity
        self.capacity = _next_prime(old_cap * 2 + 1)
        self.buckets = [None] * self.capacity
        for head in old:
            e = head
            while e is not None:
                idx = self.hash(e.key)
                self.buckets[idx] = _Entry(e.key, e.value, self.buckets[idx])
                e = e.next
        self.resize_log.append((old_cap, self.capacity, self.count))

    def __len__(self):
        return self.count

    def load_factor(self):
        return self.count / self.capacity

    def values(self):
        out = []
        for head in self.buckets:
            e = head
            while e is not None:
                out.append(e.value)
                e = e.next
        return out

    def snapshot(self):
        out = []
        for head in self.buckets:
            chain = []
            e = head
            while e is not None:
                chain.append(e.key)
                e = e.next
            out.append(chain)
        return out

    def colliding_buckets(self):
        return sum(1 for head in self.buckets if head is not None and head.next is not None)
