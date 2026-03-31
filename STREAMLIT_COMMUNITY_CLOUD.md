# Deploy no Streamlit Community Cloud

Este projeto pode ser publicado no Streamlit Community Cloud diretamente a partir do GitHub.

## Entry point

Use este arquivo como entrypoint do app:

```text
src/caixa_scanner/dashboard/app.py
```

## Passo a passo

1. Publique o repositório no GitHub.
2. Acesse [share.streamlit.io](https://share.streamlit.io/).
3. Crie um novo app e selecione o repositório e a branch.
4. Informe o entrypoint `src/caixa_scanner/dashboard/app.py`.
5. Se quiser usar variáveis de ambiente, cadastre em `Secrets` os mesmos valores do `.env`.
6. Faça o deploy.
7. Quando o app abrir, use a seção `Importar CSV da Caixa no app` para enviar um ou mais arquivos `Lista_imoveis_UF.csv`.

## Observações

- O deploy inicial pode usar `DATABASE_URL=sqlite:///caixa_scanner.db`.
- SQLite atende bem para demonstração e uso leve, mas o armazenamento no Community Cloud pode ser perdido entre rebuilds e redeploys.
- Para persistência mais confiável, vale migrar depois para um banco gerenciado.
