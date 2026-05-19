import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import pandas as pd
import json
import os
from datetime import datetime

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="Bar do Querido", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    iframe { border: none !important; }
    body { background-color: #080b12 !important; }
</style>
""", unsafe_allow_html=True)

# ─── DATABASE ─────────────────────────────────────────────────────────────────
# Usa /tmp para garantir escrita no Streamlit Cloud
DB = os.path.join("/tmp", "bar_querido.db")

def get_conn():
    return sqlite3.connect(DB, check_same_thread=False)

def run_query(query, params=()):
    conn = get_conn()
    try:
        conn.execute(query, params)
        conn.commit()
    finally:
        conn.close()

def fetch_df(query, params=()):
    conn = get_conn()
    try:
        df = pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()
    return df

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        preco REAL NOT NULL DEFAULT 0,
        categoria TEXT DEFAULT 'Outro',
        frio_unid INTEGER DEFAULT 0,
        quent_caixas INTEGER DEFAULT 0,
        un_por_caixa INTEGER DEFAULT 1,
        ativo INTEGER DEFAULT 1
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        telefone TEXT DEFAULT '',
        observacao TEXT DEFAULT '',
        criado_em TEXT DEFAULT (datetime('now','localtime')),
        ativo INTEGER DEFAULT 1
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS consumos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER,
        produto_id INTEGER,
        produto_nome TEXT DEFAULT '',
        produto_preco REAL DEFAULT 0,
        qtd INTEGER DEFAULT 1,
        total REAL DEFAULT 0,
        tipo TEXT DEFAULT 'A_VISTA',
        pago INTEGER DEFAULT 0,
        data TEXT DEFAULT (datetime('now','localtime')),
        observacao TEXT DEFAULT ''
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS pagamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER,
        valor REAL DEFAULT 0,
        data TEXT DEFAULT (datetime('now','localtime')),
        observacao TEXT DEFAULT ''
    )""")
    c.execute("SELECT COUNT(*) FROM produtos")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO produtos(nome,preco,categoria,frio_unid,quent_caixas,un_por_caixa) VALUES(?,?,?,?,?,?)", [
            ('Brahma Duplo Malte 350ml', 6.00, 'Cerveja', 48, 12, 24),
            ('Heineken Long Neck 330ml', 10.00, 'Cerveja', 24, 8, 12),
            ('Skol Lata 350ml', 5.00, 'Cerveja', 36, 10, 24),
            ('Coca-Cola Lata 350ml', 6.00, 'Refrigerante', 24, 4, 12),
            ('Coca-Cola Zero Lata', 6.00, 'Refrigerante', 18, 2, 12),
            ('Agua Mineral 500ml', 3.00, 'Agua', 30, 5, 12),
            ('Amendoim Mendorato 120g', 6.00, 'Salgados', 0, 20, 1),
            ('Porcao de Frango', 8.00, 'Porcoes', 0, 10, 1),
        ])
        c.executemany("INSERT INTO clientes(nome,telefone) VALUES(?,?)", [
            ('Marcao Engenharia', '(43) 99999-0001'),
            ('Carlos Silva - Ficha 14', '(43) 99999-0002'),
        ])
        c.execute("INSERT INTO consumos(cliente_id,produto_id,produto_nome,produto_preco,qtd,total,tipo,pago,data) VALUES(2,1,'Brahma Duplo Malte 350ml',6.00,4,24.00,'FIADO',0,'2025-06-10 21:00:00')")
        c.execute("INSERT INTO consumos(cliente_id,produto_id,produto_nome,produto_preco,qtd,total,tipo,pago,data) VALUES(2,4,'Coca-Cola Lata 350ml',6.00,2,12.00,'FIADO',0,'2025-06-12 20:30:00')")
        c.execute("INSERT INTO consumos(cliente_id,produto_id,produto_nome,produto_preco,qtd,total,tipo,pago,data) VALUES(1,2,'Heineken Long Neck 330ml',10.00,3,30.00,'FIADO',0,'2025-06-13 22:00:00')")
    conn.commit()
    conn.close()

init_db()

# ─── HANDLE ACTIONS ───────────────────────────────────────────────────────────
qp = st.query_params

if "acao" in qp:
    try:
        acao = str(qp.get("acao", ""))

        if acao == "lancar_consumo":
            p_id  = int(qp.get("produto_id", 0))
            qtd   = int(qp.get("qtd", 1))
            c_id  = str(qp.get("cliente_id", "AVULSO"))
            obs   = str(qp.get("obs", ""))
            tipo  = str(qp.get("tipo", "A_VISTA"))
            p = fetch_df("SELECT * FROM produtos WHERE id=?", (p_id,))
            if not p.empty:
                nome_p  = str(p.iloc[0]['nome'])
                preco_p = float(p.iloc[0]['preco'])
                total   = preco_p * qtd
                run_query("UPDATE produtos SET frio_unid = MAX(0, frio_unid - ?) WHERE id=?", (qtd, p_id))
                if c_id != "AVULSO":
                    run_query("INSERT INTO consumos(cliente_id,produto_id,produto_nome,produto_preco,qtd,total,tipo,pago,observacao) VALUES(?,?,?,?,?,?,'FIADO',0,?)",
                        (int(c_id), p_id, nome_p, preco_p, qtd, total, obs))
                else:
                    run_query("INSERT INTO consumos(cliente_id,produto_id,produto_nome,produto_preco,qtd,total,tipo,pago,observacao) VALUES(NULL,?,?,?,?,?,'A_VISTA',1,?)",
                        (p_id, nome_p, preco_p, qtd, total, obs))

        elif acao == "registrar_pagamento":
            c_id  = int(qp.get("cliente_id", 0))
            valor = float(qp.get("valor", 0))
            obs   = str(qp.get("obs", ""))
            if c_id and valor > 0:
                run_query("INSERT INTO pagamentos(cliente_id,valor,observacao) VALUES(?,?,?)", (c_id, valor, obs))
                pendentes = fetch_df("SELECT id, total FROM consumos WHERE cliente_id=? AND pago=0 ORDER BY data ASC", (c_id,))
                restante = valor
                for _, row in pendentes.iterrows():
                    if restante <= 0:
                        break
                    if float(row['total']) <= restante:
                        run_query("UPDATE consumos SET pago=1 WHERE id=?", (int(row['id']),))
                        restante -= float(row['total'])
                    else:
                        break

        elif acao == "cadastrar_cliente":
            nome = str(qp.get("nome", "")).strip()
            tel  = str(qp.get("tel", ""))
            obs  = str(qp.get("obs", ""))
            if nome:
                run_query("INSERT INTO clientes(nome,telefone,observacao) VALUES(?,?,?)", (nome, tel, obs))

        elif acao == "editar_cliente":
            c_id = int(qp.get("id", 0))
            nome = str(qp.get("nome", "")).strip()
            tel  = str(qp.get("tel", ""))
            obs  = str(qp.get("obs", ""))
            if c_id and nome:
                run_query("UPDATE clientes SET nome=?,telefone=?,observacao=? WHERE id=?", (nome, tel, obs, c_id))

        elif acao == "arquivar_cliente":
            c_id = int(qp.get("id", 0))
            if c_id:
                run_query("UPDATE clientes SET ativo=0 WHERE id=?", (c_id,))

        elif acao == "cadastrar_produto":
            nome  = str(qp.get("nome", ""))
            preco = float(qp.get("preco", 0))
            cat   = str(qp.get("cat", "Outro"))
            frio  = int(qp.get("frio", 0))
            quent = int(qp.get("quent", 0))
            un_cx = int(qp.get("un_cx", 1))
            if nome:
                run_query("INSERT INTO produtos(nome,preco,categoria,frio_unid,quent_caixas,un_por_caixa) VALUES(?,?,?,?,?,?)",
                    (nome, preco, cat, frio, quent, un_cx))

        elif acao == "editar_produto":
            pid   = int(qp.get("id", 0))
            nome  = str(qp.get("nome", ""))
            preco = float(qp.get("preco", 0))
            cat   = str(qp.get("cat", "Outro"))
            frio  = int(qp.get("frio", 0))
            quent = int(qp.get("quent", 0))
            un_cx = int(qp.get("un_cx", 1))
            if pid and nome:
                run_query("UPDATE produtos SET nome=?,preco=?,categoria=?,frio_unid=?,quent_caixas=?,un_por_caixa=? WHERE id=?",
                    (nome, preco, cat, frio, quent, un_cx, pid))

        elif acao == "excluir_produto":
            pid = int(qp.get("id", 0))
            if pid:
                run_query("UPDATE produtos SET ativo=0 WHERE id=?", (pid,))

        elif acao == "repor_estoque":
            pid   = int(qp.get("id", 0))
            frio  = int(qp.get("frio", 0))
            quent = int(qp.get("quent", 0))
            if pid:
                run_query("UPDATE produtos SET frio_unid=frio_unid+?, quent_caixas=quent_caixas+? WHERE id=?", (frio, quent, pid))

    except Exception as e:
        st.error(f"Erro ao processar ação '{qp.get('acao')}': {e}")

    st.query_params.clear()
    st.rerun()

