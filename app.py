import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import pandas as pd
import json
from datetime import datetime

# ─── PAGE CONFIG ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Bar do Querido",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    iframe { border: none !important; }
    body { background-color: #080b12 !important; }
</style>
""", unsafe_allow_html=True)

# ─── DATABASE ────────────────────────────────────────────────────────────────
DB = "bar_querido.db"

def get_conn():
    return sqlite3.connect(DB, check_same_thread=False)

def run(query, params=()):
    conn = get_conn()
    conn.execute(query, params)
    conn.commit()
    conn.close()

def fetch(query, params=()):
    conn = get_conn()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            preco REAL NOT NULL,
            categoria TEXT DEFAULT 'Outro',
            frio_unid INTEGER DEFAULT 0,
            quent_caixas INTEGER DEFAULT 0,
            un_por_caixa INTEGER DEFAULT 1,
            ativo INTEGER DEFAULT 1
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT DEFAULT '',
            observacao TEXT DEFAULT '',
            criado_em TEXT DEFAULT (datetime('now','localtime')),
            ativo INTEGER DEFAULT 1
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS consumos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            produto_id INTEGER,
            produto_nome TEXT,
            produto_preco REAL,
            qtd INTEGER,
            total REAL,
            tipo TEXT DEFAULT 'FIADO',
            pago INTEGER DEFAULT 0,
            data TEXT DEFAULT (datetime('now','localtime')),
            observacao TEXT DEFAULT '',
            FOREIGN KEY(cliente_id) REFERENCES clientes(id),
            FOREIGN KEY(produto_id) REFERENCES produtos(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS pagamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            valor REAL,
            data TEXT DEFAULT (datetime('now','localtime')),
            observacao TEXT DEFAULT '',
            FOREIGN KEY(cliente_id) REFERENCES clientes(id)
        )
    """)
    # seed data
    c.execute("SELECT COUNT(*) FROM produtos")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO produtos(nome,preco,categoria,frio_unid,quent_caixas,un_por_caixa) VALUES(?,?,?,?,?,?)", [
            ('Brahma Duplo Malte 350ml', 6.00, 'Cerveja', 48, 12, 24),
            ('Heineken Long Neck 330ml', 10.00, 'Cerveja', 24, 8, 12),
            ('Skol Lata 350ml', 5.00, 'Cerveja', 36, 10, 24),
            ('Coca-Cola Lata 350ml', 6.00, 'Refrigerante', 24, 4, 12),
            ('Coca-Cola Zero Lata', 6.00, 'Refrigerante', 18, 2, 12),
            ('Água Mineral 500ml', 3.00, 'Água', 30, 5, 12),
            ('Amendoim Mendorato 120g', 6.00, 'Salgados', 0, 20, 1),
            ('Danoninho Porção', 8.00, 'Porções', 0, 10, 1),
        ])
        c.executemany("INSERT INTO clientes(nome,telefone) VALUES(?,?)", [
            ('Marcão Engenharia', '(43) 99999-0001'),
            ('Carlos Silva — Ficha 14', '(43) 99999-0002'),
        ])
        # seed consumos para o Carlos
        c.execute("INSERT INTO consumos(cliente_id,produto_id,produto_nome,produto_preco,qtd,total,tipo,pago,data) VALUES(2,1,'Brahma Duplo Malte 350ml',6.00,4,24.00,'FIADO',0,'2025-06-10 21:00:00')")
        c.execute("INSERT INTO consumos(cliente_id,produto_id,produto_nome,produto_preco,qtd,total,tipo,pago,data) VALUES(2,4,'Coca-Cola Lata 350ml',6.00,2,12.00,'FIADO',0,'2025-06-12 20:30:00')")
        c.execute("INSERT INTO consumos(cliente_id,produto_id,produto_nome,produto_preco,qtd,total,tipo,pago,data) VALUES(1,2,'Heineken Long Neck 330ml',10.00,3,30.00,'FIADO',0,'2025-06-13 22:00:00')")
    conn.commit()
    conn.close()

init_db()

# ─── HANDLE ACTIONS FROM FRONT-END ───────────────────────────────────────────
qp = st.query_params

if "acao" in qp:
    acao = qp.get("acao", "")

    # ── LANÇAR CONSUMO
    if acao == "lancar_consumo":
        p_id   = int(qp.get("produto_id", 0))
        qtd    = int(qp.get("qtd", 1))
        c_id   = qp.get("cliente_id", "AVULSO")
        obs    = qp.get("obs", "")
        tipo   = qp.get("tipo", "A_VISTA")

        p = fetch("SELECT * FROM produtos WHERE id=?", (p_id,))
        if not p.empty:
            nome_p  = p.iloc[0]['nome']
            preco_p = float(p.iloc[0]['preco'])
            total   = preco_p * qtd
            run("UPDATE produtos SET frio_unid = MAX(0, frio_unid - ?) WHERE id=?", (qtd, p_id))
            if c_id != "AVULSO":
                run("INSERT INTO consumos(cliente_id,produto_id,produto_nome,produto_preco,qtd,total,tipo,pago,observacao) VALUES(?,?,?,?,?,?,'FIADO',0,?)",
                    (int(c_id), p_id, nome_p, preco_p, qtd, total, obs))
            else:
                run("INSERT INTO consumos(cliente_id,produto_id,produto_nome,produto_preco,qtd,total,tipo,pago,observacao) VALUES(NULL,?,?,?,?,?,'A_VISTA',1,?)",
                    (p_id, nome_p, preco_p, qtd, total, obs))

    # ── REGISTRAR PAGAMENTO
    elif acao == "registrar_pagamento":
        c_id  = int(qp.get("cliente_id", 0))
        valor = float(qp.get("valor", 0))
        obs   = qp.get("obs", "")
        if c_id and valor > 0:
            run("INSERT INTO pagamentos(cliente_id,valor,observacao) VALUES(?,?,?)", (c_id, valor, obs))
            # marca consumos como pagos até cobrir o valor
            pendentes = fetch("SELECT id, total FROM consumos WHERE cliente_id=? AND pago=0 ORDER BY data ASC", (c_id,))
            restante = valor
            for _, row in pendentes.iterrows():
                if restante <= 0:
                    break
                if row['total'] <= restante:
                    run("UPDATE consumos SET pago=1 WHERE id=?", (int(row['id']),))
                    restante -= row['total']
                else:
                    break

    # ── CADASTRAR CLIENTE
    elif acao == "cadastrar_cliente":
        nome = qp.get("nome", "").strip()
        tel  = qp.get("tel", "")
        obs  = qp.get("obs", "")
        if nome:
            run("INSERT INTO clientes(nome,telefone,observacao) VALUES(?,?,?)", (nome, tel, obs))

    # ── EDITAR CLIENTE
    elif acao == "editar_cliente":
        c_id = int(qp.get("id", 0))
        nome = qp.get("nome", "").strip()
        tel  = qp.get("tel", "")
        obs  = qp.get("obs", "")
        if c_id and nome:
            run("UPDATE clientes SET nome=?,telefone=?,observacao=? WHERE id=?", (nome, tel, obs, c_id))

    # ── ARQUIVAR CLIENTE
    elif acao == "arquivar_cliente":
        c_id = int(qp.get("id", 0))
        if c_id:
            run("UPDATE clientes SET ativo=0 WHERE id=?", (c_id,))

    # ── CADASTRAR PRODUTO
    elif acao == "cadastrar_produto":
        run("INSERT INTO produtos(nome,preco,categoria,frio_unid,quent_caixas,un_por_caixa) VALUES(?,?,?,?,?,?)", (
            qp.get("nome"), float(qp.get("preco", 0)),
            qp.get("cat", "Outro"),
            int(qp.get("frio", 0)), int(qp.get("quent", 0)), int(qp.get("un_cx", 1))
        ))

    # ── EDITAR PRODUTO
    elif acao == "editar_produto":
        run("UPDATE produtos SET nome=?,preco=?,categoria=?,frio_unid=?,quent_caixas=?,un_por_caixa=? WHERE id=?", (
            qp.get("nome"), float(qp.get("preco", 0)),
            qp.get("cat", "Outro"),
            int(qp.get("frio", 0)), int(qp.get("quent", 0)), int(qp.get("un_cx", 1)),
            int(qp.get("id", 0))
        ))

    # ── EXCLUIR PRODUTO
    elif acao == "excluir_produto":
        run("UPDATE produtos SET ativo=0 WHERE id=?", (int(qp.get("id", 0)),))

    # ── REPOR ESTOQUE
    elif acao == "repor_estoque":
        p_id  = int(qp.get("id", 0))
        frio  = int(qp.get("frio", 0))
        quent = int(qp.get("quent", 0))
        run("UPDATE produtos SET frio_unid=frio_unid+?, quent_caixas=quent_caixas+? WHERE id=?", (frio, quent, p_id))

    st.query_params.clear()
    st.rerun()

