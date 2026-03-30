from __future__ import annotations

import logging
import math
import random
import re
import time
import unicodedata
from io import StringIO
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests

from ..schemas import PropertyIn
from ..utils import build_session


logger = logging.getLogger(__name__)

CSV_URL_TEMPLATE = "https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_{uf}.csv"
DETAIL_URL_TEMPLATE = "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnimovel={property_code}"

COLUMN_MAP = {
    "NÂ° do imÃ³vel": "property_code",
    "N do imÃ³vel": "property_code",
    "NÂ° do imovel": "property_code",
    "N do imovel": "property_code",
    "N do imvel": "property_code",
    "UF": "uf",
    "Cidade": "city",
    "Bairro": "neighborhood",
    "EndereÃ§o": "address",
    "Endereco": "address",
    "Endereo": "address",
    "PreÃ§o": "price",
    "Preco": "price",
    "Preo": "price",
    "Valor de avaliaÃ§Ã£o": "appraisal_value",
    "Valor de avaliacao": "appraisal_value",
    "Valor de avaliao": "appraisal_value",
    "Desconto": "discount_pct",
    "Financiamento": "financing_text",
    "Financiamento ": "financing_text",
    "DescriÃ§Ã£o": "description",
    "Descricao": "description",
    "Descrio": "description",
    "Modalidade de venda": "sale_mode",
    "Link de acesso": "detail_url",
}

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "text/csv,application/octet-stream,text/plain,*/*",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://venda-imoveis.caixa.gov.br/",
    "Connection": "keep-alive",
}


def br_to_float(value):
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(" ", "")

    try:
        return float(text)
    except ValueError:
        return None


def normalize_text(text: str | None) -> str:
    if text is None:
        return ""

    value = str(text).strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"\s+", " ", value).strip()
    return value


def extract_float_flexible(patterns: list[str], text: str) -> float | None:
    norm_text = normalize_text(text or "")

    for pattern in patterns:
        match = re.search(pattern, norm_text, flags=re.IGNORECASE)
        if not match:
            continue

        value = match.group(1).strip()
        if "," in value:
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(" ", "")

        try:
            return float(value)
        except ValueError:
            continue

    return None


def extract_int_flexible(patterns: list[str], text: str) -> int | None:
    norm_text = normalize_text(text or "")

    for pattern in patterns:
        match = re.search(pattern, norm_text, flags=re.IGNORECASE)
        if not match:
            continue

        try:
            return int(match.group(1))
        except ValueError:
            continue

    return None


def parse_description_fields(description: str) -> dict:
    raw_text = (description or "").strip()
    norm_text = normalize_text(raw_text)

    property_type = None
    if raw_text:
        property_type = raw_text.split(",")[0].strip().lower()

    if property_type:
        property_type_norm = normalize_text(property_type)
        if "apartamento" in property_type_norm:
            property_type = "apartamento"
        elif "casa" in property_type_norm:
            property_type = "casa"
        elif "terreno" in property_type_norm:
            property_type = "terreno"
        elif "sobrado" in property_type_norm:
            property_type = "sobrado"
        elif "imovel comercial" in property_type_norm or "comercial" in property_type_norm:
            property_type = "comercial"

    total_area_m2 = extract_float_flexible(
        [
            r"([\d\.,]+)\s+de\s+(?:a?rea)\s+total",
            r"([\d\.,]+)\s+de\s+(?:a?rea)\s+total,",
        ],
        raw_text,
    )
    private_area_m2 = extract_float_flexible(
        [
            r"([\d\.,]+)\s+de\s+(?:a?rea)\s+privativa",
            r"([\d\.,]+)\s+de\s+(?:a?rea)\s+privativa,",
        ],
        raw_text,
    )
    land_area_m2 = extract_float_flexible(
        [
            r"([\d\.,]+)\s+de\s+(?:a?rea)\s+do\s+terreno",
            r"([\d\.,]+)\s+de\s+(?:a?rea)\s+de\s+terreno",
        ],
        raw_text,
    )
    bedrooms = extract_int_flexible(
        [
            r"(\d+)\s+qto\(s\)",
            r"(\d+)\s+quarto\(s\)",
            r"(\d+)\s+dormitorio\(s\)",
        ],
        raw_text,
    )
    parking_spots = extract_int_flexible(
        [
            r"(\d+)\s+vaga\(s\)\s+de garagem",
            r"(\d+)\s+vaga\(s\)",
            r"garagem,\s*(\d+)\s+vaga\(s\)",
        ],
        raw_text,
    )

    bathrooms = extract_int_flexible(
        [
            r"(\d+)\s+wc\b",
            r"(\d+)\s+banheiro\(s\)",
        ],
        raw_text,
    )
    if bathrooms is None:
        wc_matches = re.findall(r"\bwc\b", norm_text)
        if wc_matches:
            bathrooms = len(wc_matches)

    return {
        "property_type": property_type,
        "total_area_m2": total_area_m2,
        "private_area_m2": private_area_m2,
        "land_area_m2": land_area_m2,
        "bedrooms": bedrooms,
        "parking_spots": parking_spots,
        "bathrooms": bathrooms,
    }


def is_blocked_response(text: str, content_type: str | None) -> bool:
    text_lower = (text or "").lower()
    ctype = (content_type or "").lower()

    if "radware bot manager block" in text_lower:
        return True
    if "<html" in text_lower or "<head>" in text_lower:
        return True
    if "text/html" in ctype:
        return True

    return False


