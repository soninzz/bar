import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import pandas as pd
import json

# --- CONFIGURAÇÃO DA VITRINE ---
st.set_page_config(page_title="Bar do Querido — Hub", layout="wide", initial_sidebar_state="collapsed")

# Limpeza visual dos elementos nativos do Streamlit
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {padding: 0rem !important; max-width: 100% !important;}
        iframe {border: none !important;}
        body {background-color: #06080c !important;}
    </style>
""", unsafe_allow_html=True)

# --- BANCO DE DADOS (SQLITE) ---
DB_NAME = 'bar_elite.db'

def executar_query(query, params=()):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS produtos 
                 (id INTEGER PRIMARY KEY, nome TEXT, preco REAL, quent_caixas INTEGER, frio_unid INTEGER, un_por_caixa INTEGER, categoria TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS clientes 
                 (id INTEGER PRIMARY KEY, nome TEXT, saldo_devedor REAL DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS vendas 
                 (id INTEGER PRIMARY KEY, data TEXT, total REAL, tipo TEXT, cliente_id INTEGER)''')
    
    c.execute("SELECT count(*) FROM produtos")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO produtos (nome, preco, quent_caixas, frio_unid, un_por_caixa, categoria) VALUES (?,?,?,?,?,?)", [
            ('Brahma Duplo Malte 350ml', 6.00, 12, 48, 24, 'Cerveja'),
            ('Heineken Long Neck 330ml', 10.00, 8, 12, 12, 'Cerveja'),
            ('Coca-Cola Lata Zero', 6.00, 4, 24, 12, 'Refrigerante'),
            ('Amendoim Mendorato 120g', 6.00, 0, 30, 1, 'Salgados')
        ])
        c.executemany("INSERT INTO clientes (nome, saldo_devedor) VALUES (?,?)", [
            ('Marcão Engenharia', 180.00),
            ('Carlos Silva (Ficha 14)', 45.50)
        ])
    conn.commit()
    conn.close()

init_db()

# --- TRATAMENTO DE REQUISIÇÕES DO FRONT-END ---
query_params = st.query_params

if "acao" in query_params:
    acao = query_params["acao"]
    
    # Clientes: Cadastrar
    if acao == "cadastrar_cliente" and "nome" in query_params:
        executar_query("INSERT INTO clientes (nome, saldo_devedor) VALUES (?, 0.0)", (query_params["nome"],))
        
    # Vendas: Lançar
    elif acao == "lancar_venda" and "produto_id" in query_params:
        p_id = int(query_params["produto_id"])
        qtd = int(query_params["qtd"])
        c_id = query_params["cliente_id"]
        
        conn = sqlite3.connect(DB_NAME)
        p_info = pd.read_sql(f"SELECT preco FROM produtos WHERE id = {p_id}", conn)
        conn.close()
        
        if not p_info.empty:
            total_venda = p_info.iloc[0]['preco'] * qtd
            executar_query("UPDATE produtos SET frio_unid = MAX(0, frio_unid - ?) WHERE id = ?", (qtd, p_id))
            if c_id != "AVULSO":
                executar_query("UPDATE clientes SET saldo_devedor = saldo_devedor + ? WHERE id = ?", (total_venda, int(c_id)))
                executar_query("INSERT INTO vendas (data, total, tipo, cliente_id) VALUES (datetime('now'), ?, 'FIADO', ?)", (total_venda, int(c_id)))
            else:
                executar_query("INSERT INTO vendas (data, total, tipo, cliente_id) VALUES (datetime('now'), ?, 'A VISTA', NULL)", (total_venda,))

    # Produtos: Cadastrar
    elif acao == "cadastrar_produto":
        executar_query("""
            INSERT INTO produtos (nome, preco, quent_caixas, frio_unid, un_por_caixa, categoria) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (query_params["nome"], float(query_params["preco"]), int(query_params["quent"]), int(query_params["frio"]), int(query_params["un_cx"]), query_params["cat"]))

    # Produtos: Editar
    elif acao == "editar_produto":
        executar_query("""
            UPDATE produtos 
            SET nome = ?, preco = ?, quent_caixas = ?, frio_unid = ?, un_por_caixa = ?, categoria = ? 
            WHERE id = ?
        """, (query_params["nome"], float(query_params["preco"]), int(query_params["quent"]), int(query_params["frio"]), int(query_params["un_cx"]), query_params["cat"], int(query_params["id"])))

    # Produtos: Excluir
    elif acao == "excluir_produto":
        executar_query("DELETE FROM produtos WHERE id = ?", (int(query_params["id"]),))

    # Limpa a URL e força o recarregamento limpo do Streamlit
    st.query_params.clear()
    st.rerun()

