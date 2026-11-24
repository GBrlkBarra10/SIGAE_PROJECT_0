RED = "R"
BLACK = "B"


class _Node:
    __slots__ = ("key", "value", "color", "left", "right", "parent")

    def __init__(self, key, value, color, left, right, parent):
        self.key = key
        self.value = value
        self.color = color
        self.left = left
        self.right = right
        self.parent = parent


class RedBlackTree:
    def __init__(self):
        self.NIL = _Node(None, None, BLACK, None, None, None)
        self.NIL.left = self.NIL.right = self.NIL.parent = self.NIL
        self.root = self.NIL
        self.count = 0
        self.inserts = 0
        self.removes = 0
        self.rotations = 0
        self.recolors = 0

    def __len__(self):
        return self.count

    def _set_color(self, n, c):
        if n is not self.NIL and n.color != c:
            self.recolors += 1
        n.color = c

    def _rotate_left(self, x):
        y = x.right
        x.right = y.left
        if y.left is not self.NIL:
            y.left.parent = x
        y.parent = x.parent
        if x.parent is self.NIL:
            self.root = y
        elif x is x.parent.left:
            x.parent.left = y
        else:
            x.parent.right = y
        y.left = x
        x.parent = y
        self.rotations += 1

    def _rotate_right(self, x):
        y = x.left
        x.left = y.right
        if y.right is not self.NIL:
            y.right.parent = x
        y.parent = x.parent
        if x.parent is self.NIL:
            self.root = y
        elif x is x.parent.right:
            x.parent.right = y
        else:
            x.parent.left = y
        y.right = x
        x.parent = y
        self.rotations += 1

    def _search_node(self, key):
        x = self.root
        while x is not self.NIL:
            if key == x.key:
                return x
            x = x.left if key < x.key else x.right
        return None

    def _min_node(self, x):
        while x.left is not self.NIL:
            x = x.left
        return x

    def search(self, key):
        n = self._search_node(key)
        return None if n is None else n.value

    def contains(self, key):
        return self._search_node(key) is not None

    def min(self):
        return None if self.root is self.NIL else self._min_node(self.root).value

    def insert(self, key, value):
        y, x = self.NIL, self.root
        while x is not self.NIL:
            y = x
            if key == x.key:
                raise ValueError("Rubro-Negra: chave duplicada.")
            x = x.left if key < x.key else x.right
        z = _Node(key, value, RED, self.NIL, self.NIL, y)
        if y is self.NIL:
            self.root = z
        elif key < y.key:
            y.left = z
        else:
            y.right = z
        self.count += 1
        self.inserts += 1
        self._insert_fixup(z)

    def _insert_fixup(self, z):
        while z.parent.color == RED:
            gp = z.parent.parent
            if z.parent is gp.left:
                uncle = gp.right
                if uncle.color == RED:
                    self._set_color(z.parent, BLACK)
                    self._set_color(uncle, BLACK)
                    self._set_color(gp, RED)
                    z = gp
                else:
                    if z is z.parent.right:
                        z = z.parent
                        self._rotate_left(z)
                    self._set_color(z.parent, BLACK)
                    self._set_color(z.parent.parent, RED)
                    self._rotate_right(z.parent.parent)
            else:
                uncle = gp.left
                if uncle.color == RED:
                    self._set_color(z.parent, BLACK)
                    self._set_color(uncle, BLACK)
                    self._set_color(gp, RED)
                    z = gp
                else:
                    if z is z.parent.left:
                        z = z.parent
                        self._rotate_right(z)
                    self._set_color(z.parent, BLACK)
                    self._set_color(z.parent.parent, RED)
                    self._rotate_left(z.parent.parent)
        self._set_color(self.root, BLACK)

    def _transplant(self, u, v):
        if u.parent is self.NIL:
            self.root = v
        elif u is u.parent.left:
            u.parent.left = v
        else:
            u.parent.right = v
        v.parent = u.parent

    def remove(self, key):
        z = self._search_node(key)
        if z is None:
            return None
        y = z
        y_color = y.color
        if z.left is self.NIL:
            x = z.right
            self._transplant(z, z.right)
        elif z.right is self.NIL:
            x = z.left
            self._transplant(z, z.left)
        else:
            y = self._min_node(z.right)
            y_color = y.color
            x = y.right
            if y.parent is z:
                x.parent = y
            else:
                self._transplant(y, y.right)
                y.right = z.right
                y.right.parent = y
            self._transplant(z, y)
            y.left = z.left
            y.left.parent = y
            y.color = z.color
        if y_color == BLACK:
            self._delete_fixup(x)
        self.NIL.parent = self.NIL
        self.count -= 1
        self.removes += 1
        return z.value

    def _delete_fixup(self, x):
        while x is not self.root and x.color == BLACK:
            if x is x.parent.left:
                w = x.parent.right
                if w.color == RED:
                    self._set_color(w, BLACK)
                    self._set_color(x.parent, RED)
                    self._rotate_left(x.parent)
                    w = x.parent.right
                if w.left.color == BLACK and w.right.color == BLACK:
                    self._set_color(w, RED)
                    x = x.parent
                else:
                    if w.right.color == BLACK:
                        self._set_color(w.left, BLACK)
                        self._set_color(w, RED)
                        self._rotate_right(w)
                        w = x.parent.right
                    self._set_color(w, x.parent.color)
                    self._set_color(x.parent, BLACK)
                    self._set_color(w.right, BLACK)
                    self._rotate_left(x.parent)
                    x = self.root
            else:
                w = x.parent.left
                if w.color == RED:
                    self._set_color(w, BLACK)
                    self._set_color(x.parent, RED)
                    self._rotate_right(x.parent)
                    w = x.parent.left
                if w.right.color == BLACK and w.left.color == BLACK:
                    self._set_color(w, RED)
                    x = x.parent
                else:
                    if w.left.color == BLACK:
                        self._set_color(w.right, BLACK)
                        self._set_color(w, RED)
                        self._rotate_left(w)
                        w = x.parent.left
                    self._set_color(w, x.parent.color)
                    self._set_color(x.parent, BLACK)
                    self._set_color(w.left, BLACK)
                    self._rotate_right(x.parent)
                    x = self.root
        self._set_color(x, BLACK)

    def inorder(self):
        stack, x = [], self.root
        while stack or x is not self.NIL:
            while x is not self.NIL:
                stack.append(x)
                x = x.left
            x = stack.pop()
            yield x.key, x.value
            x = x.right

    def values(self):
        return [v for _, v in self.inorder()]

    def height(self):
        def h(n):
            return 0 if n is self.NIL else 1 + max(h(n.left), h(n.right))
        return h(self.root)

    def validate(self):
        errors = []
        if self.root.color != BLACK:
            errors.append("Raiz não é preta")
        prev = [None]
        n = [0]

        def walk(node):
            if node is self.NIL:
                return 1
            if node.color == RED and (node.left.color == RED or node.right.color == RED):
                errors.append("Nó vermelho com filho vermelho")
            for child in (node.left, node.right):
                if child is not self.NIL and child.parent is not node:
                    errors.append("Ponteiro de pai inconsistente")
            lh = walk(node.left)
            if prev[0] is not None and not (prev[0] < node.key):
                errors.append("Ordem violada")
            prev[0] = node.key
            n[0] += 1
            rh = walk(node.right)
            if lh != rh:
                errors.append("Altura negra divergente")
            return lh + (1 if node.color == BLACK else 0)

        bh = walk(self.root)
        if n[0] != self.count:
            errors.append("Contagem divergente")
        return errors, bh - 1
