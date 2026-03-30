from __future__ import annotations

import logging
import subprocess
import sys

import typer

from .config import settings
from .database import SessionLocal, init_db
from .pipeline import CaixaScannerPipeline
from .repository import PropertyRepository


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)

app = typer.Typer(help="Scanner de oportunidades de imóveis Caixa")


@app.command()
def scan(ufs: list[str] = typer.Option(None, "--ufs")) -> None:
    """Baixa dados da Caixa, enriquece e grava no banco."""
    pipeline = CaixaScannerPipeline()
    normalized_ufs = settings.normalize_ufs(ufs)
    total = pipeline.scan(normalized_ufs)
    typer.echo(f"{total} imóveis processados para: {', '.join(normalized_ufs)}")


@app.command("download-csv")
def download_csv(
    ufs: list[str] = typer.Option(..., "--ufs"),
    output_dir: str = typer.Option(..., "--output-dir"),
):
    pipeline = CaixaScannerPipeline()
    files = pipeline.download_csvs(ufs, output_dir)
    typer.echo(f"{len(files)} arquivo(s) baixado(s).")


@app.command("import-csv")
def import_csv(file_path: str):
    pipeline = CaixaScannerPipeline()
    total = pipeline.import_csv(file_path)
    typer.echo(f"{total} imóveis importados do arquivo: {file_path}")


@app.command("import-csv-batch")
def import_csv_batch(file_paths: list[str]):
    pipeline = CaixaScannerPipeline()
    total = pipeline.import_csv_batch(file_paths)
    typer.echo(f"{total} imóveis importados a partir de {len(file_paths)} arquivos.")


@app.command("download-and-import-csv")
def download_and_import_csv(
    ufs: list[str] = typer.Option(..., "--ufs"),
    output_dir: str = typer.Option(..., "--output-dir"),
):
    pipeline = CaixaScannerPipeline()
    total = pipeline.download_and_import_csvs(ufs, output_dir)
    typer.echo(f"{total} imóveis baixados/importados.")


@app.command()
def top(limit: int = 20) -> None:
    """Mostra as melhores oportunidades no banco local."""
    init_db()
    with SessionLocal() as session:
        repo = PropertyRepository(session)
        items = repo.top_opportunities(limit=limit)
        for item in items:
            typer.echo(
                f"score={item.opportunity_score:>5} | uf={item.uf} | cidade={item.city} | bairro={item.neighborhood} | "
                f"preço={item.price} | desconto={item.discount_pct} | código={item.property_code}"
            )


@app.command("send-alerts")
def send_alerts(
    min_score: float = typer.Option(80.0, "--min-score"),
    cities: str = typer.Option(",".join(settings.alert_cities), "--cities"),
    limit: int = typer.Option(50, "--limit"),
):
    pipeline = CaixaScannerPipeline()
    city_list = [c.strip().upper() for c in cities.split(",") if c.strip()]
    total = pipeline.send_alerts(min_score=min_score, cities=city_list, limit=limit)
    typer.echo(f"{total} alerta(s) enviado(s).")


@app.command()
def alert(min_score: float = typer.Option(settings.alert_min_score, "--min-score")) -> None:
    """Envia alertas Telegram para imóveis elegíveis."""
    pipeline = CaixaScannerPipeline()
    total = pipeline.send_alerts(min_score=min_score)
    typer.echo(f"{total} alerta(s) processado(s).")


@app.command()
def dashboard(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8501, "--port"),
) -> None:
    """Abre o dashboard web em Streamlit."""
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "src/caixa_scanner/dashboard/app.py",
        "--server.address",
        host,
        "--server.port",
        str(port),
    ]
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    app()
