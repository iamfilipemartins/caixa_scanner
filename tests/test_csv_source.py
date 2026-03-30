from __future__ import annotations

from pathlib import Path

from caixa_scanner.sources.caixa_csv import CaixaCsvSource, parse_description_fields


def test_parse_description_fields_extracts_main_attributes():
    parsed = parse_description_fields(
        "Apartamento, 90,00 de area total, 70,00 de area privativa, "
        "2 quarto(s), 1 vaga(s) de garagem, 2 wc"
    )

    assert parsed["property_type"] == "apartamento"
    assert parsed["total_area_m2"] == 90.0
    assert parsed["private_area_m2"] == 70.0
    assert parsed["bedrooms"] == 2
    assert parsed["parking_spots"] == 1
    assert parsed["bathrooms"] == 2


def test_fetch_properties_from_csv_file_handles_expected_headers(tmp_path: Path):
    csv_file = tmp_path / "lista.csv"
    csv_file.write_text(
        "\n".join(
            [
                "arquivo exportado",
                "NÂ° do imÃ³vel;UF;Cidade;Bairro;EndereÃ§o;PreÃ§o;Valor de avaliaÃ§Ã£o;Desconto;Financiamento;DescriÃ§Ã£o;Link de acesso",
                "123;MG;Belo Horizonte;Savassi;Rua A, 10;100.000,00;200.000,00;50,00;Sim;Apartamento, 90,00 de area total, 70,00 de area privativa, 2 quarto(s), 1 vaga(s) de garagem, 2 wc;https://example.com/imovel/123",
            ]
        ),
        encoding="utf-8",
    )

    items = CaixaCsvSource().fetch_properties_from_csv_file(str(csv_file))

    assert len(items) == 1
    item = items[0]
    assert item.property_code == "123"
    assert item.uf == "MG"
    assert item.accepts_financing is True
    assert item.private_area_m2 == 70.0
    assert item.total_area_m2 == 90.0
    assert item.bedrooms == 2
    assert item.parking_spots == 1
    assert item.bathrooms == 2


def test_fetch_properties_from_csv_file_handles_corrupted_headers(tmp_path: Path):
    csv_file = tmp_path / "lista_corrompida.csv"
    csv_file.write_text(
        "\n".join(
            [
                "arquivo exportado",
                "N do imvel;UF;Cidade;Bairro;Endereco;Preco;Valor de avaliao;Desconto;Financiamento;Descricao",
                "999;SP;Campinas;Centro;Rua B, 99;250000.50;300000.00;16.50;No;Casa, 120.00 de area total, 80.00 de area privativa, 3 quarto(s), 2 vaga(s) de garagem",
            ]
        ),
        encoding="utf-8",
    )

    items = CaixaCsvSource().fetch_properties_from_csv_file(str(csv_file))

    assert len(items) == 1
    item = items[0]
    assert item.property_code == "999"
    assert item.accepts_financing is False
    assert item.property_type == "casa"
    assert item.private_area_m2 == 80.0
    assert item.bedrooms == 3
    assert item.parking_spots == 2
