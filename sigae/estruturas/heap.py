from .hash_table import HashTable


class MinHeap:
    def __init__(self, key_fn, id_fn):
        self.a = []
        self.key = key_fn
        self.id_of = id_fn
        self.pos = HashTable(11)
        self.swaps = 0

    def __len__(self):
        return len(self.a)

    def is_empty(self):
        return not self.a

    def peek(self):
        return self.a[0] if self.a else None

    def contains(self, item_id):
        return self.pos.contains(item_id)

    def _less(self, i, j):
        return self.key(self.a[i]) < self.key(self.a[j])

    def _swap(self, i, j):
        self.swaps += 1
        self.a[i], self.a[j] = self.a[j], self.a[i]
        self.pos.put(self.id_of(self.a[i]), i)
        self.pos.put(self.id_of(self.a[j]), j)

    def _sift_up(self, i):
        while i > 0:
            p = (i - 1) // 2
            if not self._less(i, p):
                break
            self._swap(i, p)
            i = p
        return i

    def _sift_down(self, i):
        n = len(self.a)
        while True:
            l, r, m = 2 * i + 1, 2 * i + 2, i
            if l < n and self._less(l, m):
                m = l
            if r < n and self._less(r, m):
                m = r
            if m == i:
                return i
            self._swap(i, m)
            i = m

    def push(self, item):
        item_id = self.id_of(item)
        if self.pos.contains(item_id):
            raise ValueError(f"Heap: elemento {item_id} já está no heap (duplicação evitada).")
        self.a.append(item)
        self.pos.put(item_id, len(self.a) - 1)
        self._sift_up(len(self.a) - 1)

    def pop(self):
        if not self.a:
            return None
        top = self.a[0]
        last = self.a.pop()
        self.pos.remove(self.id_of(top))
        if self.a:
            self.a[0] = last
            self.pos.put(self.id_of(last), 0)
            self._sift_down(0)
        return top

    def remove(self, item_id):
        i = self.pos.get(item_id)
        if i is None:
            return None
        item = self.a[i]
        last = self.a.pop()
        self.pos.remove(item_id)
        if i < len(self.a):
            self.a[i] = last
            self.pos.put(self.id_of(last), i)
            self._sift_down(self._sift_up(i))
        return item

    def update(self, item_id):
        i = self.pos.get(item_id)
        if i is None:
            return False
        self._sift_down(self._sift_up(i))
        return True

    def to_list(self):
        return list(self.a)

    def ordered(self):
        copy = MinHeap(self.key, self.id_of)
        for i, item in enumerate(self.a):
            copy.a.append(item)
            copy.pos.put(self.id_of(item), i)
        out = []
        while copy.a:
            out.append(copy.pop())
        return out

    def validate(self):
        errors = []
        n = len(self.a)
        for i in range(n):
            for c in (2 * i + 1, 2 * i + 2):
                if c < n and self._less(c, i):
                    errors.append(f"Filho menor que o pai na posição {i}")
            if self.pos.get(self.id_of(self.a[i])) != i:
                errors.append(f"Índice de posição inconsistente para {self.id_of(self.a[i])}")
        if len(self.pos) != n:
            errors.append("Índice de posições com tamanho divergente")
        return errors
