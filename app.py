import json
import logging
import os
import random
import threading
import time
from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, url_for
from sigae.banco import BancoDados
from sigae.sistema import RISCOS, TEMPO_ALVO, Sigae, SigaeError

BASE = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_BANCO = os.path.join(BASE, "dados", "sigae.db")
ARQUIVO_JSON_ANTIGO = os.path.join(BASE, "dados", "sigae.json") 

app = Flask(__name__)
app.secret_key = "sigae-simulador-academico"

sistema = Sigae()
banco = BancoDados(ARQUIVO_BANCO)
trava = threading.Lock()                       

def carregar():
    dados = banco.carregar()
    if dados is not None:
        sistema.importar(dados)
        return

    if os.path.exists(ARQUIVO_JSON_ANTIGO):
        try:
            with open(ARQUIVO_JSON_ANTIGO, encoding="utf-8") as f:
                sistema.importar(json.load(f))
            banco.salvar(sistema)
            os.replace(ARQUIVO_JSON_ANTIGO, ARQUIVO_JSON_ANTIGO + ".migrado")
            print("Dados do arquivo JSON antigo copiados para o banco SQL.")
        except (OSError, ValueError, KeyError) as e:
            print("Aviso: não foi possível migrar os dados antigos:", e)
            sistema.reiniciar()

def salvar():
    banco.salvar(sistema)

def executar(acao, mensagem=None):
    with trava:
        try:
            resultado = acao()
        except SigaeError as e:
            flash(str(e), "erro")
            return None
        salvar()
    if mensagem:
        flash(mensagem(resultado) if callable(mensagem) else mensagem, "ok")
    return resultado


def voltar(padrao="painel"):
    destino = request.form.get("voltar") or request.args.get("voltar")
    if destino and destino.startswith("/") and not destino.startswith("//"):
        return redirect(destino)
    return redirect(url_for(padrao))

@app.template_filter("hora")
def f_hora(ts):
    return "—" if ts is None else datetime.fromtimestamp(ts).strftime("%H:%M")

@app.template_filter("datahora")
def f_datahora(ts):
    if ts is None:
        return "—"
    d = datetime.fromtimestamp(ts)
    if d.date() == datetime.now().date():
        return d.strftime("%H:%M")
    return d.strftime("%d/%m %H:%M")