class CaixaCsvSource:
    def __init__(self) -> None:
        self.session = build_session()

    @staticmethod
    def _parse_financing_value(value: str) -> bool | None:
        normalized = normalize_text(value)
        if normalized in {"sim", "s", "yes", "y"}:
            return True
        if normalized in {"nao", "no", "n"}:
            return False
        return None

    @staticmethod
    def _records_to_properties(df: pd.DataFrame) -> list[PropertyIn]:
        records = df.to_dict(orient="records")
        clean_records = []

        for record in records:
            clean = {}
            for key, value in record.items():
                if isinstance(value, float) and math.isnan(value):
                    clean[key] = None
                else:
                    clean[key] = value
            clean_records.append(clean)

        return [PropertyIn(**record) for record in clean_records]

    def _read_csv_text_to_dataframe(self, text: str, skiprows: int) -> pd.DataFrame:
        clean_text = "\n".join(line for line in text.splitlines() if line.strip())
        df = pd.read_csv(
            StringIO(clean_text),
            sep=";",
            skiprows=skiprows,
            dtype=str,
            encoding="utf-8",
            engine="python",
        )
        df = df.dropna(axis=1, how="all")
        df.columns = [str(column).strip() for column in df.columns]

        for column in df.columns:
            df[column] = df[column].astype(str).str.strip()

        return df

    def _normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("CSV columns before normalization: %s", list(df.columns))
        logger.info("CSV rows before normalization: %s", len(df))

        df = df.rename(columns=COLUMN_MAP)
        keep_cols = list(dict.fromkeys([column for column in COLUMN_MAP.values() if column in df.columns]))
        df = df[keep_cols].copy()

        if "price" in df.columns:
            df["price"] = df["price"].apply(br_to_float)
        if "appraisal_value" in df.columns:
            df["appraisal_value"] = df["appraisal_value"].apply(br_to_float)
        if "discount_pct" in df.columns:
            df["discount_pct"] = df["discount_pct"].apply(br_to_float)
        if "property_code" in df.columns:
            df["property_code"] = df["property_code"].astype(str).str.strip()
        if "uf" in df.columns:
            df["uf"] = df["uf"].astype(str).str.strip().str.upper()
        if "financing_text" in df.columns:
            df["financing_text"] = df["financing_text"].fillna("").astype(str).str.strip()
            df["accepts_financing"] = df["financing_text"].apply(self._parse_financing_value)
        if "description" not in df.columns:
            df["description"] = ""

        parsed = df["description"].fillna("").apply(parse_description_fields)
        parsed_df = pd.DataFrame(list(parsed))
        for column in parsed_df.columns:
            df[column] = parsed_df[column]

        if "property_code" not in df.columns:
            raise RuntimeError(
                f"Coluna 'property_code' nÃ£o foi encontrada apÃ³s renomeaÃ§Ã£o. "
                f"Colunas disponÃ­veis: {list(df.columns)}"
            )

        logger.info("CSV rows after normalization: %s", len(df))
        return df

    def download_csv_for_uf(self, uf: str, output_dir: str) -> str:
        uf = str(uf).strip().upper()
        url = CSV_URL_TEMPLATE.format(uf=uf)

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        file_path = output_path / f"Lista_imoveis_{uf}.csv"

        logger.info("Downloading CSV for UF=%s from %s", uf, url)

        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)

        response = session.get(url, timeout=30)
        logger.info(
            "Download response UF=%s status=%s content-type=%s",
            uf,
            response.status_code,
            response.headers.get("content-type"),
        )

        response.raise_for_status()

        if is_blocked_response(response.text, response.headers.get("content-type")):
            raise RuntimeError(
                f"A Caixa bloqueou a requisiÃ§Ã£o para a UF {uf} e retornou HTML em vez do CSV."
            )

        file_path.write_text(response.text, encoding="utf-8", errors="ignore")
        logger.info("Saved CSV for UF=%s at %s", uf, file_path)
        return str(file_path)

    def fetch_dataframe_for_uf(self, uf: str) -> pd.DataFrame:
        url = CSV_URL_TEMPLATE.format(uf=uf)
        logger.info("Fetching CSV for UF=%s from %s", uf, url)

        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)

        time.sleep(random.uniform(1.5, 3.5))

        response = session.get(url, timeout=30)
        logger.info(
            "Fetch response UF=%s status=%s content-type=%s size=%s",
            uf,
            response.status_code,
            response.headers.get("content-type"),
            len(response.text),
        )

        response.raise_for_status()

        if is_blocked_response(response.text, response.headers.get("content-type")):
            raise RuntimeError(
                "A Caixa bloqueou a requisiÃ§Ã£o automatizada e retornou uma pÃ¡gina HTML "
                "do Radware Bot Manager em vez do CSV."
            )

        raw_df = self._read_csv_text_to_dataframe(response.text, skiprows=2)
        return self._normalize_dataframe(raw_df)

    def fetch_properties_for_uf(self, uf: str) -> list[PropertyIn]:
        df = self.fetch_dataframe_for_uf(uf)
        return self._records_to_properties(df)

    def fetch_properties_from_csv_file(self, file_path: str) -> list[PropertyIn]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Arquivo nÃ£o encontrado: {file_path}")

        text = path.read_text(encoding="utf-8", errors="ignore")
        raw_df = self._read_csv_text_to_dataframe(text, skiprows=1)
        normalized_df = self._normalize_dataframe(raw_df)
        return self._records_to_properties(normalized_df)

    def fetch_many(self, ufs: Iterable[str]) -> list[PropertyIn]:
        results: list[PropertyIn] = []
        for uf in ufs:
            try:
                results.extend(self.fetch_properties_for_uf(uf))
            except Exception as exc:
                logger.error("Failed to fetch properties for UF=%s: %s", uf, exc)
        return results