# ─── LOAD DATA ────────────────────────────────────────────────────────────────
prods          = fetch_df("SELECT * FROM produtos WHERE ativo=1 ORDER BY categoria, nome")
clis           = fetch_df("SELECT * FROM clientes WHERE ativo=1 ORDER BY nome")
historico_raw  = fetch_df("SELECT id as consumo_id, cliente_id, produto_nome, produto_preco, qtd, total, tipo, pago, data, observacao FROM consumos ORDER BY data DESC")
pagamentos_raw = fetch_df("SELECT id, cliente_id, valor, data, observacao FROM pagamentos ORDER BY data DESC")

# Saldo devedor calculado em Python
def saldo_devedor(cid, hist_df):
    if hist_df.empty:
        return 0.0
    mask = (hist_df['cliente_id'] == cid) & (hist_df['tipo'] == 'FIADO') & (hist_df['pago'] == 0)
    return float(hist_df.loc[mask, 'total'].sum())

clis_com_saldo = clis.copy()
clis_com_saldo['devendo'] = clis_com_saldo['id'].apply(lambda x: saldo_devedor(x, historico_raw))

def to_json(df):
    """Serializa DataFrame para JSON JavaScript-safe."""
    records = []
    for row in df.to_dict(orient='records'):
        clean = {}
        for k, v in row.items():
            if pd.isna(v) if not isinstance(v, (list, dict)) else False:
                clean[k] = None
            elif hasattr(v, 'item'):
                clean[k] = v.item()
            else:
                clean[k] = v
        records.append(clean)
    return json.dumps(records, ensure_ascii=False, default=str)

prods_json      = to_json(prods)
clis_json       = to_json(clis_com_saldo)
historico_json  = to_json(historico_raw)
pagamentos_json = to_json(pagamentos_raw)

