"""
Zenith — agente financeiro para controle de gastos.
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
    page_title="Zenith",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Estilo
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .main-header {
        padding: 1.2rem 0 0.8rem 0;
        margin-bottom: 1rem;
    }
    .main-header h1 {
        margin: 0;
        font-size: 1.6rem;
        font-weight: 600;
    }
    .main-header p {
        margin: 0.2rem 0 0 0;
        opacity: 0.6;
        font-size: 0.9rem;
    }

    .alert-card {
        padding: 0.8rem 1rem;
        border-radius: 8px;
        margin-bottom: 0.6rem;
        border-left: 4px solid;
        color: #1a1a1a !important;
        font-size: 0.9rem;
    }
    .alert-danger  { background: #fff5f5; border-color: #c53030; }
    .alert-warning { background: #fffaf0; border-color: #c05621; }
    .alert-success { background: #f0fff4; border-color: #276749; }
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
    despesas = df[df["tipo"] == "debito"].copy()
    despesas["valor_abs"] = despesas["valor"].abs()
    receitas = df[df["tipo"] == "credito"]

    despesas["mes"] = despesas["data"].dt.to_period("M").astype(str)
    gasto_mensal = despesas.groupby("mes")["valor_abs"].sum().to_dict()

    gasto_categoria = (
        despesas.groupby("categoria")["valor_abs"]
        .sum()
        .sort_values(ascending=False)
        .to_dict()
    )

    n_meses = despesas["mes"].nunique() or 1
    media_categoria = {k: round(v / n_meses, 2) for k, v in gasto_categoria.items()}

    limites = perfil.get("preferencias", {}).get("limite_gasto_mensal", {})

    alertas = []
    ultimo_mes = despesas["mes"].max()
    gastos_ultimo_mes = despesas[despesas["mes"] == ultimo_mes]
    gasto_cat_ultimo = gastos_ultimo_mes.groupby("categoria")["valor_abs"].sum()

    for cat, limite in limites.items():
        if limite <= 0:
            continue
        gasto_atual = gasto_cat_ultimo.get(cat, 0)
        pct = (gasto_atual / limite) * 100 if limite else 0
        if pct >= 100:
            alertas.append({
                "tipo": "danger",
                "categoria": cat,
                "mensagem": f"{cat}: R${gasto_atual:,.2f} — limite de R${limite:,.2f} ultrapassado ({pct:.0f}%)"
            })
        elif pct >= 80:
            alertas.append({
                "tipo": "warning",
                "categoria": cat,
                "mensagem": f"{cat}: R${gasto_atual:,.2f} de R${limite:,.2f} — {pct:.0f}% do limite"
            })

    receita_total = receitas["valor"].sum()
    despesa_total = despesas["valor_abs"].sum()
    saldo = receita_total - despesa_total

    atipicas = []
    for _, row in despesas.iterrows():
        n_transacoes_cat = despesas[despesas["categoria"] == row["categoria"]].shape[0] / n_meses
        media_cat = media_categoria.get(row["categoria"], 0) / max(n_transacoes_cat, 1)
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
# System Prompt
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

    alertas_str = "\n".join(f"  - {a['mensagem']}" for a in analise["alertas"]) or "  Nenhum alerta."

    gastos_cat_str = "\n".join(
        f"  - {cat}: R${val:,.2f} (média mensal: R${analise['media_categoria'].get(cat, 0):,.2f})"
        for cat, val in analise["gasto_categoria"].items()
    )

    atipicas_str = "\n".join(
        f"  - {t['data']} | {t['descricao']} | R${t['valor']:,.2f} ({t['categoria']})"
        for t in analise["transacoes_atipicas"]
    ) or "  Nenhuma."

    produtos_str = "\n".join(
        f"  - {p['nome']} ({p['categoria']}): {p['rentabilidade']} | Risco: {p['risco']} | Mínimo: R${p['investimento_minimo']}"
        for p in produtos["produtos"]
    )

    hist_str = "\n".join(
        f"  - [{row['data']}] {row['assunto']}: {row['resumo']} (sentimento: {row['sentimento']})"
        for _, row in historico.iterrows()
    )

    return f"""Você é o Zenith, um assistente de controle de gastos. Fale de forma direta, sem enrolação, em português brasileiro.
Quando fizer cálculos, mostre o passo a passo. Use emojis só se fizer sentido, sem exagero.

REGRAS:
- Use APENAS os dados abaixo. Nunca invente transações ou valores.
- Se não tiver a informação, diga que não tem.
- Nada de conselho jurídico ou tributário — mande procurar um profissional.
- Só recomende produtos do catálogo abaixo.

CLIENTE
Nome: {cliente['nome']} | Idade: {cliente['idade']} | Profissão: {cliente['profissao']}
Renda mensal: R${cliente['renda_mensal']:,.2f} | Renda extra média: R${cliente['renda_extra_media']:,.2f}
Cidade: {cliente['cidade']}/{cliente['estado']}

PERFIL FINANCEIRO
Investidor: {fin['perfil_investidor']} | Risco: {fin['tolerancia_risco']}
Objetivo: {fin['objetivo_principal']}
Reserva de emergência: R${fin['valor_reserva_atual']:,.2f} de R${fin['meta_reserva_emergencia']:,.2f} ({'completa' if fin['possui_reserva_emergencia'] else 'em construção'})

