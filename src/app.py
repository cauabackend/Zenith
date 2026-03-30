"""
Zenith - Agente Financeiro Inteligente
Controle de gastos e alertas personalizados com IA Generativa.
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuração da página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Zenith – Agente Financeiro",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Estilo customizado
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* Header */
    .main-header {
        background: linear-gradient(135deg, #0f4c75 0%, #1b262c 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .main-header h1 { margin: 0; font-size: 1.8rem; }
    .main-header p  { margin: 0.3rem 0 0 0; opacity: 0.85; font-size: 0.95rem; }

    /* Cards de alerta */
    .alert-card {
        padding: 1rem 1.2rem;
        border-radius: 10px;
        margin-bottom: 0.8rem;
        border-left: 4px solid;
        color: #1a1a1a !important;
    }
    .alert-danger  { background: #fff5f5; border-color: #e53e3e; }
    .alert-warning { background: #fffaf0; border-color: #ed8936; }
    .alert-success { background: #f0fff4; border-color: #38a169; }
    .alert-info    { background: #ebf8ff; border-color: #3182ce; }

    /* Métricas na sidebar */
    .metric-box {
        background: #f7fafc;
        padding: 0.8rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    .metric-box .label { font-size: 0.75rem; color: #718096; text-transform: uppercase; }
    .metric-box .value { font-size: 1.4rem; font-weight: 700; color: #2d3748; }

    /* Chat */
    .stChatMessage { border-radius: 12px !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Carregamento de dados
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@st.cache_data
def carregar_transacoes() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "transacoes.csv")
    df["data"] = pd.to_datetime(df["data"])
    return df


@st.cache_data
def carregar_perfil() -> dict:
    with open(DATA_DIR / "perfil_investidor.json", "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def carregar_produtos() -> dict:
    with open(DATA_DIR / "produtos_financeiros.json", "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def carregar_historico_atendimento() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "historico_atendimento.csv")


# ---------------------------------------------------------------------------
# Análise de gastos
# ---------------------------------------------------------------------------
def analisar_gastos(df: pd.DataFrame, perfil: dict) -> dict:
    """Gera resumo analítico dos gastos do cliente."""
    despesas = df[df["tipo"] == "debito"].copy()
    despesas["valor_abs"] = despesas["valor"].abs()
    receitas = df[df["tipo"] == "credito"]

    # Por mês
    despesas["mes"] = despesas["data"].dt.to_period("M").astype(str)
    gasto_mensal = despesas.groupby("mes")["valor_abs"].sum().to_dict()

    # Por categoria
    gasto_categoria = despesas.groupby("categoria")["valor_abs"].sum().sort_values(ascending=False).to_dict()

    # Média mensal por categoria
    n_meses = despesas["mes"].nunique() or 1
    media_categoria = {k: round(v / n_meses, 2) for k, v in gasto_categoria.items()}

    # Limites definidos pelo cliente
    limites = perfil.get("preferencias", {}).get("limite_gasto_mensal", {})

    # Alertas automáticos
    alertas = []
    ultimo_mes = despesas["mes"].max()
    gastos_ultimo_mes = despesas[despesas["mes"] == ultimo_mes]
    gasto_cat_ultimo = gastos_ultimo_mes.groupby("categoria")["valor_abs"].sum()

    for cat, limite in limites.items():
        if limite <= 0:
            continue
        gasto_atual = gasto_cat_ultimo.get(cat, 0)
        percentual = (gasto_atual / limite) * 100 if limite else 0
        if percentual >= 100:
            alertas.append({
                "tipo": "danger",
                "categoria": cat,
                "mensagem": f"🚨 {cat}: R${gasto_atual:,.2f} gastos — limite de R${limite:,.2f} ULTRAPASSADO ({percentual:.0f}%)"
            })
        elif percentual >= 80:
            alertas.append({
                "tipo": "warning",
                "categoria": cat,
                "mensagem": f"⚠️ {cat}: R${gasto_atual:,.2f} de R${limite:,.2f} — {percentual:.0f}% do limite"
            })

    # Gasto total vs receita
    receita_total = receitas["valor"].sum()
    despesa_total = despesas["valor_abs"].sum()
    saldo = receita_total - despesa_total

    # Transações atípicas (>2x a média da categoria)
    atipicas = []
    for _, row in despesas.iterrows():
        media_cat = media_categoria.get(row["categoria"], 0) / max(despesas[despesas["categoria"] == row["categoria"]].shape[0] / n_meses, 1)
        if row["valor_abs"] > media_cat * 3 and row["valor_abs"] > 200:
            atipicas.append({
                "data": row["data"].strftime("%d/%m/%Y"),
                "descricao": row["descricao"],
                "valor": row["valor_abs"],
                "categoria": row["categoria"]
            })

    return {
        "gasto_mensal": gasto_mensal,
        "gasto_categoria": gasto_categoria,
        "media_categoria": media_categoria,
        "alertas": alertas,
        "receita_total": receita_total,
        "despesa_total": despesa_total,
        "saldo": saldo,
        "transacoes_atipicas": atipicas,
        "ultimo_mes": ultimo_mes,
        "n_meses": n_meses,
    }


# ---------------------------------------------------------------------------
# Construção do System Prompt
# ---------------------------------------------------------------------------
def construir_system_prompt(perfil: dict, analise: dict, produtos: dict, historico: pd.DataFrame) -> str:
    cliente = perfil["cliente"]
    fin = perfil["perfil_financeiro"]
    prefs = perfil["preferencias"]
    metas = perfil.get("metas", [])

    metas_str = "\n".join(
        f"  - {m['descricao']}: R${m['valor_atual']:,.2f} / R${m['valor_alvo']:,.2f} (prazo: {m['prazo']}, prioridade: {m['prioridade']})"
        for m in metas
    )

    alertas_str = "\n".join(f"  - {a['mensagem']}" for a in analise["alertas"]) or "  Nenhum alerta ativo."

    gastos_cat_str = "\n".join(
        f"  - {cat}: R${val:,.2f} (média mensal: R${analise['media_categoria'].get(cat, 0):,.2f})"
        for cat, val in analise["gasto_categoria"].items()
    )

    atipicas_str = "\n".join(
        f"  - {t['data']} | {t['descricao']} | R${t['valor']:,.2f} ({t['categoria']})"
        for t in analise["transacoes_atipicas"]
    ) or "  Nenhuma transação atípica identificada."

    produtos_str = "\n".join(
        f"  - {p['nome']} ({p['categoria']}): {p['rentabilidade']} | Risco: {p['risco']} | Mínimo: R${p['investimento_minimo']}"
        for p in produtos["produtos"]
    )

    hist_str = "\n".join(
        f"  - [{row['data']}] {row['assunto']}: {row['resumo']} (sentimento: {row['sentimento']})"
        for _, row in historico.iterrows()
    )

    return f"""Você é o Zenith, um agente financeiro inteligente especializado em controle de gastos e alertas personalizados.