def _duracao(segundos):
    m = max(0, int(segundos // 60))
    return f"{m // 60}h {m % 60:02d}min" if m >= 60 else f"{m} min"

@app.template_filter("desde")
def f_desde(ts):
    return _duracao(time.time() - ts)

@app.template_filter("duracao")
def f_duracao(segundos):
    return "—" if segundos is None else _duracao(segundos)

app.jinja_env.globals.update(RISCOS=RISCOS, TEMPO_ALVO=TEMPO_ALVO, s=sistema)

@app.context_processor
def globais():
    return {"menu": sistema.indicadores(), "agora": datetime.now().strftime("%H:%M")}

@app.get("/")
def painel():
    paciente, medico = sistema.previa_chamada()
    return render_template("painel.html", tela="painel", ind=sistema.indicadores(),
                           fila=sistema.ordem_da_fila(), ativos=sistema.atendimentos_ativos(),
                           prox_paciente=paciente, prox_medico=medico, auto_atualizar=True)

@app.get("/pacientes")
def pacientes():
    filtro = request.args.get("filtro", "Todos")
    lista = [p for p in sistema.pacientes_ativos() if filtro == "Todos" or p.situacao == filtro]
    lista.reverse()
    return render_template("pacientes.html", tela="pacientes", lista=lista, filtro=filtro,
                           agora_campo=datetime.now().strftime("%Y-%m-%dT%H:%M"))

@app.post("/pacientes")
def cadastrar_paciente():
    chegada = None
    texto = (request.form.get("chegada") or "").strip()
    if texto:
        try:
            chegada = datetime.strptime(texto, "%Y-%m-%dT%H:%M").timestamp()
        except ValueError:
            flash("Horário de chegada inválido.", "erro")
            return redirect(url_for("pacientes"))
    executar(lambda: sistema.cadastrar_paciente(request.form.get("nome"), request.form.get("prioridade"), chegada),
             lambda p: f"{p.nome} cadastrado(a) com o nº {p.id}.")
    return redirect(url_for("pacientes"))


@app.get("/pacientes/<int:pid>")
def ver_paciente(pid):
    p = sistema.paciente(pid)
    if p is None:
        flash(f"Paciente nº {pid} não encontrado.", "erro")
        return redirect(url_for("pacientes"))
    return render_template("paciente.html", tela="pacientes", p=p,
                           posicao=sistema.posicao_na_fila(p.id), total_fila=len(sistema.fila_pacientes))

@app.get("/buscar")
def buscar():
    texto = (request.args.get("id") or "").strip().lstrip("#")
    if not texto.isdigit():
        flash("Digite o número do paciente.", "erro")
        return redirect(request.referrer or url_for("painel"))
    return redirect(url_for("ver_paciente", pid=int(texto)))

@app.post("/pacientes/<int:pid>/risco")
def reclassificar(pid):
    executar(lambda: sistema.reclassificar(pid, request.form.get("prioridade")),
             lambda p: f"{p.nome} agora é {p.risco}.")
    return voltar("fila")

@app.route("/pacientes/<int:pid>/cancelar", methods=["GET", "POST"])
def cancelar_paciente(pid):
    p = sistema.paciente(pid)
    if p is None:
        return redirect(url_for("pacientes"))
    if request.method == "POST":
        executar(lambda: sistema.cancelar_paciente(pid), f"Cadastro de {p.nome} cancelado.")
        return voltar("pacientes")
    return render_template("confirmar.html", tela="pacientes", titulo="Cancelar cadastro",
                           texto=f"Remover {p.nome} do atendimento?",
                           opcoes=[("Sim, cancelar cadastro", "", "red", "")],
                           acao=url_for("cancelar_paciente", pid=pid),
                           voltar_para=request.args.get("voltar") or url_for("pacientes"))

@app.get("/fila")
def fila():
    paciente, medico = sistema.previa_chamada()
    return render_template("fila.html", tela="fila", fila=sistema.ordem_da_fila(),
                           prox_paciente=paciente, prox_medico=medico)

@app.get("/medicos")
def medicos():
    return render_template("medicos.html", tela="medicos", lista=sistema.listar_medicos(),
                           registro_sugerido=f"CRM-SIM {random.randint(10000, 99999)}")

@app.post("/medicos")
def cadastrar_medico():
    executar(lambda: sistema.cadastrar_medico(request.form.get("nome"), request.form.get("registro")),
             lambda m: f"{m.nome} cadastrado(a).")
    return redirect(url_for("medicos"))

@app.get("/medicos/<int:mid>")
def ver_medico(mid):
    m = sistema.medico(mid)
    if m is None:
        return redirect(url_for("medicos"))
    return render_template("medico.html", tela="medicos", m=m)

@app.route("/medicos/<int:mid>/apagar", methods=["GET", "POST"])
def apagar_medico(mid):
    m = sistema.medico(mid)
    if m is None or m.removido:
        return redirect(url_for("medicos"))
    if request.method == "POST":
        executar(lambda: sistema.remover_medico(mid), f"{m.nome} foi apagado(a) da lista de médicos.")
        return redirect(url_for("medicos"))
    if m.situacao == "Em atendimento":
        flash(f"{m.nome} está atendendo. Conclua ou cancele o atendimento antes de apagar.", "erro")
        return redirect(url_for("medicos"))
    return render_template("confirmar.html", tela="medicos", titulo="Apagar médico",
                           texto=f"Apagar {m.nome} da lista de médicos? Ele(a) não receberá mais pacientes. "
                                 f"Os atendimentos que já fez continuam no Histórico.",
                           opcoes=[("Sim, apagar médico", "", "red", "")],
                           acao=url_for("apagar_medico", mid=mid), voltar_para=url_for("medicos"))

@app.get("/atendimentos")
def atendimentos():
    paciente, medico = sistema.previa_chamada()
    encerrados = [a for a in sistema.listar_atendimentos() if a.situacao != "Em atendimento"]
    encerrados.reverse()
    return render_template("atendimentos.html", tela="atendimentos", ativos=sistema.atendimentos_ativos(),
                           encerrados=encerrados[:15], prox_paciente=paciente, prox_medico=medico,
                           auto_atualizar=True)

@app.post("/chamar")
def chamar():
    executar(sistema.chamar_proximo, lambda r: f"{r[0].nome} foi chamado(a) para {r[1].nome}.")
    return voltar()

@app.post("/atendimentos/<int:aid>/concluir")
def concluir(aid):
    executar(lambda: sistema.concluir_atendimento(aid),
             lambda a: f"Atendimento de {sistema.paciente(a.paciente_id).nome} concluído.")
    return voltar()

@app.route("/atendimentos/<int:aid>/cancelar", methods=["GET", "POST"])
def cancelar_atendimento(aid):
    a = sistema.atendimento(aid)
    if a is None:
        return redirect(url_for("atendimentos"))
    if request.method == "POST":
        devolver = request.form.get("opcao") == "fila"
        executar(lambda: sistema.cancelar_atendimento(aid, devolver),
                 "Paciente devolvido à fila." if devolver else "Atendimento e cadastro cancelados.")
        return voltar("atendimentos")
    nome = sistema.paciente(a.paciente_id).nome
    return render_template("confirmar.html", tela="atendimentos", titulo="Cancelar atendimento",
                           texto=f"O que fazer com {nome}? O médico fica livre e o atendimento não é contado.",
                           opcoes=[("Devolver à fila", "O paciente volta a aguardar com a mesma prioridade", "soft", "fila"),
                                   ("Encerrar o cadastro", "O paciente sai do sistema como Cancelado", "red", "encerrar")],
                           acao=url_for("cancelar_atendimento", aid=aid),
                           voltar_para=request.args.get("voltar") or url_for("atendimentos"))

@app.get("/historico")
def historico():
    medicos_ = sistema.listar_medicos(incluir_removidos=True)
    maior = max([m.concluidos for m in medicos_] + [1])
    eventos = list(reversed(sistema.eventos))[:40]
    atendidos = [a for a in sistema.listar_atendimentos() if a.situacao == "Concluído"]
    atendidos.reverse()
    return render_template("historico.html", tela="historico", ind=sistema.indicadores(),
                           medicos=medicos_, maior=maior, chegadas=sistema.chegadas_cronologicas(),
                           eventos=eventos, atendidos=atendidos)

def _carregar_exemplo():
    sistema.reiniciar()
    agora = time.time()
    for nome, reg in (("Dra. Ana Albuquerque", "CRM-SIM 10001"), ("Dr. Bruno Barros", "CRM-SIM 10002"),
                      ("Dra. Carla Campos", "CRM-SIM 10003")):
        sistema.cadastrar_medico(nome, reg)
    for nome, min_atras, risco in (("João Souza", 42, 4), ("Maria Lima", 38, 2), ("Pedro Rocha", 31, 5),
                                   ("Luiza Dias", 27, 3), ("Carlos Neves", 27, 3), ("Beatriz Reis", 19, 1),
                                   ("Rafael Pinto", 12, 4), ("Sofia Melo", 6, 2)):
        sistema.cadastrar_paciente(nome, risco, agora - min_atras * 60)

@app.route("/exemplo", methods=["GET", "POST"])
def exemplo():
    if request.method == "POST" or (len(sistema.pacientes) == 0 and len(sistema.medicos) == 0):
        executar(_carregar_exemplo, "Exemplo carregado: 3 médicos e 8 pacientes.")
        return redirect(url_for("painel"))
    return render_template("confirmar.html", tela="", titulo="Carregar dados de exemplo?",
                           texto="Os dados atuais serão substituídos.",
                           opcoes=[("Sim, carregar exemplo", "", "", "")],
                           acao=url_for("exemplo"), voltar_para=url_for("painel"))

@app.route("/limpar", methods=["GET", "POST"])
def limpar():
    if request.method == "POST":
        executar(sistema.reiniciar, "Sistema limpo.")
        return redirect(url_for("painel"))
    return render_template("confirmar.html", tela="", titulo="Limpar tudo?",
                           texto="Todos os pacientes, médicos e atendimentos serão apagados.",
                           opcoes=[("Sim, apagar tudo", "", "red", "")],
                           acao=url_for("limpar"), voltar_para=url_for("painel"))

carregar()

if __name__ == "__main__":
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    print("SIGAE WEB ligado em http://localhost:5000")
    print("Deixe esta janela aberta (pode minimizar). Para desligar, feche-a ou aperte Ctrl+C.", flush=True)
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=False, threaded=True)