METAS
{metas_str}

RESUMO ({analise['n_meses']} meses)
Receita: R${analise['receita_total']:,.2f} | Despesa: R${analise['despesa_total']:,.2f} | Saldo: R${analise['saldo']:,.2f}

GASTOS POR CATEGORIA
{gastos_cat_str}

ALERTAS ({analise['ultimo_mes']})
{alertas_str}

TRANSAÇÕES ATÍPICAS
{atipicas_str}

LIMITES DO CLIENTE
{json.dumps(prefs['limite_gasto_mensal'], ensure_ascii=False, indent=2)}

PRODUTOS DISPONÍVEIS
{produtos_str}

HISTÓRICO DE ATENDIMENTOS
{hist_str}

COMO RESPONDER
1. Pergunta sobre gastos → responda com números reais dos dados.
2. Alertas ativos → mencione quando fizer sentido.
3. Investimentos → sugira do catálogo, respeitando o perfil.
4. Dicas de economia → baseie-se nos padrões reais (ex: frequência de iFood).
5. Metas → calcule quanto guardar por mês pra atingir no prazo.
"""


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------
def get_llm_response(messages: list, system_prompt: str, api_key: str, provider: str) -> str:
    if provider == "Google Gemini":
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=system_prompt,
        )
        gemini_history = []
        for msg in messages[:-1]:
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
            json={"model": "llama3.2:3b", "messages": full_messages, "stream": False},
        )
        return resp.json()["message"]["content"]


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
def main():
    try:
        transacoes = carregar_transacoes()
        perfil = carregar_perfil()
        produtos = carregar_produtos()
        historico = carregar_historico_atendimento()
    except FileNotFoundError as e:
        st.error(f"Arquivo não encontrado: {e}")
        return

    analise = analisar_gastos(transacoes, perfil)

    # -- Sidebar --
    with st.sidebar:
        st.markdown("**LLM**")
        provider = st.selectbox("Provedor", ["Google Gemini", "OpenAI", "Ollama (Local)"], label_visibility="collapsed")

        if provider != "Ollama (Local)":
            api_key = st.text_input("API Key", type="password", label_visibility="collapsed", placeholder=f"API Key ({provider})")
        else:
            api_key = "local"
            st.caption("Ollama precisa estar rodando em localhost:11434")

        st.divider()

        cliente = perfil["cliente"]
        st.markdown(f"**{cliente['nome']}**")
        st.caption(f"{cliente['profissao']} · {cliente['cidade']}/{cliente['estado']}")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Renda", f"R${cliente['renda_mensal']:,.0f}")
        with col2:
            saldo_medio = analise["saldo"] / analise["n_meses"]
            st.metric("Saldo médio", f"R${saldo_medio:,.0f}")

        st.divider()

        st.markdown("**Metas**")
        for meta in perfil.get("metas", []):
            progresso = meta["valor_atual"] / meta["valor_alvo"]
            st.caption(meta["descricao"])
            st.progress(min(progresso, 1.0), text=f"R${meta['valor_atual']:,.0f} / R${meta['valor_alvo']:,.0f}")

        st.divider()

        st.markdown("**Gastos por categoria**")
        cat_df = pd.DataFrame({
            "Categoria": analise["gasto_categoria"].keys(),
            "Total (R$)": analise["gasto_categoria"].values(),
        }).sort_values("Total (R$)", ascending=True)
        st.bar_chart(cat_df.set_index("Categoria"), horizontal=True)

    # -- Header --
    st.markdown("""
    <div class="main-header">
        <h1>Zenith</h1>
        <p>Controle de gastos e alertas</p>
    </div>
    """, unsafe_allow_html=True)

    # -- Alertas --
    if analise["alertas"]:
        with st.expander(f"{len(analise['alertas'])} alerta(s) neste mês", expanded=True):
            for alerta in analise["alertas"]:
                css = f"alert-{alerta['tipo']}"
                st.markdown(f'<div class="alert-card {css}">{alerta["mensagem"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="alert-card alert-success">Nenhum limite ultrapassado este mês.</div>', unsafe_allow_html=True)

    st.markdown("---")

    # -- Chat --
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if not st.session_state.messages:
        st.caption("Perguntas rápidas:")
        suggestions = [
            "Como estão meus gastos este mês?",
            "Onde posso economizar?",
            "Quanto falta pra minha reserva?",
            "Qual meu gasto total com iFood?",
        ]
        cols = st.columns(len(suggestions))
        for i, sug in enumerate(suggestions):
            if cols[i].button(sug, key=f"sug_{i}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": sug})
                st.rerun()

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Pergunte sobre seus gastos..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        if provider != "Ollama (Local)" and not api_key:
            with st.chat_message("assistant"):
                st.warning("Coloca a API Key na sidebar.")
            return

        system_prompt = construir_system_prompt(perfil, analise, produtos, historico)

        with st.chat_message("assistant"):
            with st.spinner(""):
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
                    st.error(f"Erro na LLM: {str(e)}")


if __name__ == "__main__":
    main()