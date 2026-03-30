# Base de Conhecimento — Zenith

## Estratégia de dados

O agente não consulta APIs bancárias nem tem acesso a dados reais. Tudo roda em cima de dados mockados que simulam três meses de vida financeira de um desenvolvedor de 27 anos em São Paulo. Escolhi esse perfil porque é próximo o suficiente do público-alvo pra que os cenários façam sentido.

## Os 4 arquivos

### transacoes.csv

65 transações entre janeiro e março de 2025. Cada linha tem data, descrição, categoria, valor, tipo (débito/crédito) e meio de pagamento. As categorias são: Alimentação, Transporte, Moradia, Entretenimento, Vestuário, Saúde, Educação, Eletrônicos e Renda.

Incluí padrões propositais pra testar o agente: gastos recorrentes com iFood (aparece 9 vezes), uma compra atípica de R$1.299 na Apple Store, e um aumento gradual nos gastos com alimentação ao longo dos três meses.

### perfil_investidor.json

Dados do cliente: nome, idade, renda, perfil de risco (moderado), metas financeiras (reserva de emergência de R$15.600 e viagem ao Japão de R$25.000), e os limites de gasto por categoria que ele mesmo definiu.

Os limites são o coração do sistema de alertas. Quando o gasto de uma categoria no mês atual passa de 80% do limite, o agente gera um alerta amarelo. Passa de 100%, alerta vermelho.

### produtos_financeiros.json

Catálogo com 6 produtos: CDB, Tesouro Selic, LCI/LCA, fundo multimercado, conta com cashback e seguro de vida. Cada um tem risco, rentabilidade, liquidez e pra quem é indicado.

O agente só pode recomendar produtos que estejam nessa lista. Se o cliente perguntar sobre cripto ou ações, o agente vai dizer que não tem isso no catálogo.

### historico_atendimento.csv

8 registros de atendimentos anteriores com data, canal, assunto, resumo e sentimento. Serve pra dar contexto pro agente sobre o histórico do relacionamento. Se o cliente já perguntou sobre investimentos antes, o agente sabe.

## Como os dados entram no agente

Na hora de montar o system prompt, o app.py faz uma análise completa das transações (gasto por categoria, médias mensais, alertas, transações atípicas) e joga tudo — dados brutos e análise — no prompt. A LLM recebe esse contexto inteiro a cada mensagem.

Não usei RAG nem embedding porque o volume de dados é pequeno o suficiente pra caber no context window. Se fosse escalar pra um histórico de anos, precisaria fragmentar e buscar só o relevante.

## Adaptação

Os dados podem ser alterados livremente. Pra testar cenários diferentes basta editar os CSVs e JSONs. O app relê tudo a cada execução (com cache do Streamlit), então as mudanças aparecem na próxima sessão.