# ─── LOAD DATA ────────────────────────────────────────────────────────────────
prods   = fetch("SELECT * FROM produtos WHERE ativo=1 ORDER BY categoria, nome")
clis    = fetch("SELECT * FROM clientes WHERE ativo=1 ORDER BY nome")

# saldos por cliente
saldos_df = fetch("""
    SELECT cliente_id,
           COALESCE(SUM(CASE WHEN pago=0 THEN total ELSE 0 END),0) AS devendo
    FROM consumos
    WHERE tipo='FIADO'
    GROUP BY cliente_id
""")
pgtos_df  = fetch("SELECT cliente_id, COALESCE(SUM(valor),0) AS pago FROM pagamentos GROUP BY cliente_id")

clis_com_saldo = clis.copy()
clis_com_saldo = clis_com_saldo.merge(saldos_df, left_on='id', right_on='cliente_id', how='left')
clis_com_saldo['devendo'] = clis_com_saldo['devendo'].fillna(0)

# historico completo por cliente
historico_raw = fetch("""
    SELECT c.id as consumo_id, c.cliente_id, c.produto_nome, c.produto_preco,
           c.qtd, c.total, c.tipo, c.pago, c.data, c.observacao
    FROM consumos c
    ORDER BY c.data DESC
""")
pagamentos_raw = fetch("""
    SELECT p.id, p.cliente_id, p.valor, p.data, p.observacao
    FROM pagamentos p
    ORDER BY p.data DESC
""")

prods_json       = prods.to_json(orient="records")
clis_json        = clis_com_saldo.to_json(orient="records")
historico_json   = historico_raw.to_json(orient="records")
pagamentos_json  = pagamentos_raw.to_json(orient="records")

# ─── HTML UI ─────────────────────────────────────────────────────────────────
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
    --bg:        #080b12;
    --surface:   #0d1220;
    --surface2:  #111827;
    --border:    rgba(255,255,255,0.06);
    --border2:   rgba(255,255,255,0.10);
    --text:      #e2e8f0;
    --muted:     #64748b;
    --muted2:    #94a3b8;
    --gold:      #f59e0b;
    --gold2:     #fbbf24;
    --green:     #10b981;
    --cyan:      #06b6d4;
    --red:       #ef4444;
    --amber:     #f59e0b;
    --glow-gold: rgba(245,158,11,0.15);
    --glow-green:rgba(16,185,129,0.12);
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;overflow:hidden;background:var(--bg);color:var(--text);font-family:'DM Sans',sans-serif;font-size:14px}

/* SCROLLBAR */
::-webkit-scrollbar{width:4px;height:4px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:2px}

/* LAYOUT */
.shell{display:flex;height:100vh;overflow:hidden}