# --- BUSCA DADOS ATUALIZADOS ---
conn = sqlite3.connect(DB_NAME)
prods_df = pd.read_sql("SELECT * FROM produtos", conn)
clis_df = pd.read_sql("SELECT * FROM clientes", conn)
conn.close()

produtos_json = prods_df.to_json(orient="records")
clientes_json = clis_df.to_json(orient="records")

# --- INTERFACE ---
html_premium_ui = """
<!DOCTYPE html>
<html lang="pt-br" class="h-full">
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: { sans: ['Plus Jakarta Sans', 'sans-serif'] },
                    colors: { darkBg: '#06080c', panelBg: 'rgba(17, 22, 34, 0.65)', borderGlow: '#1f293d', brandNeon: '#10b981', brandIce: '#06b6d4' }
                }
            }
        }
    </script>
    <style>
        body { background-color: #06080c; color: #f3f4f6; overflow-x: hidden; font-family: 'Plus Jakarta Sans', sans-serif; }
        .glass-panel { background: rgba(13, 18, 30, 0.45); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.04); }
        .nav-link-active { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); color: #fff; }
    </style>
</head>
<body class="h-full antialiased">

    <div class="flex h-screen overflow-hidden">
        
        <!-- SIDEBAR -->
        <div class="w-64 glass-panel border-r border-gray-800/40 flex flex-col justify-between p-6">
            <div>
                <div class="flex items-center gap-3 px-2 mb-8">
                    <div class="h-10 w-10 rounded-xl bg-gradient-to-tr from-brandNeon to-brandIce flex items-center justify-center">
                        <i class="fa-solid fa-crown text-darkBg font-bold text-lg"></i>
                    </div>
                    <div>
                        <h1 class="text-sm font-bold tracking-tight text-white uppercase">Bar do Querido</h1>
                        <span class="text-[10px] font-medium text-brandNeon tracking-widest uppercase">Premium OS</span>
                    </div>
                </div>
                
                <nav class="space-y-1" id="sidebar-nav">
                    <button onclick="mudarAba('balcao')" id="btn-balcao" class="w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-xl text-gray-400 hover:text-white hover:bg-white/5 transition-all text-left">
                        <i class="fa-solid fa-square-poll-vertical text-brandNeon"></i> Balcão de Vendas
                    </button>
                    <button onclick="mudarAba('fichas')" id="btn-fichas" class="w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-xl text-gray-400 hover:text-white hover:bg-white/5 transition-all text-left">
                        <i class="fa-solid fa-address-book text-brandIce"></i> Fichas & Cadastro
                    </button>
                    <button onclick="mudarAba('estoque')" id="btn-estoque" class="w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-xl text-gray-400 hover:text-white hover:bg-white/5 transition-all text-left">
                        <i class="fa-solid fa-cubes text-amber-500"></i> Gestão de Produtos
                    </button>
                </nav>
            </div>
        </div>

        <!-- CONTEÚDO -->
        <div class="flex-1 overflow-y-auto p-8">
            
            <div class="flex justify-between items-center mb-8">
                <div>
                    <h2 class="text-2xl font-bold tracking-tight text-white" id="nome-da-tela">Balcão de Vendas</h2>
                    <p class="text-xs text-gray-500 mt-0.5">Terminal operacional integrado.</p>
                </div>
                <div class="glass-panel px-4 py-2.5 rounded-xl border border-gray-800 text-xs font-semibold text-gray-400">
                    <span id="live-clock">Sincronizando...</span>
                </div>
            </div>

            <!-- ================= TELA 1: BALCÃO ================= -->
            <div id="tela-balcao" class="space-y-8 screen-content">
                <div class="glass-panel rounded-2xl p-6 border border-gray-800/40">
                    <div class="flex items-center gap-2 mb-6">
                        <i class="fa-solid fa-circle-plus text-brandNeon text-lg"></i>
                        <h3 class="text-sm font-bold tracking-wider uppercase text-gray-300">Lançar Consumo</h3>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-12 gap-4">
                        <div class="md:col-span-6">
                            <label class="block text-[10px] font-bold text-gray-500 uppercase mb-2">Produto</label>
                            <select id="venda_produto" class="w-full bg-darkBg border border-gray-800 rounded-xl px-4 py-3 text-sm text-gray-200 focus:outline-none focus:border-brandNeon"></select>
                        </div>
                        <div class="md:col-span-2">
                            <label class="block text-[10px] font-bold text-gray-500 uppercase mb-2">Qtd</label>
                            <input id="venda_qtd" type="number" min="1" value="1" class="w-full bg-darkBg border border-gray-800 rounded-xl px-4 py-3 text-sm text-center text-gray-200 focus:outline-none focus:border-brandNeon">
                        </div>
                        <div class="md:col-span-4">
                            <label class="block text-[10px] font-bold text-gray-500 uppercase mb-2">Ficha da Conta</label>
                            <select id="venda_cliente" class="w-full bg-darkBg border border-gray-800 rounded-xl px-4 py-3 text-sm text-gray-200 focus:outline-none focus:border-brandNeon">
                                <option value="AVULSO">💰 Venda Direta (Pago na Hora)</option>
                            </select>
                        </div>
                        <div class="md:col-span-12 mt-2">
                            <button onclick="enviarVenda()" class="w-full bg-gradient-to-r from-brandNeon to-emerald-600 text-darkBg font-bold text-xs tracking-widest uppercase py-4 rounded-xl shadow-lg hover:from-emerald-500 transition-all">
                                Confirmar Operação
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- ================= TELA 2: FICHAS ================= -->
            <div id="tela-fichas" class="space-y-8 screen-content hidden">
                <div class="glass-panel rounded-2xl p-6 border border-gray-800/40">
                    <div class="flex items-center gap-2 mb-4">
                        <i class="fa-solid fa-user-plus text-brandIce text-lg"></i>
                        <h3 class="text-sm font-bold tracking-wider uppercase text-gray-300">Abrir Nova Ficha</h3>
                    </div>
                    <div class="flex gap-4">
                        <input id="novo_cliente_nome" type="text" placeholder="Nome do Cliente ou Número do Cartão" class="flex-1 bg-darkBg border border-gray-800 rounded-xl px-4 py-3 text-sm text-gray-200 focus:outline-none focus:border-brandIce">
                        <button onclick="cadastrarCliente()" class="bg-brandIce hover:bg-cyan-500 text-darkBg font-bold text-xs tracking-wider uppercase px-6 rounded-xl transition-all">
                            Abrir Conta
                        </button>
                    </div>
                </div>

                <div class="glass-panel rounded-2xl p-6 border border-gray-800/40">
                    <table class="w-full text-left text-sm text-gray-400">
                        <thead class="text-[10px] tracking-widest uppercase text-gray-500 border-b border-gray-800/60">
                            <tr>
                                <th class="py-3 px-4">Cliente / Ficha</th>
                                <th class="py-3 px-4 text-right">Saldo Devedor</th>
                                <th class="py-3 px-4 text-center">Ações</th>
                            </tr>
                        </thead>
                        <tbody id="tabela_fichas_corpo" class="divide-y divide-gray-800/40"></tbody>
                    </table>
                </div>
            </div>

            <!-- ================= TELA 3: GESTÃO DE PRODUTOS ================= -->
            <div id="tela-estoque" class="space-y-8 screen-content hidden">
                <div class="glass-panel rounded-2xl p-6 border border-gray-800/40">
                    <div class="flex items-center justify-between mb-6">
                        <div class="flex items-center gap-2">
                            <i class="fa-solid fa-box-open text-amber-500 text-lg"></i>
                            <h3 class="text-sm font-bold tracking-wider uppercase text-gray-300" id="form-produto-titulo">Adicionar Produto ao Catálogo</h3>
                        </div>
                        <button onclick="limparFormProduto()" id="btn-cancelar-edicao" class="hidden text-xs font-semibold text-red-400 hover:underline">Cancelar Edição</button>
                    </div>
                    
                    <input type="hidden" id="prod_id">
                    <div class="grid grid-cols-1 md:grid-cols-12 gap-4">
                        <div class="md:col-span-4">
                            <label class="block text-[10px] font-bold text-gray-500 uppercase mb-2">Nome do Item</label>
                            <input id="prod_nome" type="text" placeholder="Ex: Heineken Long Neck" class="w-full bg-darkBg border border-gray-800 rounded-xl px-4 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-amber-500">
                        </div>
                        <div class="md:col-span-2">
                            <label class="block text-[10px] font-bold text-gray-500 uppercase mb-2">Preço de Venda</label>
                            <input id="prod_preco" type="number" step="0.01" placeholder="0.00" class="w-full bg-darkBg border border-gray-800 rounded-xl px-4 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-amber-500">
                        </div>
                        <div class="md:col-span-2">
                            <label class="block text-[10px] font-bold text-gray-500 uppercase mb-2">Categoria</label>
                            <select id="prod_cat" class="w-full bg-darkBg border border-gray-800 rounded-xl px-4 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-amber-500">
                                <option value="Cerveja">Cerveja</option>
                                <option value="Refrigerante">Refrigerante</option>
                                <option value="Salgados">Salgados</option>
                                <option value="Doces">Doces</option>
                            </select>
                        </div>
                        <div class="md:col-span-2">
                            <label class="block text-[10px] font-bold text-gray-500 uppercase mb-2">Qtd Gelando (Frio)</label>
                            <input id="prod_frio" type="number" value="0" class="w-full bg-darkBg border border-gray-800 rounded-xl px-4 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-amber-500">
                        </div>
                        <div class="md:col-span-1">
                            <label class="block text-[10px] font-bold text-gray-500 uppercase mb-2">Caixas (Quente)</label>
                            <input id="prod_quent" type="number" value="0" class="w-full bg-darkBg border border-gray-800 rounded-xl px-4 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-amber-500">
                        </div>
                        <div class="md:col-span-1">
                            <label class="block text-[10px] font-bold text-gray-500 uppercase mb-2">Un/Caixa</label>
                            <input id="prod_un_cx" type="number" value="1" class="w-full bg-darkBg border border-gray-800 rounded-xl px-4 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-amber-500">
                        </div>
                        <div class="md:col-span-12 mt-2">
                            <button onclick="salvarProduto()" id="btn-salvar-prod" class="w-full bg-gradient-to-r from-amber-500 to-orange-600 text-darkBg font-bold text-xs tracking-widest uppercase py-3.5 rounded-xl shadow-lg hover:from-amber-400 transition-all">
                                Gravar no Catálogo
                            </button>
                        </div>
                    </div>
                </div>

                <div class="glass-panel rounded-2xl p-6 border border-gray-800/40">
                    <h3 class="text-sm font-bold tracking-wider uppercase text-gray-300 mb-4">Itens Cadastrados e Níveis de Estoque</h3>
                    <div class="overflow-x-auto">
                        <table class="w-full text-left text-sm text-gray-400">
                            <thead class="text-[10px] tracking-widest uppercase text-gray-500 border-b border-gray-800/60">
                                <tr>
                                    <th class="py-3 px-4">Item</th>
                                    <th class="py-3 px-4">Categoria</th>
                                    <th class="py-3 px-4 text-right">Preço</th>
                                    <th class="py-3 px-4 text-center">Giro (Frio)</th>
                                    <th class="py-3 px-4 text-center">Depósito (Quente)</th>
                                    <th class="py-3 px-4 text-center">Ações</th>
                                </tr>
                            </thead>
                            <tbody id="tabela_produtos_corpo" class="divide-y divide-gray-800/40"></tbody>
                        </table>
                    </div>
                </div>
            </div>

        </div>
    </div>

    <script>
        const produtos = __PRODUTOS_JSON__;
        const clientes = __CLIENTES_JSON__;

        // Função universal para injetar comandos na janela principal (ignora travas de sandbox)
        function executarAcaoGlobal(queryString) {
            const baseUrl = window.top.location.href.split('?')[0];
            window.top.location.href = baseUrl + queryString;
        }

        function mudarAba(aba) {
            document.querySelectorAll('.screen-content').forEach(el => el.classList.add('hidden'));
            document.querySelectorAll('#sidebar-nav button').forEach(el => el.classList.remove('nav-link-active'));
            localStorage.setItem('aba_ativa_bar', aba);
            
            if(aba === 'balcao') {
                document.getElementById('tela-balcao').classList.remove('hidden');
                document.getElementById('btn-balcao').classList.add('nav-link-active');
                document.getElementById('nome-da-tela').innerText = "Balcão de Vendas";
            } else if(aba === 'fichas') {
                document.getElementById('tela-fichas').classList.remove('hidden');
                document.getElementById('btn-fichas').classList.add('nav-link-active');
                document.getElementById('nome-da-tela').innerText = "Fichas & Controle de Fiado";
            } else if(aba === 'estoque') {
                document.getElementById('tela-estoque').classList.remove('hidden');
                document.getElementById('btn-estoque').classList.add('nav-link-active');
                document.getElementById('nome-da-tela').innerText = "Controle de Estoque & Catálogo";
            }
        }

        function renderizarDados() {
            const selectProd = document.getElementById('venda_produto');
            const selectCli = document.getElementById('venda_cliente');
            const tabelaFichas = document.getElementById('tabela_fichas_corpo');
            const tabelaProdutos = document.getElementById('tabela_produtos_corpo');

            produtos.forEach(p => {
                selectProd.innerHTML += `<option value="${p.id}">🍺 ${p.nome} — R$ ${p.preco.toFixed(2)}</option>`;
            });

            clientes.forEach(c => {
                selectCli.innerHTML += `<option value="${c.id}">👤 Ficha: ${c.nome}</option>`;
                tabelaFichas.innerHTML += `
                    <tr class="hover:bg-white/[0.01]">
                        <td class="py-3 px-4 font-semibold text-gray-200">${c.nome}</td>
                        <td class="py-3 px-4 text-right font-bold \${c.saldo_devedor > 0 ? 'text-amber-400' : 'text-gray-500'}">R$ \${c.saldo_devedor.toFixed(2)}</td>
                        <td class="py-3 px-4 text-center">
                            <button class="text-xs font-bold text-brandNeon bg-brandNeon/10 border border-brandNeon/20 px-3 py-1 rounded-lg hover:bg-brandNeon hover:text-black transition-all">Receber</button>
                        </td>
                    </tr>
                `;
            });

            produtos.forEach(p => {
                tabelaProdutos.innerHTML += `
                    <tr class="hover:bg-white/[0.01]">
                        <td class="py-3 px-4 font-semibold text-gray-200">${p.nome}</td>
                        <td class="py-3 px-4 text-xs text-gray-500">${p.categoria}</td>
                        <td class="py-3 px-4 text-right font-bold text-gray-300">R$ \${p.preco.toFixed(2)}</td>
                        <td class="py-3 px-4 text-center"><span class="px-2 py-0.5 bg-brandIce/10 text-brandIce text-xs rounded-md font-bold">\${p.frio_unid} un</span></td>
                        <td class="py-3 px-4 text-center"><span class="text-xs text-gray-400">\${p.quent_caixas} Cx (\${p.un_por_caixa} un/cx)</span></td>
                        <td class="py-3 px-4 text-center space-x-2">
                            <button onclick="carregarProdutoEdicao(\${p.id})" class="text-xs font-bold text-amber-400 bg-amber-400/10 hover:bg-amber-400 hover:text-black px-2.5 py-1 rounded transition-all"><i class="fa-solid fa-pen"></i></button>
                            <button onclick="excluirProduto(\\${p.id})" class="text-xs font-bold text-red-400 bg-red-400/10 hover:bg-red-400 hover:text-white px-2.5 py-1 rounded transition-all"><i class="fa-solid fa-trash"></i></button>
                        </td>
                    </tr>
                `;
            });
        }

        // --- SUBMITS CORRIGIDOS COM EXECUTARACAOBLOBAL ---
        function cadastrarCliente() {
            const nome = document.getElementById('novo_cliente_nome').value;
            if(!nome) return alert('Digite o nome do cliente!');
            executarAcaoGlobal(`?acao=cadastrar_cliente&nome=\${encodeURIComponent(nome)}`);
        }

        function enviarVenda() {
            const pId = document.getElementById('venda_produto').value;
            const qtd = document.getElementById('venda_qtd').value;
            const cId = document.getElementById('venda_cliente').value;
            executarAcaoGlobal(`?acao=lancar_venda&produto_id=\${pId}&qtd=\${qtd}&cliente_id=\${cId}`);
        }

        function salvarProduto() {
            const id = document.getElementById('prod_id').value;
            const nome = document.getElementById('prod_nome').value;
            const preco = document.getElementById('prod_preco').value;
            const cat = document.getElementById('prod_cat').value;
            const frio = document.getElementById('prod_frio').value;
            const quent = document.getElementById('prod_quent').value;
            const un_cx = document.getElementById('prod_un_cx').value;

            if(!nome || !preco) return alert("Preencha Nome e Preço!");

            const acao = id ? "editar_produto" : "cadastrar_produto";
            executarAcaoGlobal(`?acao=\${acao}&id=\${id}&nome=\${encodeURIComponent(nome)}&preco=\${preco}&cat=\${cat}&frio=\${frio}&quent=\${quent}&un_cx=\${un_cx}`);
        }

        function excluirProduto(id) {
            if(confirm("Tem certeza que deseja apagar este item permanentemente do catálogo?")) {
                executarAcaoGlobal(`?acao=excluir_produto&id=\${id}`);
            }
        }

        function carregarProdutoEdicao(id) {
            const p = produtos.find(prod => prod.id === id);
            if (!p) return;
            document.getElementById('prod_id').value = p.id;
            document.getElementById('prod_nome').value = p.nome;
            document.getElementById('prod_preco').value = p.preco;
            document.getElementById('prod_cat').value = p.categoria;
            document.getElementById('prod_frio').value = p.frio_unid;
            document.getElementById('prod_quent').value = p.quent_caixas;
            document.getElementById('prod_un_cx').value = p.un_por_caixa;
            document.getElementById('form-produto-titulo').innerText = "Editar Parâmetros do Item";
            document.getElementById('btn-cancelar-edicao').classList.remove('hidden');
            document.getElementById('btn-salvar-prod').innerText = "Atualizar Registro";
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

        function limparFormProduto() {
            document.getElementById('prod_id').value = "";
            document.getElementById('prod_nome').value = "";
            document.getElementById('prod_preco').value = "";
            document.getElementById('prod_frio').value = "0";
            document.getElementById('prod_quent').value = "0";
            document.getElementById('prod_un_cx').value = "1";
            document.getElementById('form-produto-titulo').innerText = "Adicionar Produto ao Catálogo";
            document.getElementById('btn-cancelar-edicao').classList.add('hidden');
            document.getElementById('btn-salvar-prod').innerText = "Gravar no Catálogo";
        }

        setInterval(() => {
            document.getElementById('live-clock').innerText = new Date().toLocaleDateString('pt-BR') + ' — ' + new Date().toLocaleTimeString('pt-BR');
        }, 1000);

        // Recuperação inteligente de estado da aba ativa usando localStorage
        const params = new URLSearchParams(window.top.location.search);
        const acaoAtual = params.get('acao');
        
        let abaPadrao = localStorage.getItem('aba_ativa_bar') || 'balcao';
        
        if (acaoAtual) {
            if (acaoAtual.includes('cliente')) abaPadrao = 'fichas';
            if (acaoAtual.includes('produto')) abaPadrao = 'estoque';
        }
        
        mudarAba(abaPadrao);
        renderizarDados();
    </script>
</body>
</html>
"""

html_final = html_premium_ui.replace("__PRODUTOS_JSON__", produtos_json).replace("__CLIENTES_JSON__", clientes_json)
components.html(html_final, height=900, scrolling=True)
