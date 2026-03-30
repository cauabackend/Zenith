# Roteiro do Pitch — Zenith

Duração: ~3 minutos.

---

## Abertura (30s)

"Você sabe quanto gastou com delivery no último mês? E nos últimos três? A maioria das pessoas não sabe. O extrato do banco tá lá, mas ninguém lê 60 linhas de transação pra descobrir pra onde o dinheiro foi.

O Zenith resolve isso. É um chatbot financeiro que lê seus dados de gasto e conversa com você sobre eles."

## O problema (30s)

"Apps de banco mostram transações, mas não interpretam. Planilhas funcionam pra quem tem disciplina de preencher todo dia. A maioria das pessoas quer uma resposta rápida: tô gastando demais? Onde? E o que eu faço?

Hoje não existe um canal simples onde o cliente pergunta em linguagem natural e recebe uma resposta baseada nos dados dele, não em conselho genérico."

## A solução (60s)

"O Zenith é um agente financeiro em Streamlit que usa IA generativa. Antes do chat começar, ele já analisou todas as transações, agrupou por categoria, comparou com os limites que o cliente definiu, e detectou gastos fora do padrão.

Tudo isso vira contexto pro modelo de linguagem. Então quando o cliente pergunta 'como estão meus gastos?', a resposta vem com números reais: 'você gastou R$945 com alimentação, tá em 79% do seu limite, e o iFood sozinho representa 40% disso'.

O agente também acompanha metas. Se o cliente quer montar uma reserva de emergência de R$15.600 e tem R$2.800 guardados, o Zenith calcula quanto precisa guardar por mês pra chegar lá no prazo.

E ele não inventa. Se não tem a informação, ele fala. Se a pergunta é tributária, ele manda procurar um contador."

## Diferencial (30s)

"O que separa o Zenith de um chatbot genérico é que ele não dá conselho de blog. Cada resposta é calculada a partir dos dados daquele cliente. Ele sabe que o cara gastou R$1.299 em AirPods no dia 10 de março porque leu a transação. E sabe que isso estourou o orçamento do mês porque comparou com o limite.

O anti-alucinação é tratado no prompt: o agente só trabalha com os dados que recebeu."

## Fechamento (30s)

"O Zenith é um protótipo, mas a lógica funciona com dados reais. Troca os CSVs mockados por uma API bancária e o app vira um assistente financeiro de verdade.

A stack é simples: Python, Streamlit, Pandas, e qualquer LLM que aceite um system prompt longo. Gemini, OpenAI, ou modelo local com Ollama."