/* SIDEBAR */
.sidebar{
    width:240px;min-width:240px;background:var(--surface);
    border-right:1px solid var(--border);
    display:flex;flex-direction:column;
    padding:20px 0;
    transition:.3s ease
}
.brand{padding:0 20px 24px;border-bottom:1px solid var(--border)}
.brand-logo{
    width:44px;height:44px;border-radius:12px;
    background:linear-gradient(135deg,#b45309,#f59e0b);
    display:flex;align-items:center;justify-content:center;
    font-size:20px;margin-bottom:10px;
    box-shadow:0 0 24px rgba(245,158,11,0.3)
}
.brand-name{font-family:'Syne',sans-serif;font-weight:800;font-size:16px;color:#fff;line-height:1.2}
.brand-sub{font-size:10px;color:var(--gold);letter-spacing:.12em;text-transform:uppercase;margin-top:2px}

.nav{flex:1;padding:16px 10px;overflow-y:auto}
.nav-section{font-size:9px;font-weight:600;color:var(--muted);letter-spacing:.12em;text-transform:uppercase;padding:0 10px 8px;margin-top:16px}
.nav-btn{
    width:100%;display:flex;align-items:center;gap:10px;
    padding:10px 12px;border-radius:10px;border:none;cursor:pointer;
    background:transparent;color:var(--muted2);font-family:'DM Sans',sans-serif;
    font-size:13px;font-weight:500;text-align:left;transition:.2s ease;
    position:relative
}
.nav-btn:hover{background:rgba(255,255,255,0.04);color:var(--text)}
.nav-btn.active{background:rgba(245,158,11,0.1);color:var(--gold2);border:1px solid rgba(245,158,11,0.2)}
.nav-btn .icon{width:28px;height:28px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:12px}
.nav-btn.active .icon{background:rgba(245,158,11,0.15)}
.nav-badge{margin-left:auto;background:var(--red);color:#fff;font-size:10px;font-weight:700;padding:2px 6px;border-radius:20px}

.sidebar-footer{padding:16px 20px;border-top:1px solid var(--border)}
.clock-box{font-size:11px;color:var(--muted);text-align:center;font-variant-numeric:tabular-nums}

/* MAIN */
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.topbar{
    height:60px;min-height:60px;background:var(--surface);
    border-bottom:1px solid var(--border);
    display:flex;align-items:center;justify-content:space-between;
    padding:0 28px
}
.topbar-title{font-family:'Syne',sans-serif;font-weight:700;font-size:18px;color:#fff}
.topbar-sub{font-size:11px;color:var(--muted);margin-top:1px}
.content{flex:1;overflow-y:auto;padding:24px 28px}

/* CARDS */
.card{
    background:var(--surface);border:1px solid var(--border);
    border-radius:16px;padding:20px
}
.card-title{font-family:'Syne',sans-serif;font-weight:700;font-size:13px;color:var(--text);letter-spacing:.04em;text-transform:uppercase;margin-bottom:16px;display:flex;align-items:center;gap:8px}
.card-title .dot{width:6px;height:6px;border-radius:50%}

/* STAT CARDS */
.stats-row{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:24px}
.stat-card{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:16px 18px;position:relative;overflow:hidden}
.stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;border-radius:2px 2px 0 0}
.stat-card.gold::before{background:linear-gradient(90deg,#b45309,#f59e0b)}
.stat-card.green::before{background:linear-gradient(90deg,#059669,#10b981)}
.stat-card.cyan::before{background:linear-gradient(90deg,#0891b2,#06b6d4)}
.stat-card.red::before{background:linear-gradient(90deg,#dc2626,#ef4444)}
.stat-label{font-size:10px;font-weight:600;color:var(--muted);letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px}
.stat-val{font-family:'Syne',sans-serif;font-weight:800;font-size:22px;color:#fff}
.stat-sub{font-size:11px;color:var(--muted);margin-top:3px}

/* GRID */
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.grid-3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px}
.gap-16{gap:16px}

/* FORM */
.form-group{margin-bottom:14px}
.form-label{display:block;font-size:10px;font-weight:700;color:var(--muted);letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px}
.form-control{
    width:100%;background:var(--bg);border:1px solid var(--border2);
    border-radius:10px;padding:10px 14px;color:var(--text);
    font-family:'DM Sans',sans-serif;font-size:13px;
    transition:.2s ease;outline:none
}
.form-control:focus{border-color:var(--gold);box-shadow:0 0 0 3px rgba(245,158,11,0.1)}
select.form-control option{background:var(--surface2);color:var(--text)}

/* BUTTONS */
.btn{
    display:inline-flex;align-items:center;gap:6px;
    padding:10px 18px;border-radius:10px;border:none;cursor:pointer;
    font-family:'DM Sans',sans-serif;font-size:12px;font-weight:700;
    letter-spacing:.06em;text-transform:uppercase;transition:.2s ease
}
.btn-gold{background:linear-gradient(135deg,#b45309,#f59e0b);color:#000;box-shadow:0 4px 16px rgba(245,158,11,0.25)}
.btn-gold:hover{box-shadow:0 4px 24px rgba(245,158,11,0.45);transform:translateY(-1px)}
.btn-green{background:linear-gradient(135deg,#059669,#10b981);color:#000}
.btn-green:hover{box-shadow:0 4px 20px rgba(16,185,129,0.35);transform:translateY(-1px)}
.btn-cyan{background:linear-gradient(135deg,#0891b2,#06b6d4);color:#000}
.btn-cyan:hover{box-shadow:0 4px 20px rgba(6,182,212,0.35);transform:translateY(-1px)}
.btn-red{background:rgba(239,68,68,0.1);color:var(--red);border:1px solid rgba(239,68,68,0.2)}
.btn-red:hover{background:rgba(239,68,68,0.2)}
.btn-ghost{background:rgba(255,255,255,0.04);color:var(--muted2);border:1px solid var(--border)}
.btn-ghost:hover{background:rgba(255,255,255,0.07);color:var(--text)}
.btn-full{width:100%;justify-content:center}
.btn-sm{padding:6px 12px;font-size:11px;border-radius:8px}
.btn-xs{padding:4px 8px;font-size:10px;border-radius:6px}

/* TABLE */
.table-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse}
thead tr{border-bottom:1px solid var(--border)}
thead th{padding:10px 14px;font-size:9px;font-weight:700;color:var(--muted);letter-spacing:.12em;text-transform:uppercase;text-align:left;white-space:nowrap}
tbody tr{border-bottom:1px solid rgba(255,255,255,0.03);transition:.15s}
tbody tr:hover{background:rgba(255,255,255,0.02)}
tbody td{padding:11px 14px;font-size:13px;color:var(--muted2)}
tbody td.bold{font-weight:600;color:var(--text)}
tbody td.gold{color:var(--gold2);font-weight:700}
tbody td.green{color:var(--green);font-weight:700}
tbody td.red{color:var(--red);font-weight:700}

/* BADGES */
.badge{display:inline-flex;align-items:center;gap:4px;padding:3px 8px;border-radius:20px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.06em}
.badge-green{background:rgba(16,185,129,0.12);color:var(--green);border:1px solid rgba(16,185,129,0.2)}
.badge-red{background:rgba(239,68,68,0.1);color:var(--red);border:1px solid rgba(239,68,68,0.2)}
.badge-gold{background:rgba(245,158,11,0.1);color:var(--gold2);border:1px solid rgba(245,158,11,0.2)}
.badge-cyan{background:rgba(6,182,212,0.1);color:var(--cyan);border:1px solid rgba(6,182,212,0.2)}
.badge-gray{background:rgba(100,116,139,0.1);color:var(--muted2);border:1px solid rgba(100,116,139,0.2)}

/* CLIENT CARD */
.client-card{
    background:var(--surface);border:1px solid var(--border);
    border-radius:14px;padding:16px;cursor:pointer;transition:.2s;
    display:flex;align-items:center;gap:12px
}
.client-card:hover{border-color:rgba(245,158,11,0.3);background:rgba(245,158,11,0.03)}
.client-card.has-debt{border-left:3px solid var(--amber)}
.client-avatar{
    width:42px;height:42px;border-radius:12px;
    background:linear-gradient(135deg,#1e293b,#334155);
    display:flex;align-items:center;justify-content:center;
    font-family:'Syne',sans-serif;font-weight:800;font-size:16px;color:var(--gold2);
    flex-shrink:0
}
.client-name{font-weight:600;color:var(--text);font-size:14px;line-height:1.3}
.client-meta{font-size:11px;color:var(--muted);margin-top:2px}
.client-debt{margin-left:auto;text-align:right}
.client-debt-val{font-family:'Syne',sans-serif;font-weight:800;font-size:16px}
.client-debt-lbl{font-size:10px;color:var(--muted);margin-top:1px}

/* MODAL */
.modal-overlay{
    position:fixed;inset:0;background:rgba(0,0,0,0.7);
    backdrop-filter:blur(6px);z-index:1000;
    display:flex;align-items:center;justify-content:center;
    opacity:0;pointer-events:none;transition:.2s ease
}
.modal-overlay.open{opacity:1;pointer-events:all}
.modal{
    background:var(--surface2);border:1px solid var(--border2);
    border-radius:20px;width:520px;max-width:90vw;max-height:85vh;
    overflow-y:auto;padding:28px;
    transform:translateY(20px);transition:.25s ease
}
.modal-overlay.open .modal{transform:translateY(0)}
.modal-header{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:20px}
.modal-title{font-family:'Syne',sans-serif;font-weight:700;font-size:18px;color:#fff}
.modal-close{background:rgba(255,255,255,0.06);border:1px solid var(--border);color:var(--muted2);width:30px;height:30px;border-radius:8px;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:14px;transition:.2s}
.modal-close:hover{background:rgba(255,255,255,0.1);color:#fff}

/* PRODUCT GRID */
.prod-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px}
.prod-tile{
    background:var(--bg);border:1px solid var(--border);
    border-radius:12px;padding:14px;cursor:pointer;transition:.2s;
    position:relative
}
.prod-tile:hover{border-color:rgba(245,158,11,0.3);background:rgba(245,158,11,0.03)}
.prod-tile.selected{border-color:var(--gold);box-shadow:0 0 0 2px rgba(245,158,11,0.2)}
.prod-emoji{font-size:22px;margin-bottom:8px}
.prod-tile-name{font-size:12px;font-weight:600;color:var(--text);line-height:1.3}
.prod-tile-preco{font-family:'Syne',sans-serif;font-size:15px;font-weight:800;color:var(--gold2);margin-top:4px}
.prod-tile-stock{font-size:10px;color:var(--muted);margin-top:3px}
.prod-check{position:absolute;top:8px;right:8px;width:18px;height:18px;border-radius:50%;background:var(--gold);display:flex;align-items:center;justify-content:center;font-size:10px;color:#000;opacity:0;transition:.15s}
.prod-tile.selected .prod-check{opacity:1}

/* HISTORY */
.history-entry{
    display:flex;align-items:flex-start;gap:12px;
    padding:12px 0;border-bottom:1px solid rgba(255,255,255,0.04)
}
.history-entry:last-child{border-bottom:none}
.h-icon{width:32px;height:32px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:13px;flex-shrink:0}
.h-date{font-size:11px;color:var(--muted)}
.h-desc{font-size:13px;color:var(--text);font-weight:500;margin:2px 0}
.h-meta{font-size:11px;color:var(--muted2)}

/* TOAST */
.toast-area{position:fixed;bottom:24px;right:24px;z-index:2000;display:flex;flex-direction:column;gap:8px}
.toast{
    background:var(--surface2);border:1px solid var(--border2);
    border-radius:12px;padding:12px 16px;min-width:260px;
    display:flex;align-items:center;gap:10px;
    box-shadow:0 8px 32px rgba(0,0,0,0.4);
    animation:slideIn .3s ease;font-size:13px;color:var(--text)
}
.toast.green{border-left:3px solid var(--green)}
.toast.red{border-left:3px solid var(--red)}
@keyframes slideIn{from{transform:translateX(40px);opacity:0}to{transform:none;opacity:1}}

/* DIVIDER */
.divider{border:none;border-top:1px solid var(--border);margin:16px 0}

/* SCREEN */
.screen{display:none}
.screen.active{display:block}

/* EMPTY STATE */
.empty{text-align:center;padding:40px;color:var(--muted)}
.empty-icon{font-size:36px;margin-bottom:12px;opacity:.4}
.empty-text{font-size:14px;font-weight:500;color:var(--muted2)}
.empty-sub{font-size:12px;color:var(--muted);margin-top:4px}

/* SEARCH */
.search-box{position:relative;margin-bottom:16px}
.search-box input{padding-left:36px}
.search-icon{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--muted);font-size:12px}

.tab-bar{display:flex;gap:4px;margin-bottom:20px;background:rgba(0,0,0,0.3);padding:4px;border-radius:12px;width:fit-content}
.tab{padding:8px 16px;border-radius:9px;border:none;cursor:pointer;font-family:'DM Sans',sans-serif;font-size:12px;font-weight:600;color:var(--muted);background:transparent;transition:.2s;letter-spacing:.04em}
.tab.active{background:var(--surface2);color:var(--text);box-shadow:0 1px 4px rgba(0,0,0,0.3)}

.stock-bar{height:4px;border-radius:2px;background:rgba(255,255,255,0.06);overflow:hidden;margin-top:4px}
.stock-fill{height:100%;border-radius:2px;transition:.3s}
</style>
</head>
<body>
<div class="shell">

  <!-- SIDEBAR -->
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-logo">🍺</div>
      <div class="brand-name">Bar do Querido</div>
      <div class="brand-sub">Sistema de Gestão</div>
    </div>
    <nav class="nav">
      <div class="nav-section">Principal</div>
      <button class="nav-btn active" id="nav-balcao" onclick="setScreen('balcao')">
        <span class="icon"><i class="fa-solid fa-receipt"></i></span> Balcão
      </button>
      <button class="nav-btn" id="nav-fichas" onclick="setScreen('fichas')">
        <span class="icon"><i class="fa-solid fa-users"></i></span> Fichas
        <span class="nav-badge" id="badge-fichas" style="display:none">0</span>
      </button>

      <div class="nav-section">Gestão</div>
      <button class="nav-btn" id="nav-estoque" onclick="setScreen('estoque')">
        <span class="icon"><i class="fa-solid fa-boxes-stacked"></i></span> Estoque
      </button>
      <button class="nav-btn" id="nav-relatorio" onclick="setScreen('relatorio')">
        <span class="icon"><i class="fa-solid fa-chart-bar"></i></span> Relatório
      </button>
    </nav>
    <div class="sidebar-footer">
      <div class="clock-box" id="live-clock">--/--/---- --:--:--</div>
    </div>
  </aside>

  <!-- MAIN -->
  <main class="main">
    <div class="topbar">
      <div>
        <div class="topbar-title" id="screen-title">Balcão de Vendas</div>
        <div class="topbar-sub" id="screen-sub">Terminal de operações integrado</div>
      </div>
      <div style="display:flex;gap:8px;">
        <button class="btn btn-ghost btn-sm" onclick="setScreen('balcao')"><i class="fa-solid fa-plus"></i> Novo Consumo</button>
      </div>
    </div>

    <div class="content">

      <!-- ══════════════ BALCÃO ══════════════ -->
      <div class="screen active" id="screen-balcao">
        <div class="stats-row" id="stats-balcao"></div>

        <div class="grid-2" style="gap:20px;align-items:start">
          <!-- Formulário de venda -->
          <div class="card">
            <div class="card-title"><span class="dot" style="background:var(--gold)"></span>Lançar Consumo</div>

            <div class="form-group">
              <label class="form-label">Tipo de venda</label>
              <div style="display:flex;gap:8px">
                <button class="btn btn-gold" id="tipo-avista" onclick="setTipo('A_VISTA')" style="flex:1">💵 À Vista</button>
                <button class="btn btn-ghost" id="tipo-fiado" onclick="setTipo('FIADO')" style="flex:1">📋 Fiado</button>
              </div>
            </div>

            <div class="form-group" id="grupo-cliente" style="display:none">
              <label class="form-label">Ficha do Cliente</label>
              <select class="form-control" id="venda_cliente">
                <option value="AVULSO">— Selecione o cliente —</option>
              </select>
            </div>

            <div class="form-group">
              <label class="form-label">Produto</label>
              <select class="form-control" id="venda_produto" onchange="atualizarInfoProd()"></select>
            </div>

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
              <div class="form-group">
                <label class="form-label">Quantidade</label>
                <input class="form-control" type="number" id="venda_qtd" value="1" min="1" oninput="atualizarInfoProd()">
              </div>
              <div class="form-group">
                <label class="form-label">Observação</label>
                <input class="form-control" type="text" id="venda_obs" placeholder="Opcional...">
              </div>
            </div>

            <div id="venda-preview" style="background:rgba(245,158,11,0.06);border:1px solid rgba(245,158,11,0.15);border-radius:10px;padding:12px;margin-bottom:14px;display:none">
              <div style="font-size:11px;color:var(--muted);margin-bottom:4px">TOTAL A LANÇAR</div>
              <div style="font-family:'Syne',sans-serif;font-size:24px;font-weight:800;color:var(--gold2)" id="venda-total-preview">R$ 0,00</div>
            </div>

            <button class="btn btn-gold btn-full" onclick="confirmarVenda()">
              <i class="fa-solid fa-check-circle"></i> Confirmar Operação
            </button>
          </div>

          <!-- Consumos recentes -->
          <div class="card">
            <div class="card-title"><span class="dot" style="background:var(--cyan)"></span>Últimas Operações</div>
            <div class="table-wrap">
              <table>
                <thead><tr>
                  <th>Item</th><th>Qtd</th><th>Total</th><th>Tipo</th><th>Data</th>
                </tr></thead>
                <tbody id="tabela-recentes"></tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <!-- ══════════════ FICHAS ══════════════ -->
      <div class="screen" id="screen-fichas">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
          <div></div>
          <button class="btn btn-gold" onclick="openModal('modal-novo-cliente')">
            <i class="fa-solid fa-user-plus"></i> Nova Ficha
          </button>
        </div>

        <div class="search-box">
          <i class="fa-solid fa-magnifying-glass search-icon"></i>
          <input class="form-control" id="busca-cliente" type="text" placeholder="Buscar cliente..." oninput="filtrarClientes()">
        </div>

        <div id="lista-clientes" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px"></div>
      </div>

      <!-- ══════════════ ESTOQUE ══════════════ -->
      <div class="screen" id="screen-estoque">
        <div class="tab-bar">
          <button class="tab active" id="tab-cat" onclick="setEstoqueTab('catalogo')">Catálogo</button>
          <button class="tab" id="tab-rep" onclick="setEstoqueTab('reposicao')">Reposição</button>
          <button class="tab" id="tab-new" onclick="setEstoqueTab('novo')">Novo Produto</button>
        </div>

        <!-- Catálogo -->
        <div id="estoque-catalogo">
          <div class="search-box">
            <i class="fa-solid fa-magnifying-glass search-icon"></i>
            <input class="form-control" id="busca-prod" type="text" placeholder="Buscar produto..." oninput="filtrarProdutos()">
          </div>
          <div class="card">
            <div class="table-wrap">
              <table>
                <thead><tr>
                  <th>Produto</th><th>Cat.</th><th>Preço</th><th>Frio (un)</th><th>Quente (cx)</th><th>Total</th><th>Ações</th>
                </tr></thead>
                <tbody id="tabela-estoque"></tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Reposição -->
        <div id="estoque-reposicao" style="display:none">
          <div class="card">
            <div class="card-title"><span class="dot" style="background:var(--cyan)"></span>Repor Estoque</div>
            <div style="display:grid;grid-template-columns:2fr 1fr 1fr auto;gap:12px;align-items:end">
              <div class="form-group" style="margin:0">
                <label class="form-label">Produto</label>
                <select class="form-control" id="rep_prod"></select>
              </div>
              <div class="form-group" style="margin:0">
                <label class="form-label">+ Gelando (un)</label>
                <input class="form-control" type="number" id="rep_frio" value="0" min="0">
              </div>
              <div class="form-group" style="margin:0">
                <label class="form-label">+ Quente (cx)</label>
                <input class="form-control" type="number" id="rep_quent" value="0" min="0">
              </div>
              <button class="btn btn-cyan" onclick="reporEstoque()"><i class="fa-solid fa-plus"></i> Repor</button>
            </div>
          </div>
          <div style="margin-top:16px">
            <div class="card">
              <div class="card-title"><span class="dot" style="background:var(--amber)"></span>Nível dos Estoques</div>
              <div id="nivel-estoques"></div>
            </div>
          </div>
        </div>

        <!-- Novo produto -->
        <div id="estoque-novo" style="display:none">
          <div class="card">
            <div class="card-title" id="form-prod-title"><span class="dot" style="background:var(--gold)"></span>Novo Produto</div>
            <input type="hidden" id="prod_edit_id">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
              <div class="form-group">
                <label class="form-label">Nome do Produto</label>
                <input class="form-control" id="prod_nome" type="text" placeholder="Ex: Heineken 600ml">
              </div>
              <div class="form-group">
                <label class="form-label">Preço de Venda (R$)</label>
                <input class="form-control" id="prod_preco" type="number" step="0.01" min="0" placeholder="0.00">
              </div>
              <div class="form-group">
                <label class="form-label">Categoria</label>
                <select class="form-control" id="prod_cat">
                  <option>Cerveja</option><option>Refrigerante</option><option>Água</option>
                  <option>Porções</option><option>Salgados</option><option>Doces</option><option>Outro</option>
                </select>
              </div>
              <div class="form-group">
                <label class="form-label">Un. por Caixa</label>
                <input class="form-control" id="prod_un_cx" type="number" min="1" value="1">
              </div>
              <div class="form-group">
                <label class="form-label">Qtd. Gelando (un)</label>
                <input class="form-control" id="prod_frio" type="number" min="0" value="0">
              </div>
              <div class="form-group">
                <label class="form-label">Qtd. Depósito (cx)</label>
                <input class="form-control" id="prod_quent" type="number" min="0" value="0">
              </div>
            </div>
            <hr class="divider">
            <div style="display:flex;gap:10px">
              <button class="btn btn-gold btn-full" id="btn-salvar-prod" onclick="salvarProduto()">
                <i class="fa-solid fa-floppy-disk"></i> Salvar Produto
              </button>
              <button class="btn btn-ghost btn-sm" id="btn-cancel-edit" style="display:none" onclick="cancelarEdicaoProd()">Cancelar</button>
            </div>
          </div>
        </div>
      </div>

      <!-- ══════════════ RELATÓRIO ══════════════ -->
      <div class="screen" id="screen-relatorio">
        <div class="stats-row" id="stats-relatorio"></div>
        <div class="grid-2" style="gap:20px">
          <div class="card">
            <div class="card-title"><span class="dot" style="background:var(--red)"></span>Maiores Devedores</div>
            <div id="ranking-devedores"></div>
          </div>
          <div class="card">
            <div class="card-title"><span class="dot" style="background:var(--cyan)"></span>Produtos Mais Vendidos</div>
            <div id="ranking-produtos"></div>
          </div>
        </div>
        <div class="card" style="margin-top:20px">
          <div class="card-title"><span class="dot" style="background:var(--green)"></span>Histórico Global de Consumos</div>
          <div class="table-wrap">
            <table>
              <thead><tr>
                <th>Data</th><th>Cliente</th><th>Produto</th><th>Qtd</th><th>Total</th><th>Tipo</th><th>Status</th>
              </tr></thead>
              <tbody id="tabela-historico-global"></tbody>
            </table>
          </div>
        </div>
      </div>

    </div><!-- /content -->
  </main>
</div>

<!-- ══════════════ MODALS ══════════════ -->

<!-- Modal: Novo Cliente -->
<div class="modal-overlay" id="modal-novo-cliente">
  <div class="modal">
    <div class="modal-header">
      <div class="modal-title">Nova Ficha de Cliente</div>
      <button class="modal-close" onclick="closeModal('modal-novo-cliente')"><i class="fa-solid fa-xmark"></i></button>
    </div>
    <div class="form-group">
      <label class="form-label">Nome / Apelido</label>
      <input class="form-control" id="nc_nome" type="text" placeholder="Ex: Seu João do Posto">
    </div>
    <div class="form-group">
      <label class="form-label">Telefone (opcional)</label>
      <input class="form-control" id="nc_tel" type="text" placeholder="(43) 9XXXX-XXXX">
    </div>
    <div class="form-group">
      <label class="form-label">Observação (opcional)</label>
      <input class="form-control" id="nc_obs" type="text" placeholder="Ex: Ficha nº 12, amigo do Zé...">
    </div>
    <button class="btn btn-gold btn-full" onclick="cadastrarCliente()">
      <i class="fa-solid fa-user-plus"></i> Abrir Ficha
    </button>
  </div>
</div>

<!-- Modal: Ficha do Cliente -->
<div class="modal-overlay" id="modal-ficha-cliente">
  <div class="modal" style="width:620px">
    <div class="modal-header">
      <div>
        <div class="modal-title" id="ficha-nome">—</div>
        <div style="font-size:12px;color:var(--muted);margin-top:3px" id="ficha-meta">—</div>
      </div>
      <button class="modal-close" onclick="closeModal('modal-ficha-cliente')"><i class="fa-solid fa-xmark"></i></button>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:20px" id="ficha-stats"></div>

    <!-- Registrar pagamento -->
    <div style="background:rgba(16,185,129,0.06);border:1px solid rgba(16,185,129,0.15);border-radius:12px;padding:14px;margin-bottom:16px">
      <div style="font-size:11px;font-weight:700;color:var(--green);letter-spacing:.1em;text-transform:uppercase;margin-bottom:10px"><i class="fa-solid fa-hand-holding-dollar"></i> Registrar Pagamento</div>
      <div style="display:flex;gap:10px">
        <input class="form-control" type="number" id="pgto_valor" placeholder="Valor R$" step="0.01" min="0.01" style="flex:1">
        <input class="form-control" type="text" id="pgto_obs" placeholder="Observação" style="flex:1.5">
        <button class="btn btn-green" onclick="registrarPagamento()"><i class="fa-solid fa-check"></i> Quitar</button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="tab-bar" style="margin-bottom:12px">
      <button class="tab active" id="ftab-consumos" onclick="setFichaTab('consumos')">Consumos</button>
      <button class="tab" id="ftab-pagamentos" onclick="setFichaTab('pagamentos')">Pagamentos</button>
      <button class="tab" id="ftab-editar" onclick="setFichaTab('editar')">Editar</button>
    </div>

    <div id="ftab-consumos-content">
      <div class="table-wrap" style="max-height:280px;overflow-y:auto">
        <table>
          <thead><tr><th>Data</th><th>Produto</th><th>Qtd</th><th>Total</th><th>Status</th></tr></thead>
          <tbody id="ficha-consumos-body"></tbody>
        </table>
      </div>
    </div>

    <div id="ftab-pagamentos-content" style="display:none">
      <div class="table-wrap" style="max-height:280px;overflow-y:auto">
        <table>
          <thead><tr><th>Data</th><th>Valor Pago</th><th>Obs</th></tr></thead>
          <tbody id="ficha-pagamentos-body"></tbody>
        </table>
      </div>
    </div>

    <div id="ftab-editar-content" style="display:none">
      <div class="form-group"><label class="form-label">Nome</label><input class="form-control" id="edit_cli_nome" type="text"></div>
      <div class="form-group"><label class="form-label">Telefone</label><input class="form-control" id="edit_cli_tel" type="text"></div>
      <div class="form-group"><label class="form-label">Observação</label><input class="form-control" id="edit_cli_obs" type="text"></div>
      <div style="display:flex;gap:8px">
        <button class="btn btn-gold btn-full" onclick="salvarEdicaoCliente()"><i class="fa-solid fa-floppy-disk"></i> Salvar</button>
        <button class="btn btn-red btn-sm" onclick="arquivarCliente()"><i class="fa-solid fa-archive"></i></button>
      </div>
    </div>

  </div>
</div>

<!-- Toast area -->
<div class="toast-area" id="toast-area"></div>

<script>
// ═══════════════════════════════════════════
// DATA
// ═══════════════════════════════════════════
const produtos  = __PRODUTOS_JSON__;
const clientes  = __CLIENTES_JSON__;
const historico = __HISTORICO_JSON__;
const pagamentos= __PAGAMENTOS_JSON__;

let tipoVenda     = 'A_VISTA';
let clienteAtivo  = null;
let fichaClienteId= null;

// ═══════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════
function init() {
    preencherSelectProduto('venda_produto');
    preencherSelectProduto('rep_prod');
    preencherSelectCliente('venda_cliente');
    renderRecentes();
    renderListaClientes();
    renderEstoque();
    renderNivelEstoques();
    renderRelatorio();
    atualizarBadgeFichas();

    const screen = (() => { try { return localStorage.getItem('bar_screen') || 'balcao'; } catch(e) { return 'balcao'; } })();
    setScreen(screen, false);

    setInterval(() => {
        const d = new Date();
        document.getElementById('live-clock').innerText =
            d.toLocaleDateString('pt-BR') + ' — ' + d.toLocaleTimeString('pt-BR');
    }, 1000);
}

// ═══════════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════════
const screenTitles = {
    balcao:   ['Balcão de Vendas', 'Terminal de operações integrado'],
    fichas:   ['Fichas & Clientes', 'Controle de fiado e histórico'],
    estoque:  ['Gestão de Estoque', 'Catálogo, reposição e inventário'],
    relatorio:['Relatório Geral', 'Visão consolidada do negócio'],
};

function setScreen(s, save=true) {
    document.querySelectorAll('.screen').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
    document.getElementById('screen-' + s).classList.add('active');
    document.getElementById('nav-' + s).classList.add('active');
    document.getElementById('screen-title').innerText = screenTitles[s][0];
    document.getElementById('screen-sub').innerText   = screenTitles[s][1];
    if(save) { try { localStorage.setItem('bar_screen', s); } catch(e) {} }
}

// ═══════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════
function fmtMoeda(v) {
    return 'R$ ' + parseFloat(v || 0).toLocaleString('pt-BR', {minimumFractionDigits:2, maximumFractionDigits:2});
}
function fmtData(s) {
    if(!s) return '—';
    const d = new Date(s.replace(' ','T'));
    return d.toLocaleDateString('pt-BR') + ' ' + d.toLocaleTimeString('pt-BR', {hour:'2-digit',minute:'2-digit'});
}
function catEmoji(cat) {
    const m = {'Cerveja':'🍺','Refrigerante':'🥤','Água':'💧','Porções':'🍗','Salgados':'🧆','Doces':'🍬'};
    return m[cat] || '📦';
}
function devendoCliente(cId) {
    const pendentes = historico.filter(h => h.cliente_id == cId && h.tipo === 'FIADO' && h.pago == 0);
    return pendentes.reduce((s, h) => s + h.total, 0);
}
function totalPagoCliente(cId) {
    return pagamentos.filter(p => p.cliente_id == cId).reduce((s, p) => s + p.valor, 0);
}
function totalConsumoCliente(cId) {
    return historico.filter(h => h.cliente_id == cId && h.tipo === 'FIADO').reduce((s, h) => s + h.total, 0);
}

// ═══════════════════════════════════════════
// SELECTS
// ═══════════════════════════════════════════
function preencherSelectProduto(id) {
    const sel = document.getElementById(id);
    if(!sel) return;
    sel.innerHTML = '<option value="">— Selecione o produto —</option>';
    produtos.forEach(p => {
        sel.innerHTML += `<option value="${p.id}">${catEmoji(p.categoria)} ${p.nome} — ${fmtMoeda(p.preco)} (${p.frio_unid} un)</option>`;
    });
}

function preencherSelectCliente(id) {
    const sel = document.getElementById(id);
    if(!sel) return;
    sel.innerHTML = '<option value="AVULSO">— Selecione o cliente —</option>';
    clientes.forEach(c => {
        const devendo = devendoCliente(c.id);
        sel.innerHTML += `<option value="${c.id}">👤 ${c.nome}${devendo > 0 ? ' — deve ' + fmtMoeda(devendo) : ''}</option>`;
    });
}

// ═══════════════════════════════════════════
// BALCÃO
// ═══════════════════════════════════════════
function setTipo(t) {
    tipoVenda = t;
    document.getElementById('tipo-avista').className = t === 'A_VISTA' ? 'btn btn-gold' : 'btn btn-ghost';
    document.getElementById('tipo-fiado').className  = t === 'FIADO'   ? 'btn btn-gold' : 'btn btn-ghost';
    document.getElementById('grupo-cliente').style.display = t === 'FIADO' ? 'block' : 'none';
}

function atualizarInfoProd() {
    const pId = parseInt(document.getElementById('venda_produto').value);
    const qtd = parseInt(document.getElementById('venda_qtd').value) || 0;
    const p = produtos.find(x => x.id === pId);
    const preview = document.getElementById('venda-preview');
    if(p && qtd > 0) {
        document.getElementById('venda-total-preview').innerText = fmtMoeda(p.preco * qtd);
        preview.style.display = 'block';
    } else {
        preview.style.display = 'none';
    }
}

function confirmarVenda() {
    const pId = document.getElementById('venda_produto').value;
    const qtd = document.getElementById('venda_qtd').value;
    const cId = tipoVenda === 'FIADO' ? document.getElementById('venda_cliente').value : 'AVULSO';
    const obs = document.getElementById('venda_obs').value;

    if(!pId) return toast('Selecione um produto!', 'red');
    if(tipoVenda === 'FIADO' && cId === 'AVULSO') return toast('Selecione o cliente para fiado!', 'red');

    navegar(`acao=lancar_consumo&produto_id=${pId}&qtd=${qtd}&cliente_id=${cId}&obs=${encodeURIComponent(obs)}&tipo=${tipoVenda}`);
}

function renderRecentes() {
    const tbody = document.getElementById('tabela-recentes');
    const recentes = [...historico].sort((a,b) => b.id - a.id).slice(0, 20);
    if(recentes.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="empty" style="padding:24px;text-align:center;color:var(--muted)">Nenhuma operação ainda</td></tr>`;
        return;
    }
    tbody.innerHTML = recentes.map(h => {
        const cli = clientes.find(c => c.id == h.cliente_id);
        const tipoB = h.tipo === 'FIADO'
            ? `<span class="badge badge-gold">Fiado</span>`
            : `<span class="badge badge-green">À Vista</span>`;
        return `
        <tr>
          <td class="bold">${catEmoji('')} ${h.produto_nome}</td>
          <td>${h.qtd}x</td>
          <td class="gold">${fmtMoeda(h.total)}</td>
          <td>${tipoB}</td>
          <td style="font-size:11px;color:var(--muted)">${fmtData(h.data)}</td>
        </tr>`;
    }).join('');

    // stats balcão
    const totalDia = historico.reduce((s,h) => s + h.total, 0);
    const totalFiado = historico.filter(h => h.tipo==='FIADO' && h.pago==0).reduce((s,h) => s + h.total, 0);
    const totalAVista = historico.filter(h => h.tipo==='A_VISTA').reduce((s,h) => s + h.total, 0);
    const qtdClientes = clientes.length;
    document.getElementById('stats-balcao').innerHTML = `
        <div class="stat-card gold"><div class="stat-label">Total em Caixa</div><div class="stat-val">${fmtMoeda(totalAVista)}</div><div class="stat-sub">vendas à vista</div></div>
        <div class="stat-card red"><div class="stat-label">Total em Aberto</div><div class="stat-val">${fmtMoeda(totalFiado)}</div><div class="stat-sub">fiado pendente</div></div>
        <div class="stat-card green"><div class="stat-label">Faturamento Total</div><div class="stat-val">${fmtMoeda(totalDia)}</div><div class="stat-sub">todo o histórico</div></div>
        <div class="stat-card cyan"><div class="stat-label">Clientes</div><div class="stat-val">${qtdClientes}</div><div class="stat-sub">fichas ativas</div></div>
    `;
}

// ═══════════════════════════════════════════
// FICHAS
// ═══════════════════════════════════════════
function atualizarBadgeFichas() {
    const com_divida = clientes.filter(c => devendoCliente(c.id) > 0).length;
    const badge = document.getElementById('badge-fichas');
    if(com_divida > 0) { badge.style.display = 'inline'; badge.innerText = com_divida; }
    else { badge.style.display = 'none'; }
}

function renderListaClientes(filtro='') {
    const lista = document.getElementById('lista-clientes');
    const filtrados = clientes.filter(c => c.nome.toLowerCase().includes(filtro.toLowerCase()));
    if(filtrados.length === 0) {
        lista.innerHTML = `<div class="empty" style="grid-column:1/-1"><div class="empty-icon">👤</div><div class="empty-text">Nenhum cliente encontrado</div></div>`;
        return;
    }
    lista.innerHTML = filtrados.map(c => {
        const devendo = devendoCliente(c.id);
        const inicial = c.nome.charAt(0).toUpperCase();
        return `
        <div class="client-card ${devendo > 0 ? 'has-debt' : ''}" onclick="abrirFicha(${c.id})">
          <div class="client-avatar">${inicial}</div>
          <div style="flex:1;min-width:0">
            <div class="client-name">${c.nome}</div>
            <div class="client-meta">${c.telefone || 'Sem telefone'} ${c.observacao ? '· '+c.observacao : ''}</div>
          </div>
          <div class="client-debt">
            <div class="client-debt-val ${devendo > 0 ? 'gold' : 'green'}">${fmtMoeda(devendo)}</div>
            <div class="client-debt-lbl">${devendo > 0 ? 'Pendente' : 'Quitado'}</div>
          </div>
        </div>`;
    }).join('');
}

function filtrarClientes() {
    renderListaClientes(document.getElementById('busca-cliente').value);
}

function abrirFicha(cId) {
    fichaClienteId = cId;
    const c = clientes.find(x => x.id == cId);
    const devendo = devendoCliente(cId);
    const totalConsumido = totalConsumoCliente(cId);
    const totalPago = totalPagoCliente(cId);
    const qtdConsumosAbertos = historico.filter(h => h.cliente_id == cId && h.tipo==='FIADO' && h.pago==0).length;

    document.getElementById('ficha-nome').innerText = c.nome;
    document.getElementById('ficha-meta').innerText = (c.telefone || 'Sem telefone') + (c.observacao ? ' · ' + c.observacao : '');

    document.getElementById('ficha-stats').innerHTML = `
        <div class="stat-card red" style="padding:12px"><div class="stat-label">Em Aberto</div><div class="stat-val" style="font-size:18px">${fmtMoeda(devendo)}</div></div>
        <div class="stat-card gold" style="padding:12px"><div class="stat-label">Total Consumido</div><div class="stat-val" style="font-size:18px">${fmtMoeda(totalConsumido)}</div></div>
        <div class="stat-card green" style="padding:12px"><div class="stat-label">Total Pago</div><div class="stat-val" style="font-size:18px">${fmtMoeda(totalPago)}</div></div>
    `;

    // consumos
    const consumos = historico.filter(h => h.cliente_id == cId && h.tipo === 'FIADO').sort((a,b) => b.id-a.id);
    document.getElementById('ficha-consumos-body').innerHTML = consumos.length === 0
        ? `<tr><td colspan="5" style="text-align:center;padding:20px;color:var(--muted)">Sem consumos registrados</td></tr>`
        : consumos.map(h => `
            <tr>
              <td style="font-size:11px;color:var(--muted)">${fmtData(h.data)}</td>
              <td class="bold">${h.produto_nome}</td>
              <td>${h.qtd}x</td>
              <td class="gold">${fmtMoeda(h.total)}</td>
              <td>${h.pago ? '<span class="badge badge-green">Pago</span>' : '<span class="badge badge-red">Pendente</span>'}</td>
            </tr>`).join('');

    // pagamentos
    const pgtos = pagamentos.filter(p => p.cliente_id == cId).sort((a,b) => b.id-a.id);
    document.getElementById('ficha-pagamentos-body').innerHTML = pgtos.length === 0
        ? `<tr><td colspan="3" style="text-align:center;padding:20px;color:var(--muted)">Sem pagamentos registrados</td></tr>`
        : pgtos.map(p => `
            <tr>
              <td style="font-size:11px;color:var(--muted)">${fmtData(p.data)}</td>
              <td class="green">${fmtMoeda(p.valor)}</td>
              <td style="font-size:12px;color:var(--muted2)">${p.observacao || '—'}</td>
            </tr>`).join('');

    // editar
    document.getElementById('edit_cli_nome').value = c.nome;
    document.getElementById('edit_cli_tel').value  = c.telefone || '';
    document.getElementById('edit_cli_obs').value  = c.observacao || '';

    setFichaTab('consumos');
    openModal('modal-ficha-cliente');
}

function setFichaTab(t) {
    ['consumos','pagamentos','editar'].forEach(x => {
        document.getElementById('ftab-'+x).classList.toggle('active', x===t);
        document.getElementById('ftab-'+x+'-content').style.display = x===t ? 'block' : 'none';
    });
}

function cadastrarCliente() {
    const nome = document.getElementById('nc_nome').value.trim();
    if(!nome) return toast('Digite o nome!', 'red');
    const tel = document.getElementById('nc_tel').value;
    const obs = document.getElementById('nc_obs').value;
    navegar(`acao=cadastrar_cliente&nome=${encodeURIComponent(nome)}&tel=${encodeURIComponent(tel)}&obs=${encodeURIComponent(obs)}`);
}

function salvarEdicaoCliente() {
    const nome = document.getElementById('edit_cli_nome').value.trim();
    if(!nome || !fichaClienteId) return toast('Nome inválido!', 'red');
    const tel = document.getElementById('edit_cli_tel').value;
    const obs = document.getElementById('edit_cli_obs').value;
    navegar(`acao=editar_cliente&id=${fichaClienteId}&nome=${encodeURIComponent(nome)}&tel=${encodeURIComponent(tel)}&obs=${encodeURIComponent(obs)}`);
}

function arquivarCliente() {
    if(!fichaClienteId) return;
    if(confirm('Arquivar este cliente? Os dados históricos serão mantidos.')) {
        navegar(`acao=arquivar_cliente&id=${fichaClienteId}`);
    }
}

function registrarPagamento() {
    const valor = parseFloat(document.getElementById('pgto_valor').value);
    const obs   = document.getElementById('pgto_obs').value;
    if(!fichaClienteId || !valor || valor <= 0) return toast('Informe um valor válido!', 'red');
    navegar(`acao=registrar_pagamento&cliente_id=${fichaClienteId}&valor=${valor}&obs=${encodeURIComponent(obs)}`);
}

// ═══════════════════════════════════════════
// ESTOQUE
// ═══════════════════════════════════════════
function setEstoqueTab(t) {
    ['catalogo','reposicao','novo'].forEach(x => {
        document.getElementById('estoque-'+x).style.display = x===t ? 'block' : 'none';
        document.getElementById('tab-'+x.substring(0,3)).classList.toggle('active', x===t);
    });
}

function renderEstoque(filtro='') {
    const tbody = document.getElementById('tabela-estoque');
    const filtrados = produtos.filter(p => p.nome.toLowerCase().includes(filtro.toLowerCase()));
    if(filtrados.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--muted)">Nenhum produto</td></tr>`;
        return;
    }
    tbody.innerHTML = filtrados.map(p => {
        const totalUn = p.frio_unid + (p.quent_caixas * p.un_por_caixa);
        const aviso = p.frio_unid < 6 ? '<span class="badge badge-red" style="margin-left:6px">Baixo</span>' : '';
        return `
        <tr>
          <td class="bold">${catEmoji(p.categoria)} ${p.nome}${aviso}</td>
          <td><span class="badge badge-gray">${p.categoria}</span></td>
          <td class="gold">${fmtMoeda(p.preco)}</td>
          <td><span class="badge badge-cyan">${p.frio_unid} un</span></td>
          <td style="font-size:12px;color:var(--muted)">${p.quent_caixas} cx (${p.un_por_caixa}/cx)</td>
          <td class="bold">${totalUn} un</td>
          <td style="white-space:nowrap">
            <button class="btn btn-ghost btn-xs" onclick="editarProduto(${p.id})" style="margin-right:4px"><i class="fa-solid fa-pen"></i></button>
            <button class="btn btn-red btn-xs" onclick="excluirProduto(${p.id})"><i class="fa-solid fa-trash"></i></button>
          </td>
        </tr>`;
    }).join('');
}

function filtrarProdutos() {
    renderEstoque(document.getElementById('busca-prod').value);
}

function renderNivelEstoques() {
    const el = document.getElementById('nivel-estoques');
    el.innerHTML = produtos.map(p => {
        const totalUn = p.frio_unid + (p.quent_caixas * p.un_por_caixa);
        const max = Math.max(totalUn, 100);
        const pct = Math.min(100, (p.frio_unid / max) * 100);
        const cor = p.frio_unid < 6 ? 'var(--red)' : p.frio_unid < 12 ? 'var(--amber)' : 'var(--green)';
        return `
        <div style="margin-bottom:12px">
          <div style="display:flex;justify-content:space-between;margin-bottom:4px">
            <span style="font-size:13px;color:var(--text)">${catEmoji(p.categoria)} ${p.nome}</span>
            <span style="font-size:12px;color:var(--muted2)">${p.frio_unid} frio / ${p.quent_caixas} cx quente</span>
          </div>
          <div class="stock-bar"><div class="stock-fill" style="width:${pct}%;background:${cor}"></div></div>
        </div>`;
    }).join('');
}

function editarProduto(id) {
    const p = produtos.find(x => x.id === id);
    if(!p) return;
    document.getElementById('prod_edit_id').value = p.id;
    document.getElementById('prod_nome').value   = p.nome;
    document.getElementById('prod_preco').value  = p.preco;
    document.getElementById('prod_cat').value    = p.categoria;
    document.getElementById('prod_frio').value   = p.frio_unid;
    document.getElementById('prod_quent').value  = p.quent_caixas;
    document.getElementById('prod_un_cx').value  = p.un_por_caixa;
    document.getElementById('form-prod-title').innerHTML = '<span class="dot" style="background:var(--amber)"></span>Editar Produto';
    document.getElementById('btn-salvar-prod').innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Atualizar';
    document.getElementById('btn-cancel-edit').style.display = 'inline-flex';
    setEstoqueTab('novo');
}

function cancelarEdicaoProd() {
    document.getElementById('prod_edit_id').value = '';
    document.getElementById('prod_nome').value   = '';
    document.getElementById('prod_preco').value  = '';
    document.getElementById('prod_frio').value   = '0';
    document.getElementById('prod_quent').value  = '0';
    document.getElementById('prod_un_cx').value  = '1';
    document.getElementById('form-prod-title').innerHTML = '<span class="dot" style="background:var(--gold)"></span>Novo Produto';
    document.getElementById('btn-salvar-prod').innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Salvar Produto';
    document.getElementById('btn-cancel-edit').style.display = 'none';
}

function salvarProduto() {
    const id    = document.getElementById('prod_edit_id').value;
    const nome  = document.getElementById('prod_nome').value.trim();
    const preco = document.getElementById('prod_preco').value;
    const cat   = document.getElementById('prod_cat').value;
    const frio  = document.getElementById('prod_frio').value;
    const quent = document.getElementById('prod_quent').value;
    const un_cx = document.getElementById('prod_un_cx').value;
    if(!nome || !preco) return toast('Preencha Nome e Preço!', 'red');
    const acao = id ? 'editar_produto' : 'cadastrar_produto';
    navegar(`acao=${acao}&id=${id}&nome=${encodeURIComponent(nome)}&preco=${preco}&cat=${encodeURIComponent(cat)}&frio=${frio}&quent=${quent}&un_cx=${un_cx}`);
}

function excluirProduto(id) {
    if(confirm('Excluir este produto do catálogo?')) navegar(`acao=excluir_produto&id=${id}`);
}

function reporEstoque() {
    const id   = document.getElementById('rep_prod').value;
    const frio = document.getElementById('rep_frio').value;
    const quent= document.getElementById('rep_quent').value;
    if(!id) return toast('Selecione o produto!','red');
    navegar(`acao=repor_estoque&id=${id}&frio=${frio}&quent=${quent}`);
}

// ═══════════════════════════════════════════
// RELATÓRIO
// ═══════════════════════════════════════════
function renderRelatorio() {
    const totalGeral = historico.reduce((s,h) => s + h.total, 0);
    const totalAV    = historico.filter(h => h.tipo==='A_VISTA').reduce((s,h) => s + h.total, 0);
    const totalFiado = historico.filter(h => h.tipo==='FIADO').reduce((s,h) => s + h.total, 0);
    const totalRecebido = pagamentos.reduce((s,p) => s + p.valor, 0);
    document.getElementById('stats-relatorio').innerHTML = `
        <div class="stat-card gold"><div class="stat-label">Faturamento Total</div><div class="stat-val">${fmtMoeda(totalGeral)}</div></div>
        <div class="stat-card green"><div class="stat-label">Recebido à Vista</div><div class="stat-val">${fmtMoeda(totalAV)}</div></div>
        <div class="stat-card cyan"><div class="stat-label">Pago nas Fichas</div><div class="stat-val">${fmtMoeda(totalRecebido)}</div></div>
        <div class="stat-card red"><div class="stat-label">Ainda em Aberto</div><div class="stat-val">${fmtMoeda(totalFiado - totalRecebido)}</div></div>
    `;

    // ranking devedores
    const devedores = clientes.map(c => ({nome: c.nome, deve: devendoCliente(c.id)}))
        .filter(x => x.deve > 0).sort((a,b) => b.deve - a.deve).slice(0, 8);
    document.getElementById('ranking-devedores').innerHTML = devedores.length === 0
        ? `<div class="empty"><div class="empty-icon">🎉</div><div class="empty-text">Ninguém deve!</div></div>`
        : devedores.map((d, i) => `
            <div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04)">
              <span style="font-size:12px;color:var(--muted);width:18px">${i+1}.</span>
              <span style="flex:1;font-size:13px;color:var(--text);font-weight:500">${d.nome}</span>
              <span style="font-family:'Syne',sans-serif;font-weight:700;color:var(--gold2)">${fmtMoeda(d.deve)}</span>
            </div>`).join('');

    // ranking produtos
    const contagem = {};
    historico.forEach(h => { contagem[h.produto_nome] = (contagem[h.produto_nome] || 0) + h.qtd; });
    const ranking = Object.entries(contagem).sort((a,b) => b[1]-a[1]).slice(0,8);
    document.getElementById('ranking-produtos').innerHTML = ranking.length === 0
        ? `<div class="empty"><div class="empty-icon">📦</div><div class="empty-text">Sem vendas ainda</div></div>`
        : ranking.map(([nome, qtd], i) => `
            <div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04)">
              <span style="font-size:12px;color:var(--muted);width:18px">${i+1}.</span>
              <span style="flex:1;font-size:13px;color:var(--text);font-weight:500">${nome}</span>
              <span class="badge badge-cyan">${qtd} un</span>
            </div>`).join('');

    // histórico global
    const tbody = document.getElementById('tabela-historico-global');
    const sorted = [...historico].sort((a,b) => b.id-a.id);
    tbody.innerHTML = sorted.map(h => {
        const cli = clientes.find(c => c.id == h.cliente_id);
        const tipo = h.tipo === 'FIADO' ? `<span class="badge badge-gold">Fiado</span>` : `<span class="badge badge-green">À Vista</span>`;
        const status = h.pago ? `<span class="badge badge-green">Pago</span>` : (h.tipo==='FIADO' ? `<span class="badge badge-red">Pendente</span>` : `<span class="badge badge-green">OK</span>`);
        return `
        <tr>
          <td style="font-size:11px;color:var(--muted)">${fmtData(h.data)}</td>
          <td>${cli ? cli.nome : '<span style="color:var(--muted)">Avulso</span>'}</td>
          <td class="bold">${h.produto_nome}</td>
          <td>${h.qtd}x</td>
          <td class="gold">${fmtMoeda(h.total)}</td>
          <td>${tipo}</td>
          <td>${status}</td>
        </tr>`;
    }).join('');
}

// ═══════════════════════════════════════════
// MODALS
// ═══════════════════════════════════════════
function openModal(id) {
    document.getElementById(id).classList.add('open');
}
function closeModal(id) {
    document.getElementById(id).classList.remove('open');
}
document.querySelectorAll('.modal-overlay').forEach(el => {
    el.addEventListener('click', e => { if(e.target === el) el.classList.remove('open'); });
});

// ═══════════════════════════════════════════
// TOAST
// ═══════════════════════════════════════════
function toast(msg, type='green') {
    const area = document.getElementById('toast-area');
    const el = document.createElement('div');
    const icon = type === 'green' ? 'fa-check-circle' : 'fa-circle-exclamation';
    el.className = `toast ${type}`;
    el.innerHTML = `<i class="fa-solid ${icon}" style="color:var(--${type});font-size:16px"></i> ${msg}`;
    area.appendChild(el);
    setTimeout(() => el.remove(), 3500);
}

// ═══════════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════════
function navegar(params) {
    window.parent.location.search = '?' + params;
}

// ═══════════════════════════════════════════
// START
// ═══════════════════════════════════════════
init();
</script>
</body>
</html>
"""

html_final = (HTML
    .replace("__PRODUTOS_JSON__", produtos_json)
    .replace("__CLIENTES_JSON__", clis_json)
    .replace("__HISTORICO_JSON__", historico_json)
    .replace("__PAGAMENTOS_JSON__", pagamentos_json)
)

components.html(html_final, height=950, scrolling=False)