## SUA PERSONALIDADE
- Tom: amigável, direto e educativo — como um amigo que entende de finanças.
- Use linguagem simples, evite jargões desnecessários.
- Seja proativo: quando identificar padrões ruins, alerte com empatia.
- Use emojis com moderação para deixar a conversa leve.
- Responda SEMPRE em português brasileiro.
- Quando fizer contas, mostre o raciocínio.

## REGRAS DE SEGURANÇA (ANTI-ALUCINAÇÃO)
- Use APENAS os dados fornecidos abaixo. Nunca invente transações ou valores.
- Se não souber algo, diga "não tenho essa informação nos seus dados".
- Não dê conselhos jurídicos ou tributários específicos — sugira consultar um profissional.
- Não recomende produtos que não estejam no catálogo abaixo.
- Ao sugerir economia, baseie-se nos dados reais de gasto do cliente.

## DADOS DO CLIENTE
Nome: {cliente['nome']}
Idade: {cliente['idade']} anos
Profissão: {cliente['profissao']}
Renda mensal (salário): R${cliente['renda_mensal']:,.2f}
Renda extra média: R${cliente['renda_extra_media']:,.2f}
Cidade: {cliente['cidade']}/{cliente['estado']}

## PERFIL FINANCEIRO
Perfil de investidor: {fin['perfil_investidor']}
Tolerância a risco: {fin['tolerancia_risco']}
Objetivo principal: {fin['objetivo_principal']}
Conhecimento financeiro: {fin['conhecimento_financeiro']}
Possui reserva de emergência: {'Sim' if fin['possui_reserva_emergencia'] else 'Não (em construção)'}
Reserva atual: R${fin['valor_reserva_atual']:,.2f} de R${fin['meta_reserva_emergencia']:,.2f}

