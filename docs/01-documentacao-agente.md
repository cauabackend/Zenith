# Documentação do Agente — Zenith

## Qual problema o Zenith resolve

A maioria das pessoas sabe que gasta mais do que deveria em certas categorias, mas não tem uma visão clara de quanto nem de onde cortar. Abrir o app do banco e ver uma lista de transações não ajuda muito — é informação demais sem contexto nenhum.

O Zenith é um chatbot que pega os dados financeiros do cliente (transações, perfil, metas), analisa tudo antes da conversa começar, e responde perguntas em linguagem natural. Se o cara estourou o limite de alimentação no mês, o agente avisa. Se ele pergunta "onde posso economizar?", a resposta vem com números reais, não com conselho genérico de blog.

O caso de uso principal é controle de gastos com alertas. Não é robo-advisor, não faz operação de investimento, não substitui um assessor financeiro. Ele olha pra onde o dinheiro tá indo e te conta o que tá acontecendo.

## Persona e tom de voz

O Zenith fala como um amigo que entende de finanças. Direto, sem jargão, com empatia quando o gasto tá feio. Usa português brasileiro, pode usar emoji com moderação, e quando faz conta mostra o raciocínio.

Ele não é passivo-agressivo quando o cliente estoura um limite. A ideia é que o cara se sinta confortável perguntando coisas sem medo de ser julgado.

Exemplos do tom:

- "Seus gastos com alimentação esse mês já bateram R$945. O limite que você definiu é R$1.200, então ainda tem folga, mas tá andando mais rápido que nos meses anteriores."
- "Achei uma compra de R$1.299 na Apple Store no dia 10/03. Foi planejada ou escapou? Porque ela puxou o mês pra cima."

## Arquitetura

O fluxo é simples:

1. O app carrega os 4 arquivos de dados (`transacoes.csv`, `historico_atendimento.csv`, `perfil_investidor.json`, `produtos_financeiros.json`)
2. O módulo de análise roda sobre as transações: agrupa por categoria, calcula médias mensais, compara com os limites do cliente, detecta transações atípicas
3. Tudo isso (dados brutos + análise + perfil + produtos) é embutido no system prompt da LLM
4. O usuário digita no chat, a mensagem vai pra LLM junto com o system prompt, e a resposta volta contextualizada

Não tem banco de dados, não tem RAG, não tem embedding. A base de conhecimento inteira cabe no context window da LLM. Pra um protótipo com dados mockados, isso funciona. Em produção com milhares de transações, precisaria de outra abordagem.

O app suporta três provedores de LLM: Google Gemini (grátis), OpenAI e Ollama local. A troca é feita na sidebar sem precisar reiniciar.

## Segurança e anti-alucinação

Esse é o ponto mais delicado num agente financeiro. A LLM não pode inventar uma transação que não existe ou sugerir um produto que não tá no catálogo. As regras que implementei:

- O system prompt diz explicitamente "use APENAS os dados fornecidos abaixo"
- Se a LLM não encontra informação nos dados, ela é instruída a dizer que não tem essa informação
- Produtos financeiros recomendados só podem vir do catálogo em `produtos_financeiros.json`
- Conselhos jurídicos e tributários são barrados — o agente sugere procurar um profissional
- As sugestões de economia são calculadas a partir dos padrões reais de gasto, não de regras genéricas

Isso não elimina 100% o risco de alucinação (nenhum prompt consegue isso), mas reduz bastante. Nas métricas (doc 04) eu descrevo como avaliar isso.
