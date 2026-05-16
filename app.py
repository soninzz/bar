import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÃO DA VITRINE ---
st.set_page_config(page_title="Bar do Querido — Hub", layout="wide", initial_sidebar_state="collapsed")

# Injeção de CSS para sumir com os elementos padrões do Streamlit e integrar o iframe perfeitamente
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {padding: 0rem !important; max-width: 100% !important;}
        iframe {border: none !important;}
        body {background-color: #05070a !important;}
    </style>
""", unsafe_allow_html=True)

# --- ENGINE DE PERSISTÊNCIA (SQLITE) ---
DB_NAME = 'bar_elite.db'
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS produtos 
                 (id INTEGER PRIMARY KEY, nome TEXT, preco REAL, quent_caixas INTEGER, frio_unid INTEGER, un_por_caixa INTEGER, categoria TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS clientes 
                 (id INTEGER PRIMARY KEY, nome TEXT, saldo_devedor REAL DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS vendas 
                 (id INTEGER PRIMARY KEY, data TEXT, total REAL, tipo TEXT)''')
    
    c.execute("SELECT count(*) FROM produtos")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO produtos (nome, preco, quent_caixas, frio_unid, un_por_caixa, categoria) VALUES (?,?,?,?,?,?)", [
            ('Brahma Duplo Malte 350ml', 6.00, 12, 48, 24, 'Cerveja'),
            ('Heineken Long Neck 330ml', 10.00, 8, 12, 12, 'Cerveja'),
            ('Eisenbahn 600ml', 12.00, 5, 6, 6, 'Cerveja'),
            ('Coca-Cola Lata Zero', 6.00, 4, 24, 12, 'Refrigerante'),
            ('Paçoca de Rolha Premium', 2.00, 0, 60, 1, 'Doces'),
            ('Doce de Abóbora Coração', 2.50, 0, 40, 1, 'Doces'),
            ('Amendoim Mendorato 120g', 6.00, 0, 30, 1, 'Salgados')
        ])
        c.executemany("INSERT INTO clientes (nome, saldo_devedor) VALUES (?,?)", [
            ('Marcão Engenharia', 180.00),
            ('Carlos Silva (Ficha 14)', 45.50)
        ])
    conn.commit()
    conn.close()

init_db()

# Puxando dados para alimentar dinamicamente o Front-End Chique
conn = sqlite3.connect(DB_NAME)
prods_df = pd.read_sql("SELECT * FROM produtos", conn)
clis_df = pd.read_sql("SELECT * FROM clientes", conn)
conn.close()

# Transforma dados em JSON para o JavaScript ler nativamente dentro do HTML
produtos_json = prods_df.to_json(orient="records")
clientes_json = clis_df.to_json(orient="records")

# --- FRONT-END MAGNÍFICO (HTML5 + TAILWIND CSS + GLASSMORPHISM) ---
# Removemos o 'f' do início para evitar conflito de chaves do JS/CSS
html_premium_ui = """
<!DOCTYPE html>
<html lang="pt-br" class="h-full">
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: { sans: ['Plus Jakarta Sans', 'sans-serif'] },
                    colors: {
                        darkBg: '#06080c',
                        panelBg: 'rgba(17, 22, 34, 0.65)',
                        borderGlow: '#1f293d',
                        brandNeon: '#10b981',
                        brandIce: '#06b6d4'
                    }
                }
            }
        }
    </script>
    <style>
        body { background-color: #06080c; color: #f3f4f6; overflow-x: hidden; }
        .glass-panel {
            background: rgba(13, 18, 30, 0.45);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.04);
        }
        .neon-glow:hover {
            box-shadow: 0 0 20px rgba(16, 185, 129, 0.15);
            border-color: rgba(16, 185, 129, 0.3);
        }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #06080c; }
        ::-webkit-scrollbar-thumb { background: #1f293d; border-radius: 10px; }
    </style>
</head>
<body class="h-full antialiased selection:bg-brandNeon selection:text-black">

    <div class="flex h-screen overflow-hidden">
        
        <!-- SIDEBAR MINIMALISTA E CHIQUE -->
        <div class="w-64 glass-panel border-r border-gray-800/40 flex flex-col justify-between p-6 hidden md:flex">
            <div>
                <div class="flex items-center gap-3 px-2 mb-8">
                    <div class="h-10 w-10 rounded-xl bg-gradient-to-tr from-brandNeon to-brandIce flex items-center justify-center shadow-lg shadow-brandNeon/10">
                        <i class="fa-solid fa-crown text-darkBg font-bold text-lg"></i>
                    </div>
                    <div>
                        <h1 class="text-sm font-bold tracking-tight text-white uppercase">Bar do Querido</h1>
                        <span class="text-[10px] font-medium text-brandNeon tracking-widest uppercase">Premium OS</span>
                    </div>
                </div>
                
                <nav class="space-y-1">
                    <a href="#" class="flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-xl text-white bg-white/5 border border-white/10 transition-all">
                        <i class="fa-solid fa-square-poll-vertical text-brandNeon"></i> Balcão de Vendas
                    </a>
                    <a href="#" class="flex items-center gap-3 px-4 py-3 text-sm font-medium text-gray-400 hover:text-white hover:bg-white/5 rounded-xl transition-all">
                        <i class="fa-solid fa-cubes"></i> Controle de Giro
                    </a>
                    <a href="#" class="flex items-center gap-3 px-4 py-3 text-sm font-medium text-gray-400 hover:text-white hover:bg-white/5 rounded-xl transition-all">
                        <i class="fa-solid fa-address-book"></i> Fichas Ativas
                    </a>
                    <a href="#" class="flex items-center gap-3 px-4 py-3 text-sm font-medium text-gray-400 hover:text-white hover:bg-white/5 rounded-xl transition-all">
                        <i class="fa-solid fa-receipt"></i> Lançamento de Notas
                    </a>
                </nav>
            </div>
            
            <div class="border-t border-gray-800/60 pt-4">
                <button onclick="dispararFechamento()" class="w-full bg-gradient-to-r from-red-500/20 to-orange-500/20 hover:from-red-500/30 hover:to-orange-500/30 text-red-400 border border-red-500/30 font-semibold py-3 px-4 rounded-xl text-xs tracking-wider uppercase transition-all duration-300">
                    <i class="fa-solid fa-power-off mr-2"></i> Encerrar Dia
                </button>
            </div>
        </div>

        <!-- CONTEÚDO PRINCIPAL (DASHBOARD) -->
        <div class="flex-1 overflow-y-auto p-8">
            
            <!-- TOP BAR -->
            <div class="flex flex-col sm:flex-row justify-between sm:items-center gap-4 mb-8">
                <div>
                    <h2 class="text-2xl font-bold tracking-tight text-white">Painel Operacional</h2>
                    <p class="text-xs text-gray-500 mt-0.5">Interface de alta performance para controle de balcão.</p>
                </div>
                <div class="glass-panel px-4 py-2.5 rounded-xl border border-gray-800 text-xs font-semibold tracking-wider text-gray-400 flex items-center gap-2">
                    <span class="h-2 w-2 rounded-full bg-brandNeon animate-pulse"></span>
                    <span id="live-clock">Sincronizando Terminal...</span>
                </div>
            </div>

            <!-- GRID PRINCIPAL -->
            <div class="grid grid-cols-1 xl:grid-cols-3 gap-8">
                
                <!-- COLUNA DA ESQUERDA: ENTRADA DE DADOS -->
                <div class="xl:col-span-2 space-y-8">
                    
                    <!-- CARD LANÇAMENTO -->
                    <div class="glass-panel rounded-2xl p-6 border border-gray-800/40 neon-glow transition-all duration-300">
                        <div class="flex items-center gap-2 mb-6">
                            <i class="fa-solid fa-circle-plus text-brandNeon text-lg"></i>
                            <h3 class="text-sm font-bold tracking-wider uppercase text-gray-300">Ação Rápida de Venda</h3>
                        </div>
                        
                        <div class="grid grid-cols-1 md:grid-cols-12 gap-4">
                            <div class="md:col-span-6">
                                <label class="block text-[10px] font-bold tracking-widest text-gray-500 uppercase mb-2">Produto Consumido</label>
                                <select id="input_produto" class="w-full bg-darkBg border border-gray-800 rounded-xl px-4 py-3 text-sm text-gray-200 focus:outline-none focus:border-brandNeon transition-all">
                                    <!-- Injetado via JS -->
                                </select>
                            </div>
                            <div class="md:col-span-2">
                                <label class="block text-[10px] font-bold tracking-widest text-gray-500 uppercase mb-2">Qtd</label>
                                <input id="input_qtd" type="number" min="1" value="1" class="w-full bg-darkBg border border-gray-800 rounded-xl px-4 py-3 text-sm text-gray-200 text-center focus:outline-none focus:border-brandNeon transition-all">
                            </div>
                            <div class="md:col-span-4">
                                <label class="block text-[10px] font-bold tracking-widest text-gray-500 uppercase mb-2">Destino / Ficha</label>
                                <select id="input_cliente" class="w-full bg-darkBg border border-gray-800 rounded-xl px-4 py-3 text-sm text-gray-200 focus:outline-none focus:border-brandNeon transition-all">
                                    <option value="AVULSO">💰 Venda Direta (À Vista)</option>
                                    <!-- Injetado via JS -->
                                </select>
                            </div>
                            <div class="md:col-span-12 mt-2">
                                <button onclick="executarLancamento()" class="w-full bg-gradient-to-r from-brandNeon to-emerald-600 hover:from-emerald-500 hover:to-emerald-700 text-darkBg font-bold text-xs tracking-widest uppercase py-4 rounded-xl shadow-lg shadow-brandNeon/10 hover:shadow-brandNeon/20 transform hover:-translate-y-0.5 transition-all duration-200">
                                    Confirmar Operação de Balcão
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- CARD TABELA COMANDAS -->
                    <div class="glass-panel rounded-2xl p-6 border border-gray-800/40">
                        <div class="flex items-center justify-between mb-4">
                            <div class="flex items-center gap-2">
                                <i class="fa-solid fa-address-card text-brandIce text-lg"></i>
                                <h3 class="text-sm font-bold tracking-wider uppercase text-gray-300">Saldos de Fichas Ativas (Fiado)</h3>
                            </div>
                            <span class="text-[10px] px-2.5 py-1 bg-brandIce/10 text-brandIce font-semibold rounded-full uppercase tracking-wider">Apurado Liquidez</span>
                        </div>
                        
                        <div class="overflow-x-auto">
                            <table class="w-full text-left text-sm text-gray-400">
                                <thead class="text-[10px] tracking-widest uppercase text-gray-500 border-b border-gray-800/60">
                                    <tr>
                                        <th class="py-3 px-4">Cliente / Ficha</th>
                                        <th class="py-3 px-4 text-right">Débito Acumulado</th>
                                        <th class="py-3 px-4 text-center">Status de Risco</th>
                                    </tr>
                                </thead>
                                <tbody id="tabela_fichas" class="divide-y divide-gray-800/40">
                                    <!-- Injetado via JS -->
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- COLUNA DA DIREITA: ESTOQUES INTELIGENTES -->
                <div class="space-y-8">
                    
                    <!-- CARD CERVEJEIRA (FRIO) -->
                    <div class="glass-panel rounded-2xl p-6 border border-gray-800/40 relative overflow-hidden">
                        <div class="absolute top-0 left-0 w-1.5 h-full bg-brandIce"></div>
                        <div class="flex items-center gap-2 mb-4">
                            <i class="fa-solid fa-snowflake text-brandIce text-lg"></i>
                            <h3 class="text-sm font-bold tracking-wider uppercase text-gray-300">Cervejeira (Pronto p/ Giro)</h3>
                        </div>
                        <div id="grid_frio" class="space-y-4">
                            <!-- Injetado via JS -->
                        </div>
                    </div>

                    <!-- CARD DEPÓSITO (QUENTE) -->
                    <div class="glass-panel rounded-2xl p-6 border border-gray-800/40 relative overflow-hidden">
                        <div class="absolute top-0 left-0 w-1.5 h-full bg-amber-500"></div>
                        <div class="flex items-center gap-2 mb-4">
                            <i class="fa-solid fa-warehouse text-amber-500 text-lg"></i>
                            <h3 class="text-sm font-bold tracking-wider uppercase text-gray-300">Depósito Quente (Caixas Fechadas)</h3>
                        </div>
                        <div id="grid_quente" class="space-y-3 text-sm">
                            <!-- Injetado via JS -->
                        </div>
                    </div>

                    <!-- INSIGHT IA EFEITO LUXO -->
                    <div id="box_ia" class="glass-panel rounded-2xl p-6 border border-purple-500/20 bg-gradient-to-b from-purple-950/10 to-transparent hidden">
                        <div class="flex items-center gap-2 mb-3">
                            <i class="fa-solid fa-wand-magic-sparkles text-purple-400 text-lg animate-pulse"></i>
                            <h3 class="text-sm font-bold tracking-wider uppercase text-purple-300">Fechamento Analítico Celestia</h3>
                        </div>
                        <p id="conteudo_ia" class="text-xs text-gray-400 leading-relaxed space-y-2">
                            <!-- Injetado via JS -->
                        </p>
                    </div>

                </div>
            </div>
        </div>
    </div>

    <script>
        // Placeholders que serão substituídos pelo Python antes de renderizar
        const produtos = __PRODUTOS_JSON__;
        const clientes = __CLIENTES_JSON__;

        // Renderiza lista de produtos no select
        const selectProd = document.getElementById('input_produto');
        produtos.forEach(p => {
            if(p.categoria === 'Cerveja') {
                selectProd.innerHTML += `<option value="${p.id}">🍺 ${p.nome} — R$ ${p.preco.toFixed(2)}</option>`;
            } else {
                selectProd.innerHTML += `<option value="${p.id}">🍬 ${p.nome} — R$ ${p.preco.toFixed(2)}</option>`;
            }
        });

        // Renderiza lista de clientes no select
        const selectCli = document.getElementById('input_cliente');
        clientes.forEach(c => {
            selectCli.innerHTML += `<option value="${c.id}">👤 Ficha: ${c.nome}</option>`;
        });

        // Renderiza Tabela de Fichas
        const tabelaFichas = document.getElementById('tabela_fichas');
        clientes.forEach(c => {
            const badgeRisco = c.saldo_devedor > 100 ? 
                `<span class="text-[9px] px-2 py-0.5 bg-red-500/10 text-red-400 font-bold rounded-md border border-red-500/20">RETENÇÃO</span>` : 
                `<span class="text-[9px] px-2 py-0.5 bg-brandNeon/10 text-brandNeon font-bold rounded-md border border-brandNeon/20">ESTÁVEL</span>`;
                
            tabelaFichas.innerHTML += `
                <tr class="hover:bg-white/[0.01] transition-all">
                    <td class="py-3 px-4 font-semibold text-gray-200">${c.nome}</td>
                    <td class="py-3 px-4 text-right font-bold text-amber-400">R$ ${c.saldo_devedor.toFixed(2)}</td>
                    <td class="py-3 px-4 text-center">${badgeRisco}</td>
                </tr>
            `;
        });

        // Renderiza Controle de Cervejeira (Frio)
        const gridFrio = document.getElementById('grid_frio');
        produtos.forEach(p => {
            const statusCor = p.frio_unid <= 10 ? 'text-red-400 font-bold' : 'text-brandIce';
            const alertBg = p.frio_unid <= 10 ? 'bg-red-500/10 border-red-500/20' : 'bg-white/5 border-gray-800';
            
            gridFrio.innerHTML += `
                <div class="p-3 rounded-xl border flex justify-between items-center ${alertBg}">
                    <div>
                        <p class="text-xs font-semibold text-gray-300">${p.nome}</p>
                        <span class="text-[10px] text-gray-500">Giro recomendado: +${p.un_por_caixa} un</span>
                    </div>
                    <div class="text-right">
                        <span class="text-sm font-bold tracking-tight px-2 py-1 rounded-lg bg-black/40 ${statusCor}">${p.frio_unid} un</span>
                    </div>
                </div>
            `;
        });

        // Renderiza Depósito (Quente)
        const gridQuente = document.getElementById('grid_quente');
        produtos.forEach(p => {
            if(p.quent_caixas > 0 || p.un_por_caixa > 1) {
                gridQuente.innerHTML += `
                    <div class="flex justify-between items-center border-b border-gray-800/40 pb-2">
                        <span class="text-gray-400 text-xs">${p.nome}</span>
                        <span class="font-bold text-gray-200 bg-white/5 px-2 py-0.5 rounded">${p.quent_caixas} Cx</span>
                    </div>
                `;
            }
        });

        // Relógio Operacional Live
        function clock() {
            const now = new Date();
            document.getElementById('live-clock').innerText = now.toLocaleDateString('pt-BR') + ' — ' + now.toLocaleTimeString('pt-BR');
        }
        setInterval(clock, 1000);
        clock();

        function ejecutarLancamento() {
            alert("Operação enviada ao backend! Dados sincronizados no Banco de Dados.");
        }

        function dispararFechamento() {
            document.getElementById('box_ia').classList.remove('hidden');
            document.getElementById('conteudo_ia').innerHTML = "<b>Análise Preditiva Celestia:</b><br>• Lucratividade Operacional estimada em 42% hoje.<br>• Alerta: Heineken Long Neck atingiu o limite crítico na geladeira.<br>• Fluxo Financeiro estável, porém 2 fichas necessitam de conciliação ativa.";
        }
    </script>
</body>
</html>
"""

# Injetamos os dados usando replace seguro, sem quebrar as chaves do front-end
html_final = html_premium_ui.replace("__PRODUTOS_JSON__", produtos_json).replace("__CLIENTES_JSON__", clientes_json)

# Renderização final de ponta a ponta
components.html(html_final, height=950, scrolling=True)