# ─── HTML UI ──────────────────────────────────────────────────────────────────
HTML = r"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bar do Querido</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
<style>
:root {
    --bg:#080b12;--surface:#0d1220;--surface2:#111827;--border:rgba(255,255,255,0.06);
    --border2:rgba(255,255,255,0.10);--text:#e2e8f0;--muted:#64748b;--muted2:#94a3b8;
    --gold:#f59e0b;--gold2:#fbbf24;--green:#10b981;--cyan:#06b6d4;--red:#ef4444;--amber:#f59e0b;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;overflow:hidden;background:var(--bg);color:var(--text);font-family:'DM Sans',sans-serif;font-size:14px}
::-webkit-scrollbar{width:4px;height:4px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:2px}
.shell{display:flex;height:100vh;overflow:hidden}
.sidebar{width:240px;min-width:240px;background:var(--surface);border-right:1px solid var(--border);display:flex;flex-direction:column;padding:20px 0}
.brand{padding:0 20px 24px;border-bottom:1px solid var(--border)}
.brand-logo{width:44px;height:44px;border-radius:12px;background:linear-gradient(135deg,#b45309,#f59e0b);display:flex;align-items:center;justify-content:center;font-size:20px;margin-bottom:10px;box-shadow:0 0 24px rgba(245,158,11,0.3)}
.brand-name{font-family:'Syne',sans-serif;font-weight:800;font-size:16px;color:#fff;line-height:1.2}
.brand-sub{font-size:10px;color:var(--gold);letter-spacing:.12em;text-transform:uppercase;margin-top:2px}
.nav{flex:1;padding:16px 10px;overflow-y:auto}
.nav-sec{font-size:9px;font-weight:600;color:var(--muted);letter-spacing:.12em;text-transform:uppercase;padding:0 10px 8px;margin-top:16px}
.nav-btn{width:100%;display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:10px;border:none;cursor:pointer;background:transparent;color:var(--muted2);font-family:'DM Sans',sans-serif;font-size:13px;font-weight:500;text-align:left;transition:.2s}
.nav-btn:hover{background:rgba(255,255,255,0.04);color:var(--text)}
.nav-btn.active{background:rgba(245,158,11,0.1);color:var(--gold2);border:1px solid rgba(245,158,11,0.2)}
.nav-icon{width:28px;height:28px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:12px}
.nav-btn.active .nav-icon{background:rgba(245,158,11,0.15)}
.nav-badge{margin-left:auto;background:var(--red);color:#fff;font-size:10px;font-weight:700;padding:2px 6px;border-radius:20px;display:none}
.sidebar-footer{padding:16px 20px;border-top:1px solid var(--border)}
.clock{font-size:11px;color:var(--muted);text-align:center}
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.topbar{height:60px;min-height:60px;background:var(--surface);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;padding:0 28px}
.topbar-title{font-family:'Syne',sans-serif;font-weight:700;font-size:18px;color:#fff}
.topbar-sub{font-size:11px;color:var(--muted);margin-top:1px}
.content{flex:1;overflow-y:auto;padding:24px 28px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:20px}
.card-title{font-family:'Syne',sans-serif;font-weight:700;font-size:12px;color:var(--text);letter-spacing:.06em;text-transform:uppercase;margin-bottom:16px;display:flex;align-items:center;gap:8px}
.dot{width:6px;height:6px;border-radius:50%;display:inline-block;flex-shrink:0}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:24px}
.stat{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:16px 18px;position:relative;overflow:hidden}
.stat::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;border-radius:2px 2px 0 0}
.stat.gold::before{background:linear-gradient(90deg,#b45309,#f59e0b)}
.stat.green::before{background:linear-gradient(90deg,#059669,#10b981)}
.stat.cyan::before{background:linear-gradient(90deg,#0891b2,#06b6d4)}
.stat.red::before{background:linear-gradient(90deg,#dc2626,#ef4444)}
.stat-lbl{font-size:10px;font-weight:600;color:var(--muted);letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px}
.stat-val{font-family:'Syne',sans-serif;font-weight:800;font-size:22px;color:#fff}
.stat-sub{font-size:11px;color:var(--muted);margin-top:3px}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.fg{display:flex;flex-direction:column;gap:14px}
.form-group{display:flex;flex-direction:column;gap:6px}
.form-label{font-size:10px;font-weight:700;color:var(--muted);letter-spacing:.1em;text-transform:uppercase}
.fc{width:100%;background:var(--bg);border:1px solid var(--border2);border-radius:10px;padding:10px 14px;color:var(--text);font-family:'DM Sans',sans-serif;font-size:13px;transition:.2s;outline:none}
.fc:focus{border-color:var(--gold);box-shadow:0 0 0 3px rgba(245,158,11,0.1)}
select.fc option{background:var(--surface2);color:var(--text)}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;padding:10px 18px;border-radius:10px;border:none;cursor:pointer;font-family:'DM Sans',sans-serif;font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;transition:.2s;white-space:nowrap}
.btn-gold{background:linear-gradient(135deg,#b45309,#f59e0b);color:#000;box-shadow:0 4px 16px rgba(245,158,11,0.25)}
.btn-gold:hover{box-shadow:0 4px 24px rgba(245,158,11,0.45);transform:translateY(-1px)}
.btn-green{background:linear-gradient(135deg,#059669,#10b981);color:#000}
.btn-green:hover{box-shadow:0 4px 20px rgba(16,185,129,0.35);transform:translateY(-1px)}
.btn-cyan{background:linear-gradient(135deg,#0891b2,#06b6d4);color:#000}
.btn-ghost{background:rgba(255,255,255,0.04);color:var(--muted2);border:1px solid var(--border)}
.btn-ghost:hover{background:rgba(255,255,255,0.07);color:var(--text)}
.btn-red{background:rgba(239,68,68,0.1);color:var(--red);border:1px solid rgba(239,68,68,0.2)}
.btn-red:hover{background:rgba(239,68,68,0.2)}
.btn-full{width:100%}
.btn-sm{padding:7px 14px;font-size:11px;border-radius:8px}
.btn-xs{padding:4px 8px;font-size:10px;border-radius:6px}
table{width:100%;border-collapse:collapse}
thead tr{border-bottom:1px solid var(--border)}
thead th{padding:10px 14px;font-size:9px;font-weight:700;color:var(--muted);letter-spacing:.12em;text-transform:uppercase;text-align:left;white-space:nowrap}
tbody tr{border-bottom:1px solid rgba(255,255,255,0.03);transition:.15s}
tbody tr:hover{background:rgba(255,255,255,0.02)}
tbody td{padding:11px 14px;font-size:13px;color:var(--muted2)}
td.b{font-weight:600;color:var(--text)}
td.go{color:var(--gold2);font-weight:700}
td.gr{color:var(--green);font-weight:700}
td.re{color:var(--red);font-weight:700}
.badge{display:inline-flex;align-items:center;padding:3px 8px;border-radius:20px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.06em}
.bg{background:rgba(16,185,129,0.12);color:var(--green);border:1px solid rgba(16,185,129,0.2)}
.br{background:rgba(239,68,68,0.1);color:var(--red);border:1px solid rgba(239,68,68,0.2)}
.bo{background:rgba(245,158,11,0.1);color:var(--gold2);border:1px solid rgba(245,158,11,0.2)}
.bc{background:rgba(6,182,212,0.1);color:var(--cyan);border:1px solid rgba(6,182,212,0.2)}
.bz{background:rgba(100,116,139,0.1);color:var(--muted2);border:1px solid rgba(100,116,139,0.2)}
.cli-card{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:16px;cursor:pointer;transition:.2s;display:flex;align-items:center;gap:12px}
.cli-card:hover{border-color:rgba(245,158,11,0.3)}
.cli-card.debt{border-left:3px solid var(--amber)}
.cli-av{width:42px;height:42px;border-radius:12px;background:linear-gradient(135deg,#1e293b,#334155);display:flex;align-items:center;justify-content:center;font-family:'Syne',sans-serif;font-weight:800;font-size:16px;color:var(--gold2);flex-shrink:0}
.modal-ov{position:fixed;inset:0;background:rgba(0,0,0,0.75);backdrop-filter:blur(6px);z-index:1000;display:flex;align-items:center;justify-content:center;opacity:0;pointer-events:none;transition:.2s}
.modal-ov.open{opacity:1;pointer-events:all}
.modal{background:var(--surface2);border:1px solid var(--border2);border-radius:20px;width:560px;max-width:92vw;max-height:88vh;overflow-y:auto;padding:28px;transform:translateY(20px);transition:.25s}
.modal-ov.open .modal{transform:translateY(0)}
.modal-hd{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:20px}
.modal-title{font-family:'Syne',sans-serif;font-weight:700;font-size:18px;color:#fff}
.modal-x{background:rgba(255,255,255,0.06);border:1px solid var(--border);color:var(--muted2);width:30px;height:30px;border-radius:8px;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:14px}
.modal-x:hover{background:rgba(255,255,255,0.12);color:#fff}
.screen{display:none}
.screen.active{display:block}
.tab-bar{display:flex;gap:4px;margin-bottom:20px;background:rgba(0,0,0,0.3);padding:4px;border-radius:12px;width:fit-content}
.tab{padding:8px 16px;border-radius:9px;border:none;cursor:pointer;font-family:'DM Sans',sans-serif;font-size:12px;font-weight:600;color:var(--muted);background:transparent;transition:.2s}
.tab.active{background:var(--surface2);color:var(--text);box-shadow:0 1px 4px rgba(0,0,0,0.3)}
.sbar{height:4px;border-radius:2px;background:rgba(255,255,255,0.06);overflow:hidden;margin-top:4px}
.sfill{height:100%;border-radius:2px}
.empty{text-align:center;padding:32px;color:var(--muted)}
.toast-area{position:fixed;bottom:24px;right:24px;z-index:2000;display:flex;flex-direction:column;gap:8px}
.toast{background:var(--surface2);border:1px solid var(--border2);border-radius:12px;padding:12px 16px;min-width:240px;display:flex;align-items:center;gap:10px;box-shadow:0 8px 32px rgba(0,0,0,0.4);animation:slin .3s ease;font-size:13px;color:var(--text)}
.toast.green{border-left:3px solid var(--green)}
.toast.red{border-left:3px solid var(--red)}
@keyframes slin{from{transform:translateX(40px);opacity:0}to{transform:none;opacity:1}}
.hr{border:none;border-top:1px solid var(--border);margin:16px 0}
.ovx{overflow-x:auto}
.search-w{position:relative;margin-bottom:16px}
.search-w input{padding-left:36px}
.search-i{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--muted);font-size:12px}
</style>
</head>
<body>
<div class="shell">
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-logo">&#127866;</div>
      <div class="brand-name">Bar do Querido</div>
      <div class="brand-sub">Sistema de Gestao</div>
    </div>
    <nav class="nav">
      <div class="nav-sec">Principal</div>
      <button class="nav-btn active" id="nav-balcao" onclick="setScr('balcao')">
        <span class="nav-icon"><i class="fa-solid fa-receipt"></i></span> Balcao
      </button>
      <button class="nav-btn" id="nav-fichas" onclick="setScr('fichas')">
        <span class="nav-icon"><i class="fa-solid fa-users"></i></span> Fichas
        <span class="nav-badge" id="badge-fichas">0</span>
      </button>
      <div class="nav-sec">Gestao</div>
      <button class="nav-btn" id="nav-estoque" onclick="setScr('estoque')">
        <span class="nav-icon"><i class="fa-solid fa-boxes-stacked"></i></span> Estoque
      </button>
      <button class="nav-btn" id="nav-relatorio" onclick="setScr('relatorio')">
        <span class="nav-icon"><i class="fa-solid fa-chart-bar"></i></span> Relatorio
      </button>
    </nav>
    <div class="sidebar-footer">
      <div class="clock" id="clk">--/--/---- --:--:--</div>
    </div>
  </aside>

  <main class="main">
    <div class="topbar">
      <div>
        <div class="topbar-title" id="scr-title">Balcao de Vendas</div>
        <div class="topbar-sub" id="scr-sub">Terminal de operacoes integrado</div>
      </div>
      <button class="btn btn-ghost btn-sm" onclick="setScr('balcao')"><i class="fa-solid fa-plus"></i> Novo Consumo</button>
    </div>
    <div class="content">

      <!-- BALCAO -->
      <div class="screen active" id="scr-balcao">
        <div class="stats" id="stats-balcao"></div>
        <div class="g2" style="align-items:start">
          <div class="card">
            <div class="card-title"><span class="dot" style="background:var(--gold)"></span>Lancar Consumo</div>
            <div class="fg">
              <div style="display:flex;gap:8px">
                <button class="btn btn-gold" id="btn-avista" onclick="setTipo('A_VISTA')" style="flex:1">&#128181; A Vista</button>
                <button class="btn btn-ghost" id="btn-fiado" onclick="setTipo('FIADO')" style="flex:1">&#128203; Fiado</button>
              </div>
              <div class="form-group" id="grp-cli" style="display:none">
                <label class="form-label">Ficha do Cliente</label>
                <select class="fc" id="v-cli"></select>
              </div>
              <div class="form-group">
                <label class="form-label">Produto</label>
                <select class="fc" id="v-prod" onchange="prevVenda()"></select>
              </div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
                <div class="form-group">
                  <label class="form-label">Quantidade</label>
                  <input class="fc" type="number" id="v-qtd" value="1" min="1" oninput="prevVenda()">
                </div>
                <div class="form-group">
                  <label class="form-label">Observacao</label>
                  <input class="fc" type="text" id="v-obs" placeholder="Opcional...">
                </div>
              </div>
              <div id="v-prev" style="background:rgba(245,158,11,0.06);border:1px solid rgba(245,158,11,0.15);border-radius:10px;padding:12px;display:none">
                <div style="font-size:10px;color:var(--muted);margin-bottom:4px">TOTAL</div>
                <div style="font-family:'Syne',sans-serif;font-size:24px;font-weight:800;color:var(--gold2)" id="v-total">R$ 0,00</div>
              </div>
              <button class="btn btn-gold btn-full" onclick="confirmarVenda()"><i class="fa-solid fa-check-circle"></i> Confirmar Operacao</button>
            </div>
          </div>
          <div class="card">
            <div class="card-title"><span class="dot" style="background:var(--cyan)"></span>Ultimas Operacoes</div>
            <div class="ovx"><table><thead><tr><th>Item</th><th>Qtd</th><th>Total</th><th>Tipo</th><th>Data</th></tr></thead><tbody id="tb-rec"></tbody></table></div>
          </div>
        </div>
      </div>

      <!-- FICHAS -->
      <div class="screen" id="scr-fichas">
        <div style="display:flex;justify-content:flex-end;margin-bottom:20px">
          <button class="btn btn-gold" onclick="openMod('mod-nc')"><i class="fa-solid fa-user-plus"></i> Nova Ficha</button>
        </div>
        <div class="search-w">
          <i class="fa-solid fa-magnifying-glass search-i"></i>
          <input class="fc" id="srch-cli" type="text" placeholder="Buscar cliente..." oninput="filtCli()">
        </div>
        <div id="lista-cli" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px"></div>
      </div>

      <!-- ESTOQUE -->
      <div class="screen" id="scr-estoque">
        <div class="tab-bar">
          <button class="tab active" id="t-cat" onclick="setEtab('cat')">Catalogo</button>
          <button class="tab" id="t-rep" onclick="setEtab('rep')">Reposicao</button>
          <button class="tab" id="t-new" onclick="setEtab('new')">Novo Produto</button>
        </div>
        <div id="et-cat">
          <div class="search-w"><i class="fa-solid fa-magnifying-glass search-i"></i><input class="fc" id="srch-prod" type="text" placeholder="Buscar produto..." oninput="filtProd()"></div>
          <div class="card"><div class="ovx"><table><thead><tr><th>Produto</th><th>Cat.</th><th>Preco</th><th>Frio (un)</th><th>Quente (cx)</th><th>Total un</th><th>Acoes</th></tr></thead><tbody id="tb-est"></tbody></table></div></div>
        </div>
        <div id="et-rep" style="display:none">
          <div class="card" style="margin-bottom:16px">
            <div class="card-title"><span class="dot" style="background:var(--cyan)"></span>Repor Estoque</div>
            <div style="display:grid;grid-template-columns:2fr 1fr 1fr auto;gap:12px;align-items:end">
              <div class="form-group"><label class="form-label">Produto</label><select class="fc" id="rep-prod"></select></div>
              <div class="form-group"><label class="form-label">+ Gelando (un)</label><input class="fc" type="number" id="rep-frio" value="0" min="0"></div>
              <div class="form-group"><label class="form-label">+ Quente (cx)</label><input class="fc" type="number" id="rep-quent" value="0" min="0"></div>
              <button class="btn btn-cyan" onclick="reporEst()"><i class="fa-solid fa-plus"></i> Repor</button>
            </div>
          </div>
          <div class="card"><div class="card-title"><span class="dot" style="background:var(--amber)"></span>Nivel dos Estoques</div><div id="nivel-est"></div></div>
        </div>
        <div id="et-new" style="display:none">
          <div class="card">
            <div class="card-title" id="fp-title"><span class="dot" style="background:var(--gold)"></span>Novo Produto</div>
            <input type="hidden" id="pe-id">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
              <div class="form-group"><label class="form-label">Nome do Produto</label><input class="fc" id="pe-nome" type="text" placeholder="Ex: Heineken 600ml"></div>
              <div class="form-group"><label class="form-label">Preco de Venda (R$)</label><input class="fc" id="pe-preco" type="number" step="0.01" min="0" placeholder="0.00"></div>
              <div class="form-group"><label class="form-label">Categoria</label><select class="fc" id="pe-cat"><option>Cerveja</option><option>Refrigerante</option><option>Agua</option><option>Porcoes</option><option>Salgados</option><option>Doces</option><option>Outro</option></select></div>
              <div class="form-group"><label class="form-label">Un. por Caixa</label><input class="fc" id="pe-uncx" type="number" min="1" value="1"></div>
              <div class="form-group"><label class="form-label">Qtd. Gelando (un)</label><input class="fc" id="pe-frio" type="number" min="0" value="0"></div>
              <div class="form-group"><label class="form-label">Qtd. Deposito (cx)</label><input class="fc" id="pe-quent" type="number" min="0" value="0"></div>
            </div>
            <hr class="hr">
            <div style="display:flex;gap:10px">
              <button class="btn btn-gold btn-full" id="btn-sp" onclick="salvarProd()"><i class="fa-solid fa-floppy-disk"></i> Salvar Produto</button>
              <button class="btn btn-ghost btn-sm" id="btn-cp" style="display:none" onclick="cancelEditProd()">Cancelar</button>
            </div>
          </div>
        </div>
      </div>

      <!-- RELATORIO -->
      <div class="screen" id="scr-relatorio">
        <div class="stats" id="stats-rel"></div>
        <div class="g2" style="gap:20px;margin-bottom:20px">
          <div class="card"><div class="card-title"><span class="dot" style="background:var(--red)"></span>Maiores Devedores</div><div id="rank-dev"></div></div>
          <div class="card"><div class="card-title"><span class="dot" style="background:var(--cyan)"></span>Produtos Mais Vendidos</div><div id="rank-prod"></div></div>
        </div>
        <div class="card">
          <div class="card-title"><span class="dot" style="background:var(--green)"></span>Historico Global</div>
          <div class="ovx"><table><thead><tr><th>Data</th><th>Cliente</th><th>Produto</th><th>Qtd</th><th>Total</th><th>Tipo</th><th>Status</th></tr></thead><tbody id="tb-hglobal"></tbody></table></div>
        </div>
      </div>

    </div>
  </main>
</div>

<!-- MODAL: Novo Cliente -->
<div class="modal-ov" id="mod-nc">
  <div class="modal">
    <div class="modal-hd">
      <div class="modal-title">Nova Ficha de Cliente</div>
      <button class="modal-x" onclick="closeMod('mod-nc')"><i class="fa-solid fa-xmark"></i></button>
    </div>
    <div class="fg">
      <div class="form-group"><label class="form-label">Nome / Apelido</label><input class="fc" id="nc-nome" type="text" placeholder="Ex: Seu Joao do Posto"></div>
      <div class="form-group"><label class="form-label">Telefone (opcional)</label><input class="fc" id="nc-tel" type="text" placeholder="(43) 9XXXX-XXXX"></div>
      <div class="form-group"><label class="form-label">Observacao (opcional)</label><input class="fc" id="nc-obs" type="text" placeholder="Ex: Ficha n 12, amigo do Ze..."></div>
      <button class="btn btn-gold btn-full" onclick="cadastrarCli()"><i class="fa-solid fa-user-plus"></i> Abrir Ficha</button>
    </div>
  </div>
</div>

<!-- MODAL: Ficha -->
<div class="modal-ov" id="mod-ficha">
  <div class="modal" style="width:620px">
    <div class="modal-hd">
      <div>
        <div class="modal-title" id="f-nome">-</div>
        <div style="font-size:12px;color:var(--muted);margin-top:3px" id="f-meta">-</div>
      </div>
      <button class="modal-x" onclick="closeMod('mod-ficha')"><i class="fa-solid fa-xmark"></i></button>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:20px" id="f-stats"></div>
    <div style="background:rgba(16,185,129,0.06);border:1px solid rgba(16,185,129,0.15);border-radius:12px;padding:14px;margin-bottom:16px">
      <div style="font-size:11px;font-weight:700;color:var(--green);letter-spacing:.1em;text-transform:uppercase;margin-bottom:10px"><i class="fa-solid fa-hand-holding-dollar"></i> Registrar Pagamento</div>
      <div style="display:flex;gap:10px">
        <input class="fc" type="number" id="pg-val" placeholder="Valor R$" step="0.01" min="0.01" style="flex:1">
        <input class="fc" type="text" id="pg-obs" placeholder="Observacao" style="flex:1.5">
        <button class="btn btn-green" onclick="regPgto()"><i class="fa-solid fa-check"></i> Quitar</button>
      </div>
    </div>
    <div class="tab-bar">
      <button class="tab active" id="ft-cons" onclick="setFtab('cons')">Consumos</button>
      <button class="tab" id="ft-pgto" onclick="setFtab('pgto')">Pagamentos</button>
      <button class="tab" id="ft-edit" onclick="setFtab('edit')">Editar</button>
    </div>
    <div id="fc-cons">
      <div class="ovx" style="max-height:280px;overflow-y:auto"><table><thead><tr><th>Data</th><th>Produto</th><th>Qtd</th><th>Total</th><th>Status</th></tr></thead><tbody id="f-cons-bd"></tbody></table></div>
    </div>
    <div id="fc-pgto" style="display:none">
      <div class="ovx" style="max-height:280px;overflow-y:auto"><table><thead><tr><th>Data</th><th>Valor Pago</th><th>Obs</th></tr></thead><tbody id="f-pgto-bd"></tbody></table></div>
    </div>
    <div id="fc-edit" style="display:none">
      <div class="fg">
        <div class="form-group"><label class="form-label">Nome</label><input class="fc" id="ec-nome" type="text"></div>
        <div class="form-group"><label class="form-label">Telefone</label><input class="fc" id="ec-tel" type="text"></div>
        <div class="form-group"><label class="form-label">Observacao</label><input class="fc" id="ec-obs" type="text"></div>
        <div style="display:flex;gap:8px">
          <button class="btn btn-gold btn-full" onclick="salvarEditCli()"><i class="fa-solid fa-floppy-disk"></i> Salvar</button>
          <button class="btn btn-red btn-sm" onclick="arquivarCli()"><i class="fa-solid fa-archive"></i> Arquivar</button>
        </div>
      </div>
    </div>
  </div>
</div>

<div class="toast-area" id="toast-area"></div>

<script>
const produtos  = __PRODUTOS_JSON__;
const clientes  = __CLIENTES_JSON__;
const historico = __HISTORICO_JSON__;
const pagamentos= __PAGAMENTOS_JSON__;

let tipoVenda = 'A_VISTA';
let fichaId   = null;

const SCREENS = {
  balcao:   ['Balcao de Vendas','Terminal de operacoes integrado'],
  fichas:   ['Fichas e Clientes','Controle de fiado e historico'],
  estoque:  ['Gestao de Estoque','Catalogo, reposicao e inventario'],
  relatorio:['Relatorio Geral','Visao consolidada do negocio'],
};

function setScr(s, save=true) {
  document.querySelectorAll('.screen').forEach(e=>e.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(e=>e.classList.remove('active'));
  document.getElementById('scr-'+s).classList.add('active');
  document.getElementById('nav-'+s).classList.add('active');
  document.getElementById('scr-title').innerText = SCREENS[s][0];
  document.getElementById('scr-sub').innerText   = SCREENS[s][1];
  if(save){try{localStorage.setItem('bar_scr',s)}catch(e){}}
}

function nav(p){window.parent.location.search='?'+p}

function fM(v){return'R$ '+parseFloat(v||0).toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2})}
function fD(s){if(!s)return'-';const d=new Date((s+'').replace(' ','T'));return d.toLocaleDateString('pt-BR')+' '+d.toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'})}
function catIco(c){const m={'Cerveja':'&#127866;','Refrigerante':'&#129380;','Agua':'&#128167;','Porcoes':'&#127831;','Salgados':'&#129382;','Doces':'&#127852;'};return m[c]||'&#128230;'}
function devendo(cid){return historico.filter(h=>h.cliente_id==cid&&h.tipo==='FIADO'&&h.pago==0).reduce((s,h)=>s+h.total,0)}
function totalCons(cid){return historico.filter(h=>h.cliente_id==cid&&h.tipo==='FIADO').reduce((s,h)=>s+h.total,0)}
function totalPago(cid){return pagamentos.filter(p=>p.cliente_id==cid).reduce((s,p)=>s+p.valor,0)}

function openMod(id){document.getElementById(id).classList.add('open')}
function closeMod(id){document.getElementById(id).classList.remove('open')}
document.querySelectorAll('.modal-ov').forEach(el=>el.addEventListener('click',e=>{if(e.target===el)el.classList.remove('open')}));

function toast(msg,t='green'){
  const a=document.getElementById('toast-area');
  const el=document.createElement('div');
  el.className='toast '+t;
  el.innerHTML='<i class="fa-solid '+(t==='green'?'fa-check-circle':'fa-circle-exclamation')+'" style="color:var(--'+t+');font-size:16px"></i> '+msg;
  a.appendChild(el);
  setTimeout(()=>el.remove(),3500);
}

// ── SELECTS
function fillProdSel(id){
  const s=document.getElementById(id);if(!s)return;
  s.innerHTML='<option value="">-- Selecione --</option>';
  produtos.forEach(p=>{s.innerHTML+=`<option value="${p.id}">${catIco(p.categoria)} ${p.nome} -- ${fM(p.preco)} (${p.frio_unid} un)</option>`});
}
function fillCliSel(id){
  const s=document.getElementById(id);if(!s)return;
  s.innerHTML='<option value="AVULSO">-- Selecione o cliente --</option>';
  clientes.forEach(c=>{const d=devendo(c.id);s.innerHTML+=`<option value="${c.id}">&#128100; ${c.nome}${d>0?' -- deve '+fM(d):''}</option>`});
}

// ── BALCAO
function setTipo(t){
  tipoVenda=t;
  document.getElementById('btn-avista').className=t==='A_VISTA'?'btn btn-gold':'btn btn-ghost';
  document.getElementById('btn-fiado').className =t==='FIADO'  ?'btn btn-gold':'btn btn-ghost';
  document.getElementById('grp-cli').style.display=t==='FIADO'?'flex':'none';
  document.getElementById('grp-cli').style.flexDirection='column';
  document.getElementById('grp-cli').style.gap='6px';
}
function prevVenda(){
  const pId=parseInt(document.getElementById('v-prod').value);
  const qtd=parseInt(document.getElementById('v-qtd').value)||0;
  const p=produtos.find(x=>x.id===pId);
  const el=document.getElementById('v-prev');
  if(p&&qtd>0){document.getElementById('v-total').innerText=fM(p.preco*qtd);el.style.display='block'}
  else el.style.display='none';
}
function confirmarVenda(){
  const pId=document.getElementById('v-prod').value;
  const qtd=document.getElementById('v-qtd').value;
  const cId=tipoVenda==='FIADO'?document.getElementById('v-cli').value:'AVULSO';
  const obs=document.getElementById('v-obs').value;
  if(!pId)return toast('Selecione um produto!','red');
  if(tipoVenda==='FIADO'&&cId==='AVULSO')return toast('Selecione o cliente para fiado!','red');
  nav(`acao=lancar_consumo&produto_id=${pId}&qtd=${qtd}&cliente_id=${encodeURIComponent(cId)}&obs=${encodeURIComponent(obs)}&tipo=${tipoVenda}`);
}
function renderRecentes(){
  const tb=document.getElementById('tb-rec');
  const rec=[...historico].sort((a,b)=>b.consumo_id-a.consumo_id).slice(0,20);
  if(!rec.length){tb.innerHTML='<tr><td colspan="5" class="empty">Sem operacoes ainda</td></tr>';return}
  tb.innerHTML=rec.map(h=>`<tr>
    <td class="b">${h.produto_nome}</td>
    <td>${h.qtd}x</td>
    <td class="go">${fM(h.total)}</td>
    <td>${h.tipo==='FIADO'?'<span class="badge bo">Fiado</span>':'<span class="badge bg">A Vista</span>'}</td>
    <td style="font-size:11px;color:var(--muted)">${fD(h.data)}</td>
  </tr>`).join('');
  const tAV=historico.filter(h=>h.tipo==='A_VISTA').reduce((s,h)=>s+h.total,0);
  const tFi=historico.filter(h=>h.tipo==='FIADO'&&h.pago==0).reduce((s,h)=>s+h.total,0);
  const tTo=historico.reduce((s,h)=>s+h.total,0);
  document.getElementById('stats-balcao').innerHTML=`
    <div class="stat gold"><div class="stat-lbl">Caixa (A Vista)</div><div class="stat-val">${fM(tAV)}</div><div class="stat-sub">recebido</div></div>
    <div class="stat red"><div class="stat-lbl">Em Aberto (Fiado)</div><div class="stat-val">${fM(tFi)}</div><div class="stat-sub">pendente</div></div>
    <div class="stat green"><div class="stat-lbl">Faturamento Total</div><div class="stat-val">${fM(tTo)}</div><div class="stat-sub">historico</div></div>
    <div class="stat cyan"><div class="stat-lbl">Clientes Ativos</div><div class="stat-val">${clientes.length}</div><div class="stat-sub">fichas</div></div>`;
}

// ── FICHAS
function updBadge(){
  const n=clientes.filter(c=>devendo(c.id)>0).length;
  const b=document.getElementById('badge-fichas');
  b.style.display=n>0?'inline':'none';b.innerText=n;
}
function renderClis(f=''){
  const el=document.getElementById('lista-cli');
  const arr=clientes.filter(c=>c.nome.toLowerCase().includes(f.toLowerCase()));
  if(!arr.length){el.innerHTML='<div class="empty" style="grid-column:1/-1">Nenhum cliente encontrado</div>';return}
  el.innerHTML=arr.map(c=>{
    const d=devendo(c.id);
    return`<div class="cli-card${d>0?' debt':''}" onclick="abrirFicha(${c.id})">
      <div class="cli-av">${c.nome.charAt(0).toUpperCase()}</div>
      <div style="flex:1;min-width:0">
        <div style="font-weight:600;color:var(--text)">${c.nome}</div>
        <div style="font-size:11px;color:var(--muted);margin-top:2px">${c.telefone||'Sem telefone'}${c.observacao?' · '+c.observacao:''}</div>
      </div>
      <div style="text-align:right">
        <div style="font-family:'Syne',sans-serif;font-weight:800;font-size:15px;color:${d>0?'var(--gold2)':'var(--green)'}">${fM(d)}</div>
        <div style="font-size:10px;color:var(--muted)">${d>0?'Pendente':'Quitado'}</div>
      </div>
    </div>`}).join('');
}
function filtCli(){renderClis(document.getElementById('srch-cli').value)}
function abrirFicha(cid){
  fichaId=cid;
  const c=clientes.find(x=>x.id==cid);
  if(!c)return;
  const dev=devendo(cid),tc=totalCons(cid),tp=totalPago(cid);
  document.getElementById('f-nome').innerText=c.nome;
  document.getElementById('f-meta').innerText=(c.telefone||'Sem telefone')+(c.observacao?' · '+c.observacao:'');
  document.getElementById('f-stats').innerHTML=`
    <div class="stat red" style="padding:12px"><div class="stat-lbl">Em Aberto</div><div class="stat-val" style="font-size:18px">${fM(dev)}</div></div>
    <div class="stat gold" style="padding:12px"><div class="stat-lbl">Total Consumido</div><div class="stat-val" style="font-size:18px">${fM(tc)}</div></div>
    <div class="stat green" style="padding:12px"><div class="stat-lbl">Total Pago</div><div class="stat-val" style="font-size:18px">${fM(tp)}</div></div>`;
  const cons=historico.filter(h=>h.cliente_id==cid&&h.tipo==='FIADO').sort((a,b)=>b.consumo_id-a.consumo_id);
  document.getElementById('f-cons-bd').innerHTML=!cons.length
    ?'<tr><td colspan="5" class="empty">Sem consumos registrados</td></tr>'
    :cons.map(h=>`<tr>
      <td style="font-size:11px;color:var(--muted)">${fD(h.data)}</td>
      <td class="b">${h.produto_nome}</td>
      <td>${h.qtd}x</td>
      <td class="go">${fM(h.total)}</td>
      <td>${h.pago?'<span class="badge bg">Pago</span>':'<span class="badge br">Pendente</span>'}</td>
    </tr>`).join('');
  const pgts=pagamentos.filter(p=>p.cliente_id==cid).sort((a,b)=>b.id-a.id);
  document.getElementById('f-pgto-bd').innerHTML=!pgts.length
    ?'<tr><td colspan="3" class="empty">Sem pagamentos</td></tr>'
    :pgts.map(p=>`<tr>
      <td style="font-size:11px;color:var(--muted)">${fD(p.data)}</td>
      <td class="gr">${fM(p.valor)}</td>
      <td style="font-size:12px;color:var(--muted2)">${p.observacao||'-'}</td>
    </tr>`).join('');
  document.getElementById('ec-nome').value=c.nome;
  document.getElementById('ec-tel').value=c.telefone||'';
  document.getElementById('ec-obs').value=c.observacao||'';
  setFtab('cons');
  openMod('mod-ficha');
}
function setFtab(t){
  ['cons','pgto','edit'].forEach(x=>{
    document.getElementById('ft-'+x).classList.toggle('active',x===t);
    document.getElementById('fc-'+x).style.display=x===t?'block':'none';
  });
}
function cadastrarCli(){
  const n=document.getElementById('nc-nome').value.trim();
  if(!n)return toast('Digite o nome!','red');
  nav(`acao=cadastrar_cliente&nome=${encodeURIComponent(n)}&tel=${encodeURIComponent(document.getElementById('nc-tel').value)}&obs=${encodeURIComponent(document.getElementById('nc-obs').value)}`);
}
function salvarEditCli(){
  const n=document.getElementById('ec-nome').value.trim();
  if(!n||!fichaId)return toast('Nome invalido!','red');
  nav(`acao=editar_cliente&id=${fichaId}&nome=${encodeURIComponent(n)}&tel=${encodeURIComponent(document.getElementById('ec-tel').value)}&obs=${encodeURIComponent(document.getElementById('ec-obs').value)}`);
}
function arquivarCli(){
  if(!fichaId)return;
  if(confirm('Arquivar este cliente? O historico sera mantido.'))nav(`acao=arquivar_cliente&id=${fichaId}`);
}
function regPgto(){
  const v=parseFloat(document.getElementById('pg-val').value);
  const o=document.getElementById('pg-obs').value;
  if(!fichaId||!v||v<=0)return toast('Informe um valor valido!','red');
  nav(`acao=registrar_pagamento&cliente_id=${fichaId}&valor=${v}&obs=${encodeURIComponent(o)}`);
}

// ── ESTOQUE
function setEtab(t){
  ['cat','rep','new'].forEach(x=>{
    document.getElementById('et-'+x).style.display=x===t?'block':'none';
    document.getElementById('t-'+x).classList.toggle('active',x===t);
  });
}
function renderEst(f=''){
  const tb=document.getElementById('tb-est');
  const arr=produtos.filter(p=>p.nome.toLowerCase().includes(f.toLowerCase()));
  if(!arr.length){tb.innerHTML='<tr><td colspan="7" class="empty">Nenhum produto</td></tr>';return}
  tb.innerHTML=arr.map(p=>{
    const total=p.frio_unid+(p.quent_caixas*p.un_por_caixa);
    const alerta=p.frio_unid<6?'<span class="badge br" style="margin-left:6px">Baixo</span>':'';
    return`<tr>
      <td class="b">${catIco(p.categoria)} ${p.nome}${alerta}</td>
      <td><span class="badge bz">${p.categoria}</span></td>
      <td class="go">${fM(p.preco)}</td>
      <td><span class="badge bc">${p.frio_unid} un</span></td>
      <td style="font-size:12px;color:var(--muted)">${p.quent_caixas} cx (${p.un_por_caixa}/cx)</td>
      <td class="b">${total} un</td>
      <td style="white-space:nowrap">
        <button class="btn btn-ghost btn-xs" onclick="editProd(${p.id})" style="margin-right:4px"><i class="fa-solid fa-pen"></i></button>
        <button class="btn btn-red btn-xs" onclick="delProd(${p.id})"><i class="fa-solid fa-trash"></i></button>
      </td>
    </tr>`;}).join('');
}
function filtProd(){renderEst(document.getElementById('srch-prod').value)}
function renderNivel(){
  document.getElementById('nivel-est').innerHTML=produtos.map(p=>{
    const total=p.frio_unid+(p.quent_caixas*p.un_por_caixa);
    const pct=total>0?Math.min(100,(p.frio_unid/Math.max(total,1))*100):0;
    const cor=p.frio_unid<6?'var(--red)':p.frio_unid<12?'var(--amber)':'var(--green)';
    return`<div style="margin-bottom:12px">
      <div style="display:flex;justify-content:space-between;margin-bottom:4px">
        <span style="font-size:13px;color:var(--text)">${catIco(p.categoria)} ${p.nome}</span>
        <span style="font-size:12px;color:var(--muted2)">${p.frio_unid} frio / ${p.quent_caixas} cx</span>
      </div>
      <div class="sbar"><div class="sfill" style="width:${pct}%;background:${cor}"></div></div>
    </div>`;}).join('');
}
function editProd(id){
  const p=produtos.find(x=>x.id===id);if(!p)return;
  document.getElementById('pe-id').value=p.id;
  document.getElementById('pe-nome').value=p.nome;
  document.getElementById('pe-preco').value=p.preco;
  document.getElementById('pe-cat').value=p.categoria;
  document.getElementById('pe-frio').value=p.frio_unid;
  document.getElementById('pe-quent').value=p.quent_caixas;
  document.getElementById('pe-uncx').value=p.un_por_caixa;
  document.getElementById('fp-title').innerHTML='<span class="dot" style="background:var(--amber)"></span>Editar Produto';
  document.getElementById('btn-sp').innerHTML='<i class="fa-solid fa-floppy-disk"></i> Atualizar';
  document.getElementById('btn-cp').style.display='inline-flex';
  setEtab('new');
}
function cancelEditProd(){
  document.getElementById('pe-id').value='';
  document.getElementById('pe-nome').value='';
  document.getElementById('pe-preco').value='';
  document.getElementById('pe-frio').value='0';
  document.getElementById('pe-quent').value='0';
  document.getElementById('pe-uncx').value='1';
  document.getElementById('fp-title').innerHTML='<span class="dot" style="background:var(--gold)"></span>Novo Produto';
  document.getElementById('btn-sp').innerHTML='<i class="fa-solid fa-floppy-disk"></i> Salvar Produto';
  document.getElementById('btn-cp').style.display='none';
}
function salvarProd(){
  const id=document.getElementById('pe-id').value;
  const n=document.getElementById('pe-nome').value.trim();
  const pr=document.getElementById('pe-preco').value;
  const cat=document.getElementById('pe-cat').value;
  const fr=document.getElementById('pe-frio').value;
  const qu=document.getElementById('pe-quent').value;
  const ux=document.getElementById('pe-uncx').value;
  if(!n||!pr)return toast('Preencha Nome e Preco!','red');
  nav(`acao=${id?'editar_produto':'cadastrar_produto'}&id=${id}&nome=${encodeURIComponent(n)}&preco=${pr}&cat=${encodeURIComponent(cat)}&frio=${fr}&quent=${qu}&un_cx=${ux}`);
}
function delProd(id){if(confirm('Excluir este produto?'))nav(`acao=excluir_produto&id=${id}`)}
function reporEst(){
  const id=document.getElementById('rep-prod').value;
  const fr=document.getElementById('rep-frio').value;
  const qu=document.getElementById('rep-quent').value;
  if(!id)return toast('Selecione o produto!','red');
  nav(`acao=repor_estoque&id=${id}&frio=${fr}&quent=${qu}`);
}

// ── RELATORIO
function renderRel(){
  const tG=historico.reduce((s,h)=>s+h.total,0);
  const tAV=historico.filter(h=>h.tipo==='A_VISTA').reduce((s,h)=>s+h.total,0);
  const tRec=pagamentos.reduce((s,p)=>s+p.valor,0);
  const tAb=historico.filter(h=>h.tipo==='FIADO'&&h.pago==0).reduce((s,h)=>s+h.total,0);
  document.getElementById('stats-rel').innerHTML=`
    <div class="stat gold"><div class="stat-lbl">Faturamento Total</div><div class="stat-val">${fM(tG)}</div></div>
    <div class="stat green"><div class="stat-lbl">Recebido A Vista</div><div class="stat-val">${fM(tAV)}</div></div>
    <div class="stat cyan"><div class="stat-lbl">Pago nas Fichas</div><div class="stat-val">${fM(tRec)}</div></div>
    <div class="stat red"><div class="stat-lbl">Ainda em Aberto</div><div class="stat-val">${fM(tAb)}</div></div>`;
  const devs=clientes.map(c=>({n:c.nome,d:devendo(c.id)})).filter(x=>x.d>0).sort((a,b)=>b.d-a.d).slice(0,8);
  document.getElementById('rank-dev').innerHTML=!devs.length
    ?'<div class="empty">&#127881; Ninguem deve!</div>'
    :devs.map((d,i)=>`<div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04)">
        <span style="font-size:12px;color:var(--muted);width:18px">${i+1}.</span>
        <span style="flex:1;font-size:13px;color:var(--text);font-weight:500">${d.n}</span>
        <span style="font-family:'Syne',sans-serif;font-weight:700;color:var(--gold2)">${fM(d.d)}</span>
      </div>`).join('');
  const cnt={};historico.forEach(h=>{cnt[h.produto_nome]=(cnt[h.produto_nome]||0)+h.qtd});
  const rk=Object.entries(cnt).sort((a,b)=>b[1]-a[1]).slice(0,8);
  document.getElementById('rank-prod').innerHTML=!rk.length
    ?'<div class="empty">&#128230; Sem vendas ainda</div>'
    :rk.map(([n,q],i)=>`<div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04)">
        <span style="font-size:12px;color:var(--muted);width:18px">${i+1}.</span>
        <span style="flex:1;font-size:13px;color:var(--text);font-weight:500">${n}</span>
        <span class="badge bc">${q} un</span>
      </div>`).join('');
  document.getElementById('tb-hglobal').innerHTML=[...historico].sort((a,b)=>b.consumo_id-a.consumo_id).map(h=>{
    const c=clientes.find(x=>x.id==h.cliente_id);
    return`<tr>
      <td style="font-size:11px;color:var(--muted)">${fD(h.data)}</td>
      <td>${c?c.nome:'<span style="color:var(--muted)">Avulso</span>'}</td>
      <td class="b">${h.produto_nome}</td>
      <td>${h.qtd}x</td>
      <td class="go">${fM(h.total)}</td>
      <td>${h.tipo==='FIADO'?'<span class="badge bo">Fiado</span>':'<span class="badge bg">A Vista</span>'}</td>
      <td>${h.pago?'<span class="badge bg">Pago</span>':(h.tipo==='FIADO'?'<span class="badge br">Pendente</span>':'<span class="badge bg">OK</span>')}</td>
    </tr>`}).join('');
}

// ── INIT
function init(){
  fillProdSel('v-prod');fillProdSel('rep-prod');
  fillCliSel('v-cli');
  renderRecentes();
  renderClis();
  renderEst();
  renderNivel();
  renderRel();
  updBadge();
  let s='balcao';try{s=localStorage.getItem('bar_scr')||'balcao'}catch(e){}
  setScr(s,false);
  setInterval(()=>{const d=new Date();document.getElementById('clk').innerText=d.toLocaleDateString('pt-BR')+' - '+d.toLocaleTimeString('pt-BR')},1000);
}

init();
</script>
</body>
</html>
"""

html_final = (HTML
    .replace("__PRODUTOS_JSON__", prods_json)
    .replace("__CLIENTES_JSON__", clis_json)
    .replace("__HISTORICO_JSON__", historico_json)
    .replace("__PAGAMENTOS_JSON__", pagamentos_json)
)

components.html(html_final, height=950, scrolling=False)
