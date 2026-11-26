import time

from .estruturas import AVLTree, HashTable, MinHeap, RedBlackTree

RISCOS = ("", "Emergência", "Muito urgente", "Urgente", "Pouco urgente", "Não urgente")
TEMPO_ALVO = ("", "atendimento imediato", "até 10 min", "até 60 min", "até 120 min", "até 240 min")

AGUARDANDO = "Aguardando"
EM_ATENDIMENTO = "Em atendimento"
CONCLUIDO = "Concluído"
CANCELADO = "Cancelado"
DISPONIVEL = "Disponível"

CONTADORES = ("proximo_paciente_id", "proximo_medico_id", "proximo_atendimento_id", "seq_atribuicao")


class SigaeError(Exception):
    pass


class Paciente:
    __slots__ = ("id", "nome", "chegada", "prioridade", "situacao", "medico_id",
                 "atendimento_id", "atendimentos", "triagens")

    def __init__(self, id, nome, chegada, prioridade):
        self.id = id
        self.nome = nome
        self.chegada = chegada
        self.prioridade = prioridade
        self.situacao = AGUARDANDO
        self.medico_id = None
        self.atendimento_id = None
        self.atendimentos = []
        self.triagens = []

    @property
    def risco(self):
        return RISCOS[self.prioridade]


class Medico:
    __slots__ = ("id", "nome", "registro", "situacao", "concluidos", "cancelados",
                 "ultima_seq", "ultima_atribuicao", "atendimento_id", "removido")

    def __init__(self, id, nome, registro):
        self.removido = False
        self.id = id
        self.nome = nome
        self.registro = registro
        self.situacao = DISPONIVEL
        self.concluidos = 0
        self.cancelados = 0
        self.ultima_seq = 0
        self.ultima_atribuicao = None
        self.atendimento_id = None


class Atendimento:
    __slots__ = ("id", "paciente_id", "medico_id", "prioridade", "inicio", "fim",
                 "situacao", "resultado")

    def __init__(self, id, paciente_id, medico_id, prioridade, inicio):
        self.id = id
        self.paciente_id = paciente_id
        self.medico_id = medico_id
        self.prioridade = prioridade
        self.inicio = inicio
        self.fim = None
        self.situacao = EM_ATENDIMENTO
        self.resultado = None


class Indicadores:
    __slots__ = ("aguardando", "em_atendimento", "concluidos", "cancelados", "total_pacientes",
                 "medicos_total", "medicos_livres", "espera_media")

    @property
    def por_situacao(self):
        return [(AGUARDANDO, self.aguardando), (EM_ATENDIMENTO, self.em_atendimento),
                (CONCLUIDO, self.concluidos), (CANCELADO, self.cancelados)]


def chave_paciente(p):
    return (p.prioridade, p.chegada, p.id)


def chave_medico(m):
    return (m.concluidos, m.ultima_seq, m.id)


def _id(x):
    return x.id


def _validar_risco(valor):
    try:
        p = int(valor)
    except (TypeError, ValueError):
        raise SigaeError("Classificação de risco inválida (use 1 a 5).")
    if not 1 <= p <= 5:
        raise SigaeError("Classificação de risco inválida (use 1 a 5).")
    return p


