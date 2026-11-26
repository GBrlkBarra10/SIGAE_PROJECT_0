class Contadores:
    __slots__ = ("rb_tam", "rb_ins", "rb_rem", "rb_rot", "rb_rec",
                 "avl_tam", "avl_ins", "avl_rot", "avl_simples", "avl_duplas",
                 "hp_tam", "hp_trocas", "hm_tam", "hm_trocas",
                 "hash_itens", "hash_colisoes", "hash_redim", "hash_capacidades")

    @staticmethod
    def capturar(s):
        c = Contadores()
        rb, avl = s.indice_espera, s.historico_chegadas
        c.rb_tam, c.rb_ins, c.rb_rem, c.rb_rot, c.rb_rec = len(rb), rb.inserts, rb.removes, rb.rotations, rb.recolors
        c.avl_tam, c.avl_ins, c.avl_rot = len(avl), avl.inserts, avl.rotations
        c.avl_simples, c.avl_duplas = avl.simple_rotations, avl.double_rotations
        c.hp_tam, c.hp_trocas = len(s.fila_pacientes), s.fila_pacientes.swaps
        c.hm_tam, c.hm_trocas = len(s.fila_medicos), s.fila_medicos.swaps
        tabelas = tabelas_hash(s)
        c.hash_itens = sum(len(h) for _, h in tabelas)
        c.hash_colisoes = sum(h.collisions for _, h in tabelas)
        c.hash_redim = sum(len(h.resize_log) for _, h in tabelas)
        c.hash_capacidades = tuple(h.capacity for _, h in tabelas)
        return c


def tabelas_hash(s):
    return [("Pacientes (por ID)", s.pacientes), ("Médicos (por ID)", s.medicos),
            ("Atendimentos (por ID)", s.atendimentos), ("Registros profissionais", s.registros)]


def _plural(n, um, varios):
    return f"{n} {um if n == 1 else varios}"


def diferenca(a, b, s=None):
    out = []
    partes = []
    if b.rb_ins > a.rb_ins:
        partes.append(f"+{b.rb_ins - a.rb_ins} inserção")
    if b.rb_rem > a.rb_rem:
        partes.append(f"−{b.rb_rem - a.rb_rem} remoção")
    if b.rb_rot > a.rb_rot:
        partes.append(_plural(b.rb_rot - a.rb_rot, "rotação", "rotações"))
    if b.rb_rec > a.rb_rec:
        partes.append(_plural(b.rb_rec - a.rb_rec, "recoloração", "recolorações"))
    if partes:
        out.append(f"Rubro-Negra (espera): {', '.join(partes)} · {a.rb_tam} → {b.rb_tam} nós")

    partes = []
    if b.avl_ins > a.avl_ins:
        partes.append(f"+{b.avl_ins - a.avl_ins} inserção")
    if b.avl_simples > a.avl_simples:
        partes.append(_plural(b.avl_simples - a.avl_simples, "rotação simples", "rotações simples"))
    if b.avl_duplas > a.avl_duplas:
        partes.append(_plural(b.avl_duplas - a.avl_duplas, "rotação dupla", "rotações duplas"))
    if partes:
        out.append(f"AVL (histórico): {', '.join(partes)} · {a.avl_tam} → {b.avl_tam} nós")

    for nome, ta, tb, ca, cb in (("Heap de pacientes", a.hp_tam, b.hp_tam, a.hp_trocas, b.hp_trocas),
                                 ("Heap de médicos", a.hm_tam, b.hm_tam, a.hm_trocas, b.hm_trocas)):
        if ta != tb or cb > ca:
            texto = f"{nome}: {ta} → {tb} itens"
            if cb > ca:
                texto += f", {_plural(cb - ca, 'troca pai/filho', 'trocas pai/filho')}"
            out.append(texto)

    partes = []
    if b.hash_itens != a.hash_itens:
        partes.append(f"{a.hash_itens} → {b.hash_itens} registros")
    if b.hash_colisoes > a.hash_colisoes:
        partes.append(_plural(b.hash_colisoes - a.hash_colisoes, "colisão (encadeada)", "colisões (encadeadas)"))
    if b.hash_redim > a.hash_redim and s is not None:
        for (nome, _), ca, cb in zip(tabelas_hash(s), a.hash_capacidades, b.hash_capacidades):
            if ca != cb:
                partes.append(f"{nome} redimensionada {ca} → {cb} (rehash)")
    if partes:
        out.append(f"Tabelas Hash: {', '.join(partes)}")
    return out


class RegistroMonitor:
    __slots__ = ("momento", "acao", "mudancas", "problemas")

    def __init__(self, momento, acao, mudancas, problemas):
        self.momento = momento
        self.acao = acao
        self.mudancas = mudancas
        self.problemas = problemas


class NoDesenho:
    __slots__ = ("x", "y", "rotulo", "detalhe", "cor", "dica")


class ArestaDesenho:
    __slots__ = ("x1", "y1", "x2", "y2")


class Desenho:
    __slots__ = ("nos", "arestas", "largura", "altura", "cortado")


ESPACO_X = 58
ESPACO_Y = 66
NIVEIS_MAX = 6


def desenhar(raiz, vazio, esquerda, direita, rotulo, detalhe, cor, dica):
    d = Desenho()
    d.nos, d.arestas, d.cortado = [], [], False
    ordem = [0]
    prof_max = [0]

    def visitar(n, prof):
        if vazio(n):
            return None
        if prof >= NIVEIS_MAX:
            d.cortado = True
            return None
        e = visitar(esquerda(n), prof + 1)
        no = NoDesenho()
        no.x = 20 + ordem[0] * ESPACO_X + ESPACO_X // 2
        no.y = 32 + prof * ESPACO_Y
        no.rotulo, no.detalhe, no.cor, no.dica = rotulo(n), detalhe(n), cor(n), dica(n)
        ordem[0] += 1
        prof_max[0] = max(prof_max[0], prof)
        d.nos.append(no)
        r = visitar(direita(n), prof + 1)
        for filho in (e, r):
            if filho is not None:
                a = ArestaDesenho()
                a.x1, a.y1, a.x2, a.y2 = no.x, no.y, filho.x, filho.y
                d.arestas.append(a)
        return no

    visitar(raiz, 0)
    d.largura = max(320, 40 + ordem[0] * ESPACO_X)
    d.altura = 64 + prof_max[0] * ESPACO_Y
    return d


class NivelHeap:
    __slots__ = ("itens",)


class ItemHeap:
    __slots__ = ("pos", "rotulo", "detalhe", "cor", "raiz")


def niveis_heap(vetor, rotulo, detalhe, cor):
    niveis, i, tam = [], 0, 1
    while i < len(vetor):
        nivel = NivelHeap()
        nivel.itens = []
        for _ in range(tam):
            if i >= len(vetor):
                break
            it = ItemHeap()
            it.pos, it.rotulo, it.detalhe, it.cor, it.raiz = i, rotulo(vetor[i]), detalhe(vetor[i]), cor(vetor[i]), i == 0
            nivel.itens.append(it)
            i += 1
        niveis.append(nivel)
        tam *= 2
    return niveis