## METAS
{metas_str}

## RESUMO FINANCEIRO (período: {analise['n_meses']} meses)
Receita total: R${analise['receita_total']:,.2f}
Despesa total: R${analise['despesa_total']:,.2f}
Saldo acumulado: R${analise['saldo']:,.2f}

## GASTOS POR CATEGORIA (acumulado):
{gastos_cat_str}

## ALERTAS ATIVOS (mês {analise['ultimo_mes']}):
{alertas_str}

## TRANSAÇÕES ATÍPICAS DETECTADAS:
{atipicas_str}

## LIMITES DE GASTO DEFINIDOS PELO CLIENTE:
{json.dumps(prefs['limite_gasto_mensal'], ensure_ascii=False, indent=2)}

## PRODUTOS FINANCEIROS DISPONÍVEIS:
{produtos_str}

## HISTÓRICO DE ATENDIMENTOS:
{hist_str}

## COMO AGIR
1. Se o cliente perguntar sobre gastos → analise os dados acima e responda com números reais.
2. Se houver alertas ativos → mencione proativamente quando relevante.
3. Se perguntar sobre investimentos → sugira produtos do catálogo compatíveis com o perfil.
4. Se pedir dicas de economia → baseie-se nos padrões de gasto reais (ex: frequência de iFood, gastos com transporte).
5. Se perguntar sobre metas → mostre progresso e calcule quanto falta por mês para atingir no prazo.
"""


# ---------------------------------------------------------------------------
# Integração com LLM
# ---------------------------------------------------------------------------
def get_llm_response(messages: list, system_prompt: str, api_key: str, provider: str) -> str:
    """Obtém resposta da LLM escolhida."""

    if provider == "Google Gemini":
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=system_prompt,
        )
        # Converter histórico para formato Gemini
        gemini_history = []
        for msg in messages[:-1]:  # Todos menos o último
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [msg["content"]]})

        chat = model.start_chat(history=gemini_history)
        response = chat.send_message(messages[-1]["content"])
        return response.text

    elif provider == "OpenAI":
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=full_messages,
            temperature=0.7,
            max_tokens=1500,
        )
        return response.choices[0].message.content

    elif provider == "Ollama (Local)":
        import requests as req
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        resp = req.post(
            "http://localhost:11434/api/chat",
            json={"model": "llama3.1:8b", "messages": full_messages, "stream": False},
        )
        return resp.json()["message"]["content"]


# ---------------------------------------------------------------------------
# Interface principal
# ---------------------------------------------------------------------------
def main():
    # ---- Carregar dados ----
    try:
        transacoes = carregar_transacoes()
        perfil = carregar_perfil()
        produtos = carregar_produtos()
        historico = carregar_historico_atendimento()
    except FileNotFoundError as e:
        st.error(f"Arquivo de dados não encontrado: {e}")
        st.info("Certifique-se de que a pasta `data/` contém todos os arquivos necessários.")
        return

    analise = analisar_gastos(transacoes, perfil)

    # ---- Sidebar: Configuração + Perfil ----
    with st.sidebar:
        st.markdown("## ⚙️ Configuração da LLM")
        provider = st.selectbox("Provedor", ["Google Gemini", "OpenAI", "Ollama (Local)"])

        if provider != "Ollama (Local)":
            api_key = st.text_input(
                f"API Key ({provider})",
                type="password",
                help="Sua chave de API. Nunca é armazenada."
            )
        else:
            api_key = "local"
            st.caption("Certifique-se de que o Ollama está rodando em `localhost:11434`.")

        st.divider()

        # Perfil do cliente
        cliente = perfil["cliente"]
        st.markdown(f"### 👤 {cliente['nome']}")
        st.caption(f"{cliente['profissao']} · {cliente['cidade']}/{cliente['estado']}")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Renda Mensal", f"R${cliente['renda_mensal']:,.0f}")
        with col2:
            saldo_ultimo = analise["saldo"] / analise["n_meses"]
            st.metric("Saldo Médio/Mês", f"R${saldo_ultimo:,.0f}")

        st.divider()

        # Progresso das metas
        st.markdown("### 🎯 Metas")
        for meta in perfil.get("metas", []):
            progresso = meta["valor_atual"] / meta["valor_alvo"]
            st.caption(meta["descricao"])
            st.progress(min(progresso, 1.0), text=f"R${meta['valor_atual']:,.0f} / R${meta['valor_alvo']:,.0f}")

        st.divider()

        # Gráfico de gastos por categoria
        st.markdown("### 📊 Gastos por Categoria")
        cat_df = pd.DataFrame({
            "Categoria": analise["gasto_categoria"].keys(),
            "Total (R$)": analise["gasto_categoria"].values(),
        }).sort_values("Total (R$)", ascending=True)
        st.bar_chart(cat_df.set_index("Categoria"), horizontal=True)

    # ---- Header ----
    st.markdown("""
    <div class="main-header">
        <h1>💰 Zenith</h1>
        <p>Seu agente financeiro inteligente — controle de gastos e alertas personalizados</p>
    </div>
    """, unsafe_allow_html=True)

    # ---- Alertas ativos ----
    if analise["alertas"]:
        with st.expander(f"🔔 {len(analise['alertas'])} alerta(s) ativo(s) — clique para ver", expanded=True):
            for alerta in analise["alertas"]:
                css_class = f"alert-{alerta['tipo']}"
                st.markdown(f'<div class="alert-card {css_class}">{alerta["mensagem"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="alert-card alert-success">✅ Tudo sob controle! Nenhum alerta ativo este mês.</div>', unsafe_allow_html=True)

    # ---- Chat ----
    st.markdown("---")

    # Inicializar histórico de chat
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Sugestões de perguntas
    if not st.session_state.messages:
        st.caption("💡 Experimente perguntar:")
        suggestions = [
            "Como estão meus gastos este mês?",
            "Onde posso economizar?",
            "Quanto falta para minha reserva de emergência?",
            "Qual meu maior gasto com iFood?",
        ]
        cols = st.columns(len(suggestions))
        for i, sug in enumerate(suggestions):
            if cols[i].button(sug, key=f"sug_{i}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": sug})
                st.rerun()

    # Exibir mensagens anteriores
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="🧑‍💻" if msg["role"] == "user" else "💰"):
            st.markdown(msg["content"])

    # Input do chat
    if prompt := st.chat_input("Pergunte sobre seus gastos, metas ou peça dicas..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(prompt)

        # Verificar API key
        if provider != "Ollama (Local)" and not api_key:
            with st.chat_message("assistant", avatar="💰"):
                st.warning("Configure sua API Key na barra lateral para começar!")
            return

        # Gerar resposta
        system_prompt = construir_system_prompt(perfil, analise, produtos, historico)

        with st.chat_message("assistant", avatar="💰"):
            with st.spinner("Analisando seus dados..."):
                try:
                    response = get_llm_response(
                        st.session_state.messages,
                        system_prompt,
                        api_key,
                        provider,
                    )
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    st.error(f"Erro ao se comunicar com a LLM: {str(e)}")
                    st.info("Verifique sua API key e conexão com a internet.")


if __name__ == "__main__":
    main()