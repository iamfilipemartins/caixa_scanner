# Caixa Scanner

Scanner em Python para monitorar imóveis da Caixa, enriquecer dados públicos, calcular score de oportunidade e enviar alertas no Telegram.

## O que o projeto faz

- baixa a lista oficial de imóveis da Caixa por UF
- normaliza e persiste os dados em SQLite
- consulta a página pública de detalhe do imóvel
- extrai sinais úteis como FGTS, financiamento, matrícula e edital
- calcula score de oportunidade e score focado em moradia
- envia alertas filtrados no Telegram
- disponibiliza dashboard em Streamlit com filtros e ranking

## Estrutura principal

- `src/caixa_scanner/sources`: ingestão de CSV e detalhe do imóvel
- `src/caixa_scanner/valuation`: regras de score
- `src/caixa_scanner/repository.py`: acesso aos dados
- `src/caixa_scanner/pipeline.py`: orquestração dos fluxos
- `src/caixa_scanner/dashboard/app.py`: dashboard Streamlit
- `tests`: testes automatizados do parsing, scoring, repositório e pipeline

## Setup

```bash
python -m venv .venv
```

Ativação no Windows:

```powershell
.venv\Scripts\activate
```

Instale as dependências principais:

```bash
pip install -r requirements.txt
```

Se quiser rodar os testes:

```bash
pip install -e .[dev]
```

Crie o arquivo de ambiente:

```bash
copy .env.example .env
```

## Variáveis de ambiente

```env
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id
TELEGRAM_ENABLED=true
DATABASE_URL=sqlite:///caixa_scanner.db
DEFAULT_UFS=SP,MG,RJ
ALERT_MIN_SCORE=70
ALERT_CITIES=IPATINGA,BELO HORIZONTE
REQUEST_TIMEOUT=30
USER_AGENT=Mozilla/5.0 (compatible; CaixaScanner/1.0)
```

## Execução

Rodar pipeline completo:

```bash
python -m caixa_scanner.main scan --ufs SP MG
```

Baixar CSVs:

```bash
python -m caixa_scanner.main download-csv --ufs MG --ufs SP --output-dir C:\temp\caixa
```

Importar um CSV local:

```bash
python -m caixa_scanner.main import-csv "C:\Users\Administrador\Downloads\Lista_imoveis_MG.csv"
```

Importar vários CSVs:

```bash
python -m caixa_scanner.main import-csv-batch "C:\Users\Administrador\Downloads\Lista_imoveis_MG.csv" "C:\Users\Administrador\Downloads\Lista_imoveis_SP.csv"
```

Enviar alertas:

```bash
python -m caixa_scanner.main send-alerts --min-score 82 --cities "IPATINGA,BELO HORIZONTE" --limit 20
```

Abrir dashboard:

```bash
python -m caixa_scanner.main dashboard
```

## Testes

```bash
python -m pytest
```

## Dashboard

O dashboard permite:

- filtrar por UF, cidade, bairro, tipo, quartos, vagas, área, preço e score
- visualizar KPIs agregados
- comparar score e desconto
- consultar rapidamente um imóvel por código
- exportar a base filtrada em CSV

## Limitações atuais

- parsing de edital PDF ainda não foi implementado
- parsing de matrícula PDF ainda não foi implementado
- não há integração com comparáveis de mercado
- o score atual é heurístico e conservador
- o projeto é uma ferramenta de triagem, não um parecer jurídico ou avaliação definitiva

## Próximas evoluções sugeridas

- parser de edital PDF
- parser de matrícula PDF
- score por estratégia: moradia, aluguel e flip
- histórico de mudanças de preço e desconto
- cache HTTP e fila de processamento
- modelo de valor justo por bairro e cidade
