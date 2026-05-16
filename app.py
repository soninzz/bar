import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Celestia Bar OS",
    page_icon="🍺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS CUSTOMIZADO PARA IDIOMA DE DESIGN DARK/MODERNO ---
st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    div.stButton > button { width: 100%; border-radius: 6px; height: 3em; font-weight: bold; }
    .stProgress > div > div > div > div { background-color: #238636; }
    .css-12w0qpk { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZAÇÃO DO BANCO DE DADOS (SQLite) ---
DB_NAME = 'bar_data_production.db'

def get_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # Tabela de Produtos
    c.execute('''CREATE TABLE IF NOT EXISTS produtos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    preco_venda REAL NOT NULL,
                    preco_custo REAL NOT NULL,
                    quent_caixas INTEGER DEFAULT 0,
                    frio_unid INTEGER DEFAULT 0,
                    un_por_caixa INTEGER NOT NULL,
                    categoria TEXT NOT NULL,
                    estoque_minimo_frio INTEGER DEFAULT 6
                 )''')
                 
    # Tabela de Clientes
    c.execute('''CREATE TABLE IF NOT EXISTS clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL UNIQUE,
                    telefone TEXT,
                    saldo_devedor REAL DEFAULT 0.0
                 )''')
                 
    # Tabela de Histórico de Consumo (Fiado Detalhado)
    c.execute('''CREATE TABLE IF NOT EXISTS historico_consumo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente_id INTEGER,
                    data TEXT NOT NULL,
                    descricao TEXT NOT NULL,
                    valor REAL NOT NULL,
                    FOREIGN KEY(cliente_id) REFERENCES clientes(id)
                 )''')
                 
    # Tabela de Vendas Gerais
    c.execute('''CREATE TABLE IF NOT EXISTS vendas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT NOT NULL,
                    total REAL NOT NULL,
                    detalhes TEXT NOT NULL,
                    tipo_pagamento TEXT NOT NULL
                 )''')
                 
    # Tabela de Contas a Pagar / Lançamento de Notas
    c.execute('''CREATE TABLE IF NOT EXISTS contas_a_pagar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    descricao TEXT NOT NULL,
                    valor REAL NOT NULL,
                    data_vencimento TEXT NOT NULL,
                    status TEXT DEFAULT 'PENDENTE'
                 )''')
    
    # Carga Inicial de Produtos Reais se a tabela estiver vazia
    c.execute("SELECT COUNT(*) FROM produtos")
    if c.fetchone()[0] == 0:
        produtos_padrao = [
            # Cervejas Caixa de 24, 12 e 6
            ('Brahma Duplo Malte 350ml (Cx 24)', 5.00, 3.20, 5, 24, 24, 'Cerveja', 12),
            ('Heineken Long Neck (Cx 12)', 9.00, 6.50, 8, 12, 12, 'Cerveja', 6),
            ('Eisenbahn 600ml (Cx 6)', 11.00, 7.80, 12, 6, 6, 'Cerveja', 6),
            ('Amstel Lata 473ml (Cx 12)', 6.50, 4.10, 6, 12, 12, 'Cerveja', 8),
            # Refrigerantes e Água
            ('Coca-Cola Lata 350ml', 6.00, 3.20, 2, 12, 12, 'Refrigerante', 6),
            ('Guaraná Antarctica 2L', 10.00, 6.00, 4, 6, 6, 'Refrigerante', 4),
            ('Água Mineral Sem Gás', 4.00, 1.50, 1, 12, 1, 'Água', 6),
            # Doces e Salgadinhos
            ('Paçoca Amor (Unidade)', 1.50, 0.60, 0, 50, 1, 'Doces', 10),
            ('Doce de Abóbora Coração', 2.00, 0.90, 0, 30, 1, 'Doces', 10),
            ('Amendoim Grelhaditos Mendorato', 5.00, 2.30, 0, 25, 1, 'Salgadinhos', 5),
            ('Salgadinho Torcida Pimenta', 4.50, 2.00, 0, 20, 1, 'Salgadinhos', 5)
        ]
        c.executemany('''INSERT INTO produtos (nome, preco_venda, preco_custo, quent_caixas, frio_unid, un_por_caixa, categoria, estoque_minimo_frio) 
                         VALUES (?,?,?,?,?,?,?,?)''', produtos_padrao)
        
    conn.commit()
    conn.close()

init_db()

# --- INTEGRAÇÃO INTELIGENTE DE IA (GEMINI) ---
def analisar_dados_ia(vendas_hoje, estoque_critico, contas_vencendo):
    try:
        import google.generativeai as genai
        if "GEMINI_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            Você é o gerente executivo do Bar do Vovô. Analise os dados operacionais de hoje e gere um relatório de fechamento direto, humanizado e estratégico.
            
            DADOS DE HOJE:
            - Vendas Realizadas: R$ {vendas_hoje['total'].sum():.2f}
            - Métodos de pagamento: {vendas_hoje['tipo_pagamento'].value_counts().to_dict()}
            - Alertas de Estoque Crítico na Geladeira: {estoque_critico}
            - Compromissos Financeiros Próximos: {contas_vencendo}
            
            Gere o relatório estruturado exatamente com os tópicos:
            1. **Resumo Financeiro e Lucratividade Estimada**
            2. **Análise de Risco de Crédito (Fiado/Fichas)**
            3. **Ações urgentes de Reposição e Compras para amanhã**
            """
            response = model.generate_content(prompt)
            return response.text
    except Exception as e:
        pass
    
    # Fallback estruturado caso a API Key não esteja setada nos Secrets do Streamlit ainda
    total = vendas_hoje['total'].sum() if not vendas_hoje.empty else 0
    return f"""
    ### 🤖 Relatório Automatizado Celestia (Modo de Segurança)
    *   **Financeiro:** Faturamento total de R$ {total:.2f} registrado no banco de dados.
    *   **Estoque:** Verifique a aba de estoque. Existem {len(estoque_critico)} itens operando abaixo do nível mínimo na geladeira.
    *   **Contas:** Existem {len(contas_vencendo)} lançamentos de notas pendentes no contas a pagar.
    *   *Nota: Adicione a chave `GEMINI_API_KEY` nos Secrets do Streamlit para ativar a análise preditiva via IA.*
    """

# --- RENDERIZAÇÃO DA INTERFACE ---
st.title("🍺 Celestia Bar OS — Operação de Balcão")

conn = get_db()
c = conn.cursor()

# Métrica de cabeçalho rápida
hoje_str = datetime.now().strftime("%Y-%m-%d")
vendas_hoje_df = pd.read_sql(f"SELECT * FROM vendas WHERE data LIKE '{hoje_str}%'", conn)
total_hoje = vendas_hoje_df['total'].sum() if not vendas_hoje_df.empty else 0.0

st.sidebar.metric("Faturamento Hoje", f"R$ {total_hoje:.2f}")
st.sidebar.write(f"📅 {datetime.now().strftime('%d/%m/%Y — %H:%M')}")

# Tabs Principais do Sistema
tab_balcao, tab_estoque, tab_clientes, tab_financeiro, tab_ia = st.tabs([
    "🛒 Balcão / Comanda", 
    "📦 Estoque Geral & Caixas", 
    "👥 Clientes (Fichas/Fiado)", 
    "💸 Contas a Pagar & Notas",
    "📊 Fechamento do Dia (IA)"
])

# --- TAB 1: BALCÃO / COMANDA ---
with tab_balcao:
    st.subheader("⚡ Lançamento de Consumo Instantâneo")
    
    produtos_df = pd.read_sql("SELECT * FROM produtos", conn)
    clientes_df = pd.read_sql("SELECT * FROM clientes", conn)
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        prod_lista = [f"{row['nome']} — R$ {row['preco_venda']:.2f} ({row['frio_unid']} geladas)" for _, row in produtos_df.iterrows()]
        prod_selecionado = st.selectbox("Selecione o Produto", prod_lista)
        prod_id = produtos_df.iloc[prod_lista.index(prod_selecionado)]['id'] if prod_selecionado else None
        
    with col2:
        quantidade = st.number_input("Quantidade", min_value=1, value=1, step=1)
        
    with col3:
        lista_cli_opcoes = ["Venda Direta (Dinheiro/Pix/Cartão)"] + clientes_df['nome'].tolist()
        cliente_selecionado = st.selectbox("Vincular à Ficha/Cliente", lista_cli_opcoes)
        
    col1_v, col2_v = st.columns(2)
    with col1_v:
        forma_pagamento = st.selectbox("Forma de Pagamento", ["PIX", "DINHEIRO", "CARTÃO DE CRÉDITO/DÉBITO", "PENDURAR NA FICHA (FIADO)"])

    if st.button("🚀 CONFIRMAR LANÇAMENTO (F2)", use_container_width=True):
        prod_row = produtos_df[produtos_df['id'] == prod_id].iloc[0]
        
        if prod_row['frio_unid'] < quantidade:
            st.error(f"❌ Estoque insuficiente na Geladeira! {prod_row['nome']} só possui {prod_row['frio_unid']} unidades geladas. Vá na aba de estoque e reponha!")
        else:
            total_venda = prod_row['preco_venda'] * quantidade
            data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Abate do estoque frio (geladeira)
            c.execute("UPDATE produtos SET frio_unid = frio_unid - ? WHERE id = ?", (quantidade, prod_id))
            
            if forma_pagamento == "PENDURAR NA FICHA (FIADO)":
                if cliente_selecionado == "Venda Direta (Dinheiro/Pix/Cartão)":
                    st.error("❌ Para pendurar, você deve selecionar ou cadastrar um cliente válido na ficha!")
                else:
                    # Atualiza saldo do cliente e cria histórico cronológico
                    c.execute("UPDATE clientes SET saldo_devedor = saldo_devedor + ? WHERE nome = ?", (total_venda, cliente_selecionado))
                    c.execute("SELECT id FROM clientes WHERE nome = ?", (cliente_selecionado,))
                    cli_id = c.fetchone()[0]
                    
                    detalhe_hist = f"{quantidade}x {prod_row['nome']}"
                    c.execute("INSERT INTO historico_consumo (cliente_id, data, descricao, valor) VALUES (?, ?, ?, ?)",
                              (cli_id, data_atual, detalhe_hist, total_venda))
                    
                    c.execute("INSERT INTO vendas (data, total, detalhes, tipo_pagamento) VALUES (?, ?, ?, ?)",
                              (data_atual, total_venda, f"{quantidade}x {prod_row['nome']} (Fiado: {cliente_selecionado})", "FIADO"))
                    st.success(f"📝 R$ {total_venda:.2f} pendurados com sucesso na ficha de {cliente_selecionado}!")
            else:
                # Venda à vista
                c.execute("INSERT INTO vendas (data, total, detalhes, tipo_pagamento) VALUES (?, ?, ?, ?)",
                          (data_atual, total_venda, f"{quantidade}x {prod_row['nome']}", forma_pagamento))
                st.success(f"💰 Venda à vista computada! R$ {total_venda:.2f} recebidos via {forma_pagamento}.")
                
            conn.commit()
            st.rerun()

# --- TAB 2: ESTOQUE GERAL & CAIXAS ---
with tab_estoque:
    st.subheader("📦 Engenharia de Estoque Inteligente")
    
    # Formulário para entrada de mercadoria de Notas Fiscais ou Compras de Caixas
    with st.expander("📥 Lançar Entrada de Mercadoria / Compras de Caixas"):
        with st.form("entrada_estoque"):
            prod_ent = st.selectbox("Qual produto está chegando?", produtos_df['nome'].tolist())
            qtd_caixas_novas = st.number_input("Quantas Caixas/Fardos estão entrando no Depósito?", min_value=0, value=1)
            unidades_soltas = st.number_input("Alguma unidade avulsa direto pra geladeira?", min_value=0, value=0)
            
            if st.form_submit_button("Dar Entrada no Estoque"):
                c.execute("UPDATE produtos SET quent_caixas = quent_caixas + ?, frio_unid = frio_unid + ? WHERE nome = ?", 
                          (qtd_caixas_novas, unidades_soltas, prod_ent))
                conn.commit()
                st.success(f"Estoque atualizado para {prod_ent}!")
                st.rerun()

    st.divider()
    
    # Painel de Automação Visual de Reposição
    st.subheader("🚨 Alertas Automáticos de Cervejeira")
    
    for _, row in produtos_df.iterrows():
        # Se estiver abaixo do estoque mínimo configurado
        if row['frio_unid'] <= row['estoque_minimo_frio']:
            col_p, col_m, col_btn = st.columns([3, 2, 2])
            with col_p:
                st.warning(f"⚠️ **{row['nome']}** está acabando na geladeira!")
            with col_m:
                st.write(f"Geladeira: **{row['frio_unid']} un** | Depósito: **{row['quent_caixas']} cx**")
            with col_btn:
                if row['quent_caixas'] > 0:
                    if st.button(f"Mover 1 Cx (+{row['un_por_caixa']} un) para Gelar", key=f"repor_{row['id']}"):
                        c.execute("UPDATE produtos SET quent_caixas = quent_caixas - 1, frio_unid = frio_unid + ? WHERE id = ?", 
                                  (row['un_por_caixa'], row['id']))
                        conn.commit()
                        st.success(f"Sucesso! 1 caixa de {row['nome']} foi aberta e colocada para gelar.")
                        st.rerun()
                else:
                    st.error("🚨 Zero caixas no depósito! Compre urgente.")
                    
    st.divider()
    st.subheader("📑 Inventário Completo Atualizado")
    st.dataframe(produtos_df[['categoria', 'nome', 'preco_venda', 'frio_unid', 'quent_caixas', 'un_por_caixa']], use_container_width=True)

# --- TAB 3: CLIENTES (FICHAS / FIADO) ---
with tab_clientes:
    st.subheader("👥 Controle Avançado de Conta Corrente (Fiado)")
    
    with st.form("novo_cliente_form"):
        st.write("**Cadastrar Novo Cliente de Ficha**")
        nome_c = st.text_input("Nome Completo do Cliente")
        tel_c = st.text_input("Telefone / WhatsApp")
        if st.form_submit_button("Salvar Cadastro"):
            if nome_c:
                try:
                    c.execute("INSERT INTO clientes (nome, telefone) VALUES (?, ?)", (nome_c, tel_c))
                    conn.commit()
                    st.success("Cliente cadastrado com sucesso!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Este nome já está cadastrado.")
                    
    st.divider()
    
    # Listagem de Devedores e Histórico Cronológico Completo
    st.subheader("📌 Extrato Detalhado de Fichas")
    if not clientes_df.empty:
        for _, cli in clientes_df.iterrows():
            if cli['saldo_devedor'] > 0:
                with st.expander(f"🔴 {cli['nome']} — Devendo: R$ {cli['saldo_devedor']:.2f}"):
                    st.write(f"**Contato:** {cli['telefone']}")
                    st.write("**Histórico de consumo acumulado (Mês corrente):**")
                    
                    # Busca o histórico do banco de dados relacional
                    historico_df = pd.read_sql(f"SELECT data, descricao, valor FROM historico_consumo WHERE cliente_id = {cli['id']}", conn)
                    if not historico_df.empty:
                        st.table(historico_df)
                    else:
                        st.info("Consumo registrado no sistema legado ou migrado.")
                        
                    # Opção de Baixa ou Pagamento Parcial/Total
                    valor_pago = st.number_input(f"Valor pago por {cli['nome']}", min_value=0.0, max_value=float(cli['saldo_devedor']), value=float(cli['saldo_devedor']), key=f"pago_{cli['id']}")
                    if st.button(f"Confirmar Recebimento de R$ {valor_pago:.2f}", key=f"btn_pago_{cli['id']}"):
                        c.execute("UPDATE clientes SET saldo_devedor = saldo_devedor - ? WHERE id = ?", (valor_pago, cli['id']))
                        # Salva a entrada no caixa geral
                        c.execute("INSERT INTO vendas (data, total, detalhes, tipo_pagamento) VALUES (?, ?, ?, ?)",
                                  (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), valor_pago, f"Recebimento de Fiado: {cli['nome']}", "PIX/DINHEIRO"))
                        conn.commit()
                        st.success(f"Baixa dada com sucesso na conta de {cli['nome']}!")
                        st.rerun()
    else:
        st.info("Nenhum cliente cadastrado no sistema ainda.")

# --- TAB 4: CONTAS A PAGAR & NOTAS ---
with tab_financeiro:
    st.subheader("🧾 Lançamento de Notas Fiscais & Lembrete de Boletos")
    
    with st.form("nova_nota"):
        desc_nota = st.text_input("Descrição da Nota/Boleto (Ex: Distribuidora Ambev - Cervejas)")
        valor_nota = st.number_input("Valor do Compromisso (R$)", min_value=0.0, step=10.0)
        venc_nota = st.date_input("Data de Vencimento")
        
        if st.form_submit_button("Lançar Nota no Contas a Pagar"):
            c.execute("INSERT INTO contas_a_pagar (descricao, valor, data_vencimento) VALUES (?, ?, ?)",
                      (desc_nota, valor_nota, venc_nota.strftime("%Y-%m-%d")))
            conn.commit()
            st.success("Nota lançada no financeiro com sucesso!")
            st.rerun()
            
    st.divider()
    st.subheader("📅 Próximos Compromissos Financeiros (Lembretes)")
    contas_df = pd.read_sql("SELECT * FROM contas_a_pagar WHERE status = 'PENDENTE'", conn)
    
    if not contas_df.empty:
        for _, conta in contas_df.iterrows():
            col_c1, col_c2, col_c3 = st.columns([3, 2, 2])
            col_c1.write(f"❌ **{conta['descricao']}**")
            col_c2.write(f"Valor: **R$ {conta['valor']:.2f}** | Vence em: `{conta['data_vencimento']}`")
            if col_c3.button("Marcar como Pago", key=f"pago_nota_{conta['id']}"):
                c.execute("UPDATE contas_a_pagar SET status = 'PAGO' WHERE id = ?", (conta['id'],))
                conn.commit()
                st.success("Conta baixada!")
                st.rerun()
    else:
        st.success("Tudo em dia! Nenhuma nota ou boleto pendente de pagamento.")

# --- TAB 5: FECHAMENTO DO DIA (IA) ---
with tab_ia:
    st.subheader("🏁 Encerramento de Caixa Inteligente")
    st.write("Ao clicar no botão abaixo, o sistema consolida todas as movimentações financeiras do dia, estoque consumido e gera inteligência de negócios automatizada.")
    
    if st.button("🔴 FINALIZAR DIA E EMITIR RELATÓRIO COMPLETISSIMO", use_container_width=True):
        vendas_do_dia = pd.read_sql(f"SELECT * FROM vendas WHERE data LIKE '{hoje_str}%'", conn)
        estoque_atual = pd.read_sql("SELECT nome, frio_unid, estoque_minimo_frio FROM produtos", conn)
        contas_criticas = pd.read_sql("SELECT descricao, data_vencimento FROM contas_a_pagar WHERE status = 'PENDENTE'", conn)
        
        itens_criticos = estoque_atual[estoque_atual['frio_unid'] <= estoque_atual['estoque_minimo_frio']]['nome'].tolist()
        notas_lembrete = contas_criticas.to_dict(orient='records')
        
        st.write("---")
        st.subheader("📊 Resumo de Caixa Bruto")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Faturamento Líquido Direto", f"R$ {vendas_do_dia[vendas_do_dia['tipo_pagamento'] != 'FIADO']['total'].sum():.2f}")
        c2.metric("Total Injetado no Fiado", f"R$ {vendas_do_dia[vendas_do_dia['tipo_pagamento'] == 'FIADO']['total'].sum():.2f}")
        c3.metric("Operações Totais", f"{len(vendas_do_dia)} vendas")
        
        # Chamada da IA com os dados dinâmicos coletados do SQLite
        st.write("---")
        st.subheader("🤖 Parecer Tecnológico da Inteligência Artificial")
        with st.spinner("Analisando métricas de lucratividade e risco..."):
            relatorio_final = analisar_dados_ia(vendas_do_dia, itens_criticos, notas_lembrete)
            st.markdown(relatorio_final)

conn.close()