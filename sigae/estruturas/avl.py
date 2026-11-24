class _NoAVL:
    __slots__ = ("key", "value", "left", "right", "height")

    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.left = None
        self.right = None
        self.height = 1


def _altura(n):
    return 0 if n is None else n.height


def _fb(n):
    return _altura(n.left) - _altura(n.right)


def _atualizar(n):
    n.height = 1 + max(_altura(n.left), _altura(n.right))


class AVLTree:
    def __init__(self):
        self.root = None
        self.count = 0
        self.inserts = 0
        self.removes = 0
        self.rotations = 0
        self.simple_rotations = 0
        self.double_rotations = 0

    def __len__(self):
        return self.count

    def _rotate_right(self, y):
        x = y.left
        y.left = x.right
        x.right = y
        _atualizar(y)
        _atualizar(x)
        self.rotations += 1
        return x

    def _rotate_left(self, x):
        y = x.right
        x.right = y.left
        y.left = x
        _atualizar(x)
        _atualizar(y)
        self.rotations += 1
        return y

    def _balancear(self, n):
        _atualizar(n)
        fb = _fb(n)
        if fb > 1:
            if _fb(n.left) < 0:
                n.left = self._rotate_left(n.left)
                self.double_rotations += 1
            else:
                self.simple_rotations += 1
            return self._rotate_right(n)
        if fb < -1:
            if _fb(n.right) > 0:
                n.right = self._rotate_right(n.right)
                self.double_rotations += 1
            else:
                self.simple_rotations += 1
            return self._rotate_left(n)
        return n

    def insert(self, key, value):
        self.root = self._insert(self.root, key, value)
        self.count += 1
        self.inserts += 1

    def _insert(self, n, key, value):
        if n is None:
            return _NoAVL(key, value)
        if key == n.key:
            raise ValueError("AVL: chave duplicada.")
        if key < n.key:
            n.left = self._insert(n.left, key, value)
        else:
            n.right = self._insert(n.right, key, value)
        return self._balancear(n)

    def remove(self, key):
        removido = [None]
        self.root = self._remove(self.root, key, removido)
        if removido[0] is not None:
            self.count -= 1
            self.removes += 1
            return removido[0][0]
        return None

    def _remove(self, n, key, removido):
        if n is None:
            return None
        if key < n.key:
            n.left = self._remove(n.left, key, removido)
        elif key > n.key:
            n.right = self._remove(n.right, key, removido)
        else:
            removido[0] = (n.value,)
            if n.left is None:
                return n.right
            if n.right is None:
                return n.left
            s = n.right
            while s.left is not None:
                s = s.left
            n.key, n.value = s.key, s.value
            n.right = self._remove_min(n.right)
        return self._balancear(n)

    def _remove_min(self, n):
        if n.left is None:
            return n.right
        n.left = self._remove_min(n.left)
        return self._balancear(n)

    def _search_node(self, key):
        n = self.root
        while n is not None:
            if key == n.key:
                return n
            n = n.left if key < n.key else n.right
        return None

    def search(self, key):
        n = self._search_node(key)
        return None if n is None else n.value

    def contains(self, key):
        return self._search_node(key) is not None

    def min(self):
        n = self.root
        if n is None:
            return None
        while n.left is not None:
            n = n.left
        return n.value

    def inorder(self):
        stack, n = [], self.root
        while stack or n is not None:
            while n is not None:
                stack.append(n)
                n = n.left
            n = stack.pop()
            yield n.key, n.value
            n = n.right

    def values(self):
        return [v for _, v in self.inorder()]

    def height(self):
        return _altura(self.root)

    def validate(self):
        errors = []
        prev = [None]
        n = [0]

        def walk(node):
            if node is None:
                return 0
            hl = walk(node.left)
            if prev[0] is not None and not (prev[0] < node.key):
                errors.append("Ordem violada")
            prev[0] = node.key
            n[0] += 1
            hr = walk(node.right)
            if node.height != 1 + max(hl, hr):
                errors.append("Altura guardada incorreta")
            if abs(hl - hr) > 1:
                errors.append("Fator de balanceamento fora de -1..+1")
            return 1 + max(hl, hr)

        walk(self.root)
        if n[0] != self.count:
            errors.append("Contagem divergente")
        return errors