class Sigae:
    def __init__(self, relogio=None):
        self.relogio = relogio or time.time
        self.reiniciar()

    def reiniciar(self):
        self.pacientes = HashTable(7)
        self.medicos = HashTable(7)
        self.atendimentos = HashTable(7)
        self.registros = HashTable(7)
        self.indice_espera = RedBlackTree()
        self.historico_chegadas = AVLTree()
        self.fila_pacientes = MinHeap(chave_paciente, _id)
        self.fila_medicos = MinHeap(chave_medico, _id)
        self.proximo_paciente_id = 1
        self.proximo_medico_id = 1
        self.proximo_atendimento_id = 1
        self.seq_atribuicao = 0
        self.eventos = []

    def _registrar(self, msg):
        self.eventos.append((self.relogio(), msg))
        if len(self.eventos) > 500:
            self.eventos.pop(0)

    def cadastrar_paciente(self, nome, prioridade, chegada=None):
        nome = (nome or "").strip()
        if not nome:
            raise SigaeError("Informe o nome do paciente.")
        prioridade = _validar_risco(prioridade)
        chegada = self.relogio() if chegada is None else float(chegada)
        p = Paciente(self.proximo_paciente_id, nome, chegada, prioridade)
        self.proximo_paciente_id += 1
        p.triagens.append((self.relogio(), None, prioridade))
        self.pacientes.put(p.id, p)
        self.historico_chegadas.insert((p.chegada, p.id), p)
        self._enfileirar(p)
        self._registrar(f"{p.nome} (nº {p.id}) cadastrado(a) — {p.risco}.")
        return p

    def _enfileirar(self, p):
        self.indice_espera.insert((p.chegada, p.id), p)
        self.fila_pacientes.push(p)

    def _desenfileirar(self, p):
        self.indice_espera.remove((p.chegada, p.id))
        self.fila_pacientes.remove(p.id)

    def paciente(self, pid):
        try:
            return self.pacientes.get(int(pid))
        except (TypeError, ValueError):
            return None

    def _exigir_paciente(self, pid):
        p = self.paciente(pid)
        if p is None:
            raise SigaeError(f"Paciente nº {pid} não encontrado.")
        return p

    def reclassificar(self, pid, prioridade):
        p = self._exigir_paciente(pid)
        prioridade = _validar_risco(prioridade)
        if p.situacao in (CONCLUIDO, CANCELADO):
            raise SigaeError(f"{p.nome} está {p.situacao.lower()}; não pode ser reclassificado(a).")
        if p.prioridade == prioridade:
            return p
        antes = p.prioridade
        p.prioridade = prioridade
        p.triagens.append((self.relogio(), antes, prioridade))
        if p.situacao == AGUARDANDO:
            self.fila_pacientes.update(p.id)
        self._registrar(f"{p.nome} reclassificado(a): {RISCOS[antes]} → {RISCOS[prioridade]}.")
        return p

    def cancelar_paciente(self, pid):
        p = self._exigir_paciente(pid)
        if p.situacao == AGUARDANDO:
            self._desenfileirar(p)
            p.situacao = CANCELADO
            self._registrar(f"Cadastro de {p.nome} cancelado (estava aguardando).")
        elif p.situacao == EM_ATENDIMENTO:
            self.cancelar_atendimento(p.atendimento_id, devolver_a_fila=False)
        else:
            raise SigaeError(f"{p.nome} já está {p.situacao.lower()}.")
        return p

    def cadastrar_medico(self, nome, registro):
        nome = (nome or "").strip()
        registro = (registro or "").strip()
        if not nome:
            raise SigaeError("Informe o nome do médico.")
        if not registro:
            raise SigaeError("Informe o registro profissional (fictício).")
        existente = self.registros.get(registro.upper())
        if existente is not None:
            raise SigaeError(f"O registro {registro} já pertence a {existente.nome}.")
        m = Medico(self.proximo_medico_id, nome, registro)
        self.proximo_medico_id += 1
        self.medicos.put(m.id, m)
        self.registros.put(m.registro.upper(), m)
        self.fila_medicos.push(m)
        self._registrar(f"{m.nome} ({m.registro}) cadastrado(a).")
        return m

    def medico(self, mid):
        try:
            return self.medicos.get(int(mid))
        except (TypeError, ValueError):
            return None

    def remover_medico(self, mid):
        m = self.medico(mid)
        if m is None or m.removido:
            raise SigaeError(f"Médico nº {mid} não encontrado.")
        if m.situacao == EM_ATENDIMENTO:
            raise SigaeError(f"{m.nome} está atendendo. Conclua ou cancele o atendimento antes de apagar.")
        self.fila_medicos.remove(m.id)
        self.registros.remove(m.registro.upper())
        m.removido = True
        self._registrar(f"{m.nome} foi removido(a) do plantão ({m.concluidos} atendimento(s) concluído(s)).")
        return m

    def previa_chamada(self):
        return self.fila_pacientes.peek(), self.fila_medicos.peek()

    def chamar_proximo(self):
        if self.fila_pacientes.is_empty():
            raise SigaeError("Não há pacientes aguardando na fila.")
        if self.fila_medicos.is_empty():
            raise SigaeError("Nenhum médico disponível no momento. O paciente permanece na fila.")
        p = self.fila_pacientes.pop()
        m = self.fila_medicos.pop()
        self.indice_espera.remove((p.chegada, p.id))
        agora = self.relogio()
        a = Atendimento(self.proximo_atendimento_id, p.id, m.id, p.prioridade, agora)
        self.proximo_atendimento_id += 1
        self.atendimentos.put(a.id, a)
        p.situacao = EM_ATENDIMENTO
        p.medico_id = m.id
        p.atendimento_id = a.id
        p.atendimentos.append(a.id)
        m.situacao = EM_ATENDIMENTO
        m.atendimento_id = a.id
        self.seq_atribuicao += 1
        m.ultima_seq = self.seq_atribuicao
        m.ultima_atribuicao = agora
        self._registrar(f"{p.nome} ({p.risco}) chamado(a) para {m.nome} ({m.concluidos} concluídos).")
        return p, m, a

    def atendimento(self, aid):
        try:
            return self.atendimentos.get(int(aid))
        except (TypeError, ValueError):
            return None

    def _exigir_ativo(self, aid):
        a = self.atendimento(aid)
        if a is None:
            raise SigaeError(f"Atendimento nº {aid} não encontrado.")
        if a.situacao != EM_ATENDIMENTO:
            raise SigaeError(f"O atendimento nº {a.id} já está {a.situacao.lower()}.")
        return a

    def _liberar_medico(self, m):
        m.situacao = DISPONIVEL
        m.atendimento_id = None
        self.fila_medicos.push(m)

    def concluir_atendimento(self, aid):
        a = self._exigir_ativo(aid)
        p, m = self.paciente(a.paciente_id), self.medico(a.medico_id)
        a.situacao = CONCLUIDO
        a.fim = self.relogio()
        a.resultado = "Concluído"
        p.situacao = CONCLUIDO
        p.atendimento_id = None
        m.concluidos += 1
        self._liberar_medico(m)
        self._registrar(f"Atendimento de {p.nome} concluído. {m.nome} agora tem {m.concluidos} concluído(s).")
        return a

    def cancelar_atendimento(self, aid, devolver_a_fila):
        a = self._exigir_ativo(aid)
        p, m = self.paciente(a.paciente_id), self.medico(a.medico_id)
        a.situacao = CANCELADO
        a.fim = self.relogio()
        a.resultado = "Paciente devolvido à fila" if devolver_a_fila else "Cadastro encerrado"
        m.cancelados += 1
        self._liberar_medico(m)
        p.atendimento_id = None
        p.medico_id = None
        if devolver_a_fila:
            p.situacao = AGUARDANDO
            self._enfileirar(p)
        else:
            p.situacao = CANCELADO
        self._registrar(f"Atendimento de {p.nome} cancelado ({a.resultado.lower()}). "
                        f"{m.nome} liberado(a) sem alterar o contador ({m.concluidos}).")
        return a

    def listar_pacientes(self):
        out = []
        for pid in range(1, self.proximo_paciente_id):
            p = self.pacientes.get(pid)
            if p is not None:
                out.append(p)
        return out

    def listar_medicos(self, incluir_removidos=False):
        out = []
        for mid in range(1, self.proximo_medico_id):
            m = self.medicos.get(mid)
            if m is not None and (incluir_removidos or not m.removido):
                out.append(m)
        return out

    def pacientes_ativos(self):
        return [p for p in self.listar_pacientes() if p.situacao in (AGUARDANDO, EM_ATENDIMENTO)]

    def listar_atendimentos(self):
        out = []
        for aid in range(1, self.proximo_atendimento_id):
            a = self.atendimentos.get(aid)
            if a is not None:
                out.append(a)
        return out

    def atendimentos_ativos(self):
        return [a for a in self.listar_atendimentos() if a.situacao == EM_ATENDIMENTO]

    def ordem_da_fila(self):
        return self.fila_pacientes.ordered()

    def ordem_dos_medicos(self):
        return self.fila_medicos.ordered()

    def espera_por_chegada(self):
        return self.indice_espera.values()

    def chegadas_cronologicas(self):
        return self.historico_chegadas.values()

    def posicao_na_fila(self, pid):
        for i, p in enumerate(self.ordem_da_fila(), start=1):
            if p.id == pid:
                return i
        return None

    def indicadores(self):
        ind = Indicadores()
        ind.aguardando = ind.em_atendimento = ind.concluidos = ind.cancelados = 0
        for p in self.pacientes.values():
            if p.situacao == AGUARDANDO:
                ind.aguardando += 1
            elif p.situacao == EM_ATENDIMENTO:
                ind.em_atendimento += 1
            elif p.situacao == CONCLUIDO:
                ind.concluidos += 1
            else:
                ind.cancelados += 1
        medicos = self.listar_medicos()
        ind.total_pacientes = len(self.pacientes)
        ind.medicos_total = len(medicos)
        ind.medicos_livres = sum(1 for m in medicos if m.situacao == DISPONIVEL)
        esperas = []
        for a in self.listar_atendimentos():
            p = self.paciente(a.paciente_id)
            if p is not None:
                esperas.append(a.inicio - p.chegada)
        ind.espera_media = (sum(esperas) / len(esperas)) if esperas else None
        return ind

    def verificar_consistencia(self):
        problemas = []
        aguardando = em_atendimento = 0
        for p in self.pacientes.values():
            no_heap = self.fila_pacientes.contains(p.id)
            na_arvore = self.indice_espera.contains((p.chegada, p.id))
            if p.situacao == AGUARDANDO:
                aguardando += 1
                if not no_heap:
                    problemas.append(f"Paciente {p.id} aguardando fora do Heap")
                if not na_arvore:
                    problemas.append(f"Paciente {p.id} aguardando fora da Rubro-Negra")
            else:
                if no_heap:
                    problemas.append(f"Paciente {p.id} ({p.situacao}) ainda no Heap")
                if na_arvore:
                    problemas.append(f"Paciente {p.id} ({p.situacao}) ainda na Rubro-Negra")
            if p.situacao == EM_ATENDIMENTO:
                em_atendimento += 1
                a = self.atendimento(p.atendimento_id)
                if a is None or a.situacao != EM_ATENDIMENTO:
                    problemas.append(f"Paciente {p.id} em atendimento sem atendimento ativo")
                else:
                    m = self.medico(a.medico_id)
                    if m is None or m.atendimento_id != a.id or m.situacao != EM_ATENDIMENTO:
                        problemas.append(f"Vínculo médico–paciente inconsistente no atendimento {a.id}")
            if not self.historico_chegadas.contains((p.chegada, p.id)):
                problemas.append(f"Paciente {p.id} ausente do histórico de chegadas (AVL)")
        if len(self.fila_pacientes) != aguardando:
            problemas.append("Heap de pacientes com tamanho divergente")
        if len(self.indice_espera) != aguardando:
            problemas.append("Rubro-Negra com tamanho divergente")

        soma = 0
        for m in self.medicos.values():
            soma += m.concluidos
            no_heap = self.fila_medicos.contains(m.id)
            if m.removido:
                if no_heap:
                    problemas.append(f"Médico {m.id} removido ainda no Heap")
                if m.situacao == EM_ATENDIMENTO:
                    problemas.append(f"Médico {m.id} removido durante um atendimento")
                continue
            if self.registros.get(m.registro.upper()) is not m:
                problemas.append(f"Médico {m.id} fora do índice de registros")
            if m.situacao == DISPONIVEL and not no_heap:
                problemas.append(f"Médico {m.id} disponível fora do Heap")
            if m.situacao == EM_ATENDIMENTO:
                if no_heap:
                    problemas.append(f"Médico {m.id} ocupado ainda no Heap")
                a = self.atendimento(m.atendimento_id)
                if a is None or a.situacao != EM_ATENDIMENTO or a.medico_id != m.id:
                    problemas.append(f"Médico {m.id} ocupado sem atendimento ativo")
        concluidos = ativos = 0
        for a in self.atendimentos.values():
            if a.situacao == CONCLUIDO:
                concluidos += 1
            elif a.situacao == EM_ATENDIMENTO:
                ativos += 1
        if ativos != em_atendimento:
            problemas.append("Atendimentos ativos ≠ pacientes em atendimento")
        if soma != concluidos:
            problemas.append("Soma dos contadores ≠ atendimentos concluídos")

        erros, _ = self.indice_espera.validate()
        problemas += ["Rubro-Negra: " + e for e in erros]
        problemas += ["AVL (histórico): " + e for e in self.historico_chegadas.validate()]
        if len(self.historico_chegadas) != len(self.pacientes):
            problemas.append("AVL com tamanho diferente da Hash de pacientes")
        problemas += ["Heap pacientes: " + e for e in self.fila_pacientes.validate()]
        problemas += ["Heap médicos: " + e for e in self.fila_medicos.validate()]
        return problemas

    def restaurar(self, medicos, pacientes, atendimentos, eventos, contadores):
        self.reiniciar()
        for m in medicos:
            self.medicos.put(m.id, m)
            if not m.removido:
                self.registros.put(m.registro.upper(), m)
                if m.situacao == DISPONIVEL:
                    self.fila_medicos.push(m)
        for p in pacientes:
            self.pacientes.put(p.id, p)
            self.historico_chegadas.insert((p.chegada, p.id), p)
            if p.situacao == AGUARDANDO:
                self._enfileirar(p)
        for a in atendimentos:
            self.atendimentos.put(a.id, a)
        self.eventos = list(eventos)
        for nome, valor in zip(CONTADORES, contadores):
            setattr(self, nome, valor)
