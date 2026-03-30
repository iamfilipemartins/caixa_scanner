# Caixa Auction Scanner (MVP)

Scanner em Python para monitorar imóveis da Caixa, enriquecer dados, calcular score de oportunidade e enviar alertas no Telegram.

## O que este MVP faz

- baixa a lista oficial de imóveis da Caixa por UF (CSV público)
- normaliza os dados e grava em SQLite
- consulta a página de detalhe do imóvel
- extrai informações úteis como formas de pagamento, FGTS, financiamento, matrícula e link de edital
- calcula um score inicial de oportunidade
- envia alertas no Telegram para imóveis acima de um score mínimo

## Fontes de dados suportadas neste MVP

### 1) Lista completa de imóveis da Caixa
Fonte principal e mais confiável para descoberta em escala.

Exemplo de padrão de URL:
- `https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_SP.csv`

Campos normalmente presentes:
- número do imóvel
- UF
- cidade
- bairro
- endereço
- preço
- valor de avaliação
- desconto
- financiamento
- descrição

### 2) Página pública de detalhe do imóvel
Padrão:
- `https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel=<ID>`

Campos frequentemente extraídos:
- pagamento aceito
- permite FGTS
- responsabilidade por condomínio/tributos
- link para edital
- link para matrícula
- dados básicos da oferta

### 3) Editais PDF da Caixa
Quando houver edital vinculado, o sistema armazena o link. O parser de PDF foi deixado como extensão futura porque o layout varia conforme a modalidade.

## Limitações reais de obtenção de dados

### Dados com boa viabilidade de automação
- lista oficial CSV da Caixa
- página de detalhe do imóvel
- link e metadados do edital
- link da matrícula quando disponível
- filtros internos por UF

### Dados com viabilidade parcial
- parsing detalhado do edital PDF
- parsing da matrícula PDF
- resultado oficial da licitação
- ocupação real e passivos específicos

### Dados mais difíceis ou frágeis
- valor de mercado preciso via portais privados
- aluguel real de mercado em escala sem contrato/API
- condomínio/IPTU em aberto
- status real de ocupação
- litígios específicos do imóvel sem análise documental/jurídica

## Recomendação prática

Use o sistema em 3 camadas:

1. **Camada automática confiável**
   - Caixa CSV + detalhe do imóvel
2. **Camada semi-automática**
   - edital, matrícula e regras por modalidade
3. **Camada humana**
   - jurídico, vistoria, comparáveis de mercado e confirmação de ocupação

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env
```

Preencha no `.env`:

```env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
DATABASE_URL=sqlite:///caixa_scanner.db
DEFAULT_UFS=SP,MG,RJ
ALERT_MIN_SCORE=70
REQUEST_TIMEOUT=30
USER_AGENT=Mozilla/5.0 (compatible; CaixaScanner/1.0)
```

## Execução

Rodar pipeline completo:

```bash
python -m caixa_scanner.main scan --ufs SP MG
```

Escanear estados:

```bash
python -m caixa_scanner.main import-csv-batch ` "C:\Users\Administrador\Downloads\Lista_imoveis_MG.csv" ` "C:\Users\Administrador\Downloads\Lista_imoveis_SP.csv" ` "C:\Users\Administrador\Downloads\Lista_imoveis_RJ.csv"
```

Escanear estado específico:

```bash
python -m caixa_scanner.main import-csv "C:\Users\Administrador\Downloads\Lista_imoveis_MG.csv"
```
Somente listar oportunidades top:

```bash
python -m caixa_scanner.main top --limit 20
```

Enviar alertas novamente para itens elegíveis:

```bash
python -m caixa_scanner.main alert --min-score 75
```

Enviar alertas novamente para cidades elegíveis:

```bash
python -m caixa_scanner.main send-alerts --min-score 82 --cities "IPATINGA,BELO HORIZONTE" --limit 20
```
## Score atual do MVP

O score foi desenhado para ser conservador e explicável.

Componentes:
- desconto bruto
- desconto vs avaliação
- financiamento permitido
- FGTS permitido
- penalização por texto de risco na descrição
- bônus por tipologia residencial
- bônus por área/quartos/vaga quando detectáveis


## Dashboard web

O projeto agora inclui um dashboard em **Streamlit** para visualizar:

- melhores oportunidades por estado
- score médio e desconto médio por filtro
- ranking geral filtrado
- comparação entre score e desconto
- exportação da base filtrada em CSV

### Como abrir

Depois de rodar um scan e popular o banco:

```bash
python -m caixa_scanner.main dashboard
```

Ou diretamente com Streamlit:

```bash
streamlit run src/caixa_scanner/dashboard/app.py
```

Parâmetros opcionais:

```bash
python -m caixa_scanner.main dashboard --host 0.0.0.0 --port 8502
```

### O que o dashboard mostra

- **Visão por estado**: melhor imóvel encontrado em cada UF filtrada
- **KPIs**: quantidade, score médio, desconto médio e potencial bruto médio
- **Gráficos**: score médio por estado, volume por estado e dispersão score x desconto
- **Ranking detalhado**: tabela ordenada pelas melhores oportunidades
- **Exportação**: download do CSV já filtrado

## Próximas evoluções sugeridas

- parser robusto de edital PDF
- parser de matrícula PDF
- integrações de comparáveis de mercado via upload manual/API licenciada
- cache HTTP e fila de jobs
- classificação por estratégia: moradia, aluguel, flip, evitar
- modelo de valor justo por bairro/cidade

## Observação importante

Este projeto é um **scanner de triagem**, não um parecer jurídico ou avaliação definitiva. Em imóveis da Caixa, os maiores riscos costumam estar em:
- ocupação
- débitos e responsabilidades contratuais
- liquidez da região
- estado real de conservação
- documentação
