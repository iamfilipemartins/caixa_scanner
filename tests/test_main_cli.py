from __future__ import annotations

from typer.testing import CliRunner

from caixa_scanner import main


runner = CliRunner()


class DummyPipeline:
    def scan(self, ufs):
        self.last_scan = ufs
        return 7

    def import_csv(self, file_path):
        self.last_import = file_path
        return 3

    def import_csv_batch(self, file_paths):
        self.last_batch = file_paths
        return 5

    def download_and_import_csvs(self, ufs, output_dir):
        self.last_download_import = (ufs, output_dir)
        return 4

    def download_csvs(self, ufs, output_dir):
        self.last_download = (ufs, output_dir)
        return ["a.csv", "b.csv"]

    def reprocess(self, limit=100, pending_only=True, rescore_only=False):
        self.last_reprocess = (limit, pending_only, rescore_only)
        return 6

    def send_alerts(self, min_score=None, cities=None, limit=50):
        self.last_alerts = (min_score, cities, limit)
        return 2


def test_scan_command_uses_normalized_ufs(monkeypatch):
    pipeline = DummyPipeline()
    monkeypatch.setattr(main, "CaixaScannerPipeline", lambda: pipeline)

    result = runner.invoke(main.app, ["scan", "--ufs", "mg", "--ufs", "sp"])

    assert result.exit_code == 0
    assert "7 imoveis processados para: MG, SP" in result.stdout
    assert pipeline.last_scan == ["MG", "SP"]


def test_send_alerts_command_splits_cities(monkeypatch):
    pipeline = DummyPipeline()
    monkeypatch.setattr(main, "CaixaScannerPipeline", lambda: pipeline)

    result = runner.invoke(
        main.app,
        ["send-alerts", "--min-score", "82", "--cities", "Ipatinga, Belo Horizonte", "--limit", "20"],
    )

    assert result.exit_code == 0
    assert "2 alerta(s) enviado(s)." in result.stdout
    assert pipeline.last_alerts == (82.0, ["IPATINGA", "BELO HORIZONTE"], 20)


def test_import_csv_command_reports_result(monkeypatch):
    pipeline = DummyPipeline()
    monkeypatch.setattr(main, "CaixaScannerPipeline", lambda: pipeline)

    result = runner.invoke(main.app, ["import-csv", "C:\\temp\\lista.csv"])

    assert result.exit_code == 0
    assert "3 imoveis importados do arquivo: C:\\temp\\lista.csv" in result.stdout
    assert pipeline.last_import == "C:\\temp\\lista.csv"


def test_reprocess_command_passes_incremental_flags(monkeypatch):
    pipeline = DummyPipeline()
    monkeypatch.setattr(main, "CaixaScannerPipeline", lambda: pipeline)

    result = runner.invoke(main.app, ["reprocess", "--limit", "25", "--all", "--rescore-only"])

    assert result.exit_code == 0
    assert "6 imoveis reprocessados." in result.stdout
    assert pipeline.last_reprocess == (25, False, True)
