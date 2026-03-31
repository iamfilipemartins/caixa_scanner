from __future__ import annotations

import html
import sys
import tempfile
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine

SRC_ROOT = Path(__file__).resolve().parents[2]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from caixa_scanner.config import settings
from caixa_scanner.database import init_db
from caixa_scanner.pipeline import CaixaScannerPipeline


st.set_page_config(
    page_title="Caixa Scanner Dashboard",
    page_icon="house",
    layout="wide",
)

RISK_FLAG_LABELS = {
    "edital_has_occupied_risk": "Imovel ocupado",
    "edital_has_no_visit_risk": "Visitacao restrita",
    "edital_buyer_pays_condo": "Condominio por conta do comprador",
    "edital_buyer_pays_iptu": "IPTU por conta do comprador",
    "edital_has_judicial_risk": "Mencao judicial",
}

CUSTOM_CSS = """
<style>
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(0, 92, 79, 0.10), transparent 28%),
            linear-gradient(180deg, #f6f4ee 0%, #fbfaf7 45%, #f3efe5 100%);
    }
    [data-testid="stAppViewContainer"] {
        color: #17362f;
    }
    [data-testid="stAppViewContainer"] p,
    [data-testid="stAppViewContainer"] label,
    [data-testid="stAppViewContainer"] span,
    [data-testid="stAppViewContainer"] .stMarkdown,
    [data-testid="stAppViewContainer"] .stCaption {
        color: #17362f;
    }
    [data-testid="stAppViewContainer"] h1,
    [data-testid="stAppViewContainer"] h2,
    [data-testid="stAppViewContainer"] h3 {
        color: #133c33;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #202833 0%, #262934 100%);
    }
    [data-testid="stSidebar"] * {
        color: #eef3ef !important;
    }
    [data-testid="stSidebar"] [data-testid="stSidebarContent"] {
        background: linear-gradient(180deg, #202833 0%, #262934 100%);
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span {
        color: #eef3ef !important;
    }
    [data-testid="stSidebar"] [data-baseweb="select"] *,
    [data-testid="stSidebar"] [data-baseweb="select"] span,
    [data-testid="stSidebar"] .stSelectbox *,
    [data-testid="stSidebar"] .stMultiSelect * {
        color: #eef3ef !important;
    }
    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] .stSelectbox > div > div,
    [data-testid="stSidebar"] .stMultiSelect > div > div {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.10) !important;
        border-radius: 14px !important;
    }
    [data-testid="stSidebar"] .stSlider [data-baseweb="slider"] {
        padding-top: 0.4rem;
    }
    [data-testid="stSidebar"] .stSlider [role="slider"] {
        background: #d8b15a !important;
        border-color: #d8b15a !important;
    }
    [data-testid="stSidebar"] .stSlider [data-testid="stTickBar"] {
        background: rgba(255, 255, 255, 0.16) !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.6rem;
        margin-top: 1.35rem;
        margin-bottom: 1rem;
        padding: 0.35rem;
        background: rgba(255, 255, 255, 0.60);
        border: 1px solid rgba(19, 60, 51, 0.08);
        border-radius: 18px;
        box-shadow: 0 10px 24px rgba(19, 60, 51, 0.06);
        width: fit-content;
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        padding-left: 0.95rem;
        padding-right: 0.95rem;
        border-radius: 12px;
        color: #50625c;
        font-weight: 600;
        transition: background 120ms ease, color 120ms ease, transform 120ms ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(19, 60, 51, 0.06);
        color: #17362f;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #143f35 0%, #245548 100%) !important;
        color: #fffaf2 !important;
        box-shadow: 0 10px 18px rgba(19, 60, 51, 0.14);
        transform: translateY(-1px);
    }
    .stTabs [aria-selected="true"] * {
        color: #fffaf2 !important;
    }
    .dashboard-hero {
        position: relative;
        overflow: hidden;
        padding: 1.35rem 1.45rem 1.3rem 1.45rem;
        border-radius: 24px;
        background:
            radial-gradient(circle at 88% 18%, rgba(255, 223, 140, 0.38), transparent 26%),
            linear-gradient(135deg, #11342d 0%, #1c4a40 44%, #7a7247 100%);
        color: #fffaf2;
        border: 1px solid rgba(255, 249, 239, 0.14);
        box-shadow: 0 24px 42px rgba(19, 60, 51, 0.18);
        margin-bottom: 1rem;
    }
    .dashboard-hero::after {
        content: "";
        position: absolute;
        inset: auto -10% -55% auto;
        width: 320px;
        height: 320px;
        background: radial-gradient(circle, rgba(255, 223, 140, 0.24), transparent 68%);
        pointer-events: none;
    }
    .dashboard-hero h1 {
        margin: 0;
        color: #fffaf2 !important;
        font-size: 2.1rem;
        letter-spacing: -0.03em;
        line-height: 1.02;
        font-weight: 750;
        max-width: 620px;
    }
    .dashboard-hero p {
        margin: 0.7rem 0 0 0;
        color: rgba(255, 249, 239, 0.92) !important;
        font-size: 1.02rem;
        line-height: 1.45;
        max-width: 760px;
    }
    .hero-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 0.55rem;
        margin-top: 1rem;
    }
    .hero-chip {
        padding: 0.48rem 0.82rem;
        border-radius: 999px;
        background: rgba(255, 249, 239, 0.10);
        border: 1px solid rgba(255, 249, 239, 0.16);
        color: rgba(255, 250, 242, 0.96) !important;
        font-size: 0.9rem;
        font-weight: 500;
        backdrop-filter: blur(8px);
    }
    .section-title {
        margin: 1.2rem 0 0.5rem 0;
        font-size: 1.1rem;
        font-weight: 700;
        color: #17362f;
        letter-spacing: -0.02em;
    }
    .section-shell {
        margin-top: 0.8rem;
        margin-bottom: 0.8rem;
    }
    .card-row-spaced {
        display: flex;
        gap: 1rem;
        align-items: stretch;
    }
    .card-row-spaced > div {
        flex: 1 1 0;
    }
    .section-header {
        padding: 0.9rem 1rem;
        background: rgba(255, 255, 255, 0.72);
        border: 1px solid rgba(19, 60, 51, 0.08);
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(19, 60, 51, 0.08);
        margin-bottom: 0.7rem;
    }
    .section-eyebrow {
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #6a7973;
    }
    .section-header h2 {
        margin: 0.3rem 0 0 0;
        font-size: 1.9rem;
        line-height: 1.05;
        color: #133c33;
        letter-spacing: -0.03em;
    }
    .section-copy {
        margin-top: 0.35rem;
        color: #52615b;
        max-width: 760px;
    }
    .control-shell {
        padding: 0.75rem 0.9rem 0.1rem 0.9rem;
        background: rgba(255, 255, 255, 0.72);
        border: 1px solid rgba(19, 60, 51, 0.08);
        border-radius: 18px;
        box-shadow: 0 10px 30px rgba(19, 60, 51, 0.08);
        margin-bottom: 0.8rem;
    }
    .export-shell {
        padding: 1rem 1.05rem;
        background: rgba(255, 255, 255, 0.76);
        border: 1px solid rgba(19, 60, 51, 0.08);
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(19, 60, 51, 0.08);
        margin-bottom: 1rem;
    }
    .export-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.9rem;
        margin-top: 0.85rem;
    }
    .export-card {
        padding: 0.9rem 1rem;
        border-radius: 16px;
        background: rgba(19, 60, 51, 0.04);
        border: 1px solid rgba(19, 60, 51, 0.08);
    }
    .export-label {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #66756f;
    }
    .export-value {
        margin-top: 0.35rem;
        font-size: 1.28rem;
        font-weight: 700;
        color: #17362f;
    }
    .export-copy {
        margin-top: 0.35rem;
        color: #52615b;
        font-size: 0.92rem;
    }
    .lookup-shell {
        padding: 1rem 1.05rem;
        background: rgba(255, 255, 255, 0.76);
        border: 1px solid rgba(19, 60, 51, 0.08);
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(19, 60, 51, 0.08);
        margin-bottom: 1rem;
    }
    .lookup-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.9rem;
        margin-top: 1rem;
    }
    .lookup-card {
        padding: 0.95rem 1rem;
        border-radius: 16px;
        background: rgba(19, 60, 51, 0.04);
        border: 1px solid rgba(19, 60, 51, 0.08);
    }
    .lookup-kicker {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #66756f;
    }
    .lookup-title {
        margin-top: 0.35rem;
        font-size: 1.45rem;
        line-height: 1.08;
        font-weight: 700;
        color: #17362f;
    }
    .lookup-meta {
        margin-top: 0.4rem;
        color: #52615b;
        font-size: 0.96rem;
    }
    .lookup-description {
        margin-top: 0.85rem;
        color: #425750;
        font-size: 0.95rem;
        line-height: 1.45;
    }
    .support-shell {
        padding: 1rem 1.05rem;
        background: rgba(255, 255, 255, 0.76);
        border: 1px solid rgba(19, 60, 51, 0.08);
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(19, 60, 51, 0.08);
        margin-top: 0.95rem;
    }
    .support-metrics {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.8rem;
        margin: 0.2rem 0 0.95rem 0;
    }
    .support-metric {
        padding: 0.85rem 0.95rem;
        border-radius: 16px;
        background: rgba(19, 60, 51, 0.04);
        border: 1px solid rgba(19, 60, 51, 0.08);
    }
    .support-metric-label {
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #66756f;
    }
    .support-metric-value {
        margin-top: 0.3rem;
        font-size: 1.35rem;
        font-weight: 700;
        color: #17362f;
    }
    .support-metric-copy {
        margin-top: 0.22rem;
        color: #52615b;
        font-size: 0.9rem;
    }
    .stat-card {
        border-radius: 18px;
        padding: 1rem 1.05rem;
        background: rgba(255, 255, 255, 0.72);
        border: 1px solid rgba(19, 60, 51, 0.08);
        box-shadow: 0 10px 30px rgba(19, 60, 51, 0.08);
        backdrop-filter: blur(6px);
        min-height: 118px;
    }
    .stat-label {
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #5e6d67;
    }
    .stat-value {
        margin-top: 0.35rem;
        font-size: 1.8rem;
        font-weight: 700;
        color: #133c33;
    }
    .stat-caption {
        margin-top: 0.25rem;
        font-size: 0.9rem;
        color: #52615b;
    }
    .badge-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        margin: 0.45rem 0 0.25rem 0;
    }
    .badge {
        display: inline-flex;
        align-items: center;
        padding: 0.28rem 0.6rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        line-height: 1;
        border: 1px solid transparent;
    }
    .badge-score-high {
        background: rgba(19, 140, 92, 0.12);
        color: #0f6d48;
        border-color: rgba(19, 140, 92, 0.18);
    }
    .badge-score-mid {
        background: rgba(216, 177, 90, 0.18);
        color: #8a6218;
        border-color: rgba(216, 177, 90, 0.22);
    }
    .badge-score-low {
        background: rgba(166, 63, 43, 0.12);
        color: #8b3424;
        border-color: rgba(166, 63, 43, 0.2);
    }
    .badge-status-ok {
        background: rgba(19, 140, 92, 0.12);
        color: #0f6d48;
        border-color: rgba(19, 140, 92, 0.18);
    }
    .badge-status-pending {
        background: rgba(204, 120, 24, 0.12);
        color: #9c5b09;
        border-color: rgba(204, 120, 24, 0.2);
    }
    .badge-risk-low {
        background: rgba(19, 140, 92, 0.10);
        color: #0f6d48;
        border-color: rgba(19, 140, 92, 0.16);
    }
    .badge-risk-high {
        background: rgba(166, 63, 43, 0.12);
        color: #8b3424;
        border-color: rgba(166, 63, 43, 0.2);
    }
    .empty-state {
        margin-top: 1.4rem;
        padding: 1.2rem 1.3rem;
        border-radius: 18px;
        background: rgba(255, 255, 255, 0.76);
        border: 1px solid rgba(19, 60, 51, 0.08);
        box-shadow: 0 10px 30px rgba(19, 60, 51, 0.08);
    }
    .empty-state h2 {
        margin: 0 0 0.4rem 0;
        color: #133c33;
        font-size: 1.5rem;
    }
    .empty-state p {
        margin: 0.2rem 0;
        color: #38524a;
    }
    .empty-state code {
        background: rgba(19, 60, 51, 0.08);
        color: #133c33;
        padding: 0.12rem 0.35rem;
        border-radius: 6px;
    }
    .import-shell {
        position: relative;
        overflow: hidden;
        margin-top: 1rem;
        margin-bottom: 1rem;
        padding: 1.15rem 1.2rem 1rem 1.2rem;
        border-radius: 24px;
        background:
            radial-gradient(circle at top right, rgba(216, 177, 90, 0.22), transparent 26%),
            linear-gradient(135deg, rgba(17, 52, 45, 0.96) 0%, rgba(28, 74, 64, 0.92) 58%, rgba(78, 88, 58, 0.88) 100%);
        border: 1px solid rgba(255, 249, 239, 0.12);
        box-shadow: 0 24px 44px rgba(19, 60, 51, 0.16);
    }
    .import-shell::after {
        content: "";
        position: absolute;
        inset: auto -8% -42% auto;
        width: 260px;
        height: 260px;
        background: radial-gradient(circle, rgba(255, 223, 140, 0.18), transparent 70%);
        pointer-events: none;
    }
    .import-grid {
        display: grid;
        grid-template-columns: minmax(0, 1.6fr) minmax(240px, 0.9fr);
        gap: 1rem;
        align-items: start;
    }
    .import-kicker {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: rgba(255, 249, 239, 0.72);
    }
    .import-title {
        margin: 0.35rem 0 0 0;
        color: #fffaf2;
        font-size: 1.55rem;
        line-height: 1.02;
        letter-spacing: -0.03em;
        font-weight: 760;
    }
    .import-copy {
        margin-top: 0.55rem;
        color: rgba(255, 249, 239, 0.84);
        max-width: 780px;
        line-height: 1.48;
    }
    .import-code {
        display: inline-flex;
        align-items: center;
        margin-top: 0.65rem;
        padding: 0.32rem 0.6rem;
        border-radius: 999px;
        background: rgba(255, 249, 239, 0.10);
        border: 1px solid rgba(255, 249, 239, 0.12);
        color: #fff7ec;
        font-family: "Consolas", "SFMono-Regular", monospace;
        font-size: 0.83rem;
    }
    .import-steps {
        display: grid;
        gap: 0.7rem;
    }
    .import-step {
        padding: 0.78rem 0.85rem;
        border-radius: 18px;
        background: rgba(255, 249, 239, 0.08);
        border: 1px solid rgba(255, 249, 239, 0.10);
        backdrop-filter: blur(8px);
    }
    .import-step-label {
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: rgba(255, 249, 239, 0.62);
    }
    .import-step-value {
        margin-top: 0.22rem;
        color: #fffaf2;
        font-size: 0.95rem;
        line-height: 1.35;
        font-weight: 600;
    }
    .import-widget-shell {
        margin-top: 0.9rem;
        padding: 1rem;
        border-radius: 20px;
        background: rgba(255, 255, 255, 0.76);
        border: 1px solid rgba(19, 60, 51, 0.08);
        box-shadow: 0 12px 28px rgba(19, 60, 51, 0.08);
    }
    .import-widget-shell [data-testid="stFileUploaderDropzone"] {
        border: 1.5px dashed rgba(19, 60, 51, 0.18);
        border-radius: 18px;
        background:
            radial-gradient(circle at top right, rgba(216, 177, 90, 0.10), transparent 30%),
            linear-gradient(180deg, rgba(248, 246, 240, 0.95), rgba(243, 239, 229, 0.82));
        transition: border-color 140ms ease, transform 140ms ease, box-shadow 140ms ease;
        min-height: 150px;
    }
    .import-widget-shell [data-testid="stFileUploaderDropzone"]:hover {
        border-color: rgba(19, 60, 51, 0.34);
        box-shadow: 0 12px 24px rgba(19, 60, 51, 0.08);
        transform: translateY(-1px);
    }
    .import-widget-shell [data-testid="stFileUploaderDropzone"] * {
        color: #17362f !important;
    }
    .import-widget-shell .stButton > button {
        min-height: 52px;
        border-radius: 16px;
        border: 1px solid rgba(19, 60, 51, 0.12);
        background: linear-gradient(135deg, #143f35 0%, #245548 100%);
        color: #fff9ef;
        font-weight: 700;
        font-size: 1rem;
        box-shadow: 0 12px 26px rgba(19, 60, 51, 0.16);
    }
    .import-widget-shell .stButton > button:hover {
        border-color: rgba(19, 60, 51, 0.12);
        background: linear-gradient(135deg, #17483d 0%, #2c6554 100%);
        color: #fff9ef;
    }
    .import-widget-shell .stButton > button:focus:not(:active) {
        border-color: rgba(19, 60, 51, 0.18);
        color: #fff9ef;
    }
    @media (max-width: 980px) {
        .import-grid {
            grid-template-columns: 1fr;
        }
    }
    .property-card {
        padding: 1.1rem 1.15rem 1rem 1.15rem;
        background: rgba(255, 255, 255, 0.82);
        border: 1px solid rgba(19, 60, 51, 0.10);
        border-radius: 22px;
        box-shadow: 0 18px 40px rgba(19, 60, 51, 0.10);
        min-height: 100%;
    }
    .card-row-gap {
        height: 1.05rem;
    }
    .property-card-title {
        margin: 0;
        color: #17362f;
        font-size: 1.15rem;
        line-height: 1.15;
        letter-spacing: -0.03em;
        font-weight: 700;
    }
    .property-card-kicker {
        color: #5b6b65;
        font-size: 0.9rem;
        margin-bottom: 0.65rem;
    }
    .property-card-line {
        margin-top: 0.35rem;
        color: #38524a;
        font-size: 0.95rem;
    }
    .property-card-line strong {
        color: #17362f;
    }
    .property-card-meta {
        margin-top: 0.6rem;
        color: #4d625b;
        font-size: 0.95rem;
    }
    .property-card-note {
        margin-top: 0.55rem;
        color: #4d625b;
        font-size: 0.92rem;
    }
    .property-card-cta {
        display: inline-flex;
        margin-top: 0.8rem;
        align-items: center;
        justify-content: center;
        width: 100%;
        padding: 0.72rem 0.9rem;
        border-radius: 14px;
        background: linear-gradient(135deg, #143f35 0%, #245548 100%);
        color: #fff9ef !important;
        text-decoration: none;
        font-weight: 600;
        box-shadow: 0 10px 20px rgba(19, 60, 51, 0.14);
    }
    .property-card-cta:hover {
        filter: brightness(1.04);
    }
    .chart-card {
        padding: 0.9rem 1rem 0.4rem 1rem;
        background: rgba(255, 255, 255, 0.82);
        border: 1px solid rgba(19, 60, 51, 0.10);
        border-radius: 22px;
        box-shadow: 0 18px 40px rgba(19, 60, 51, 0.10);
    }
    .table-card {
        padding: 0.2rem;
        background: rgba(255, 255, 255, 0.82);
        border: 1px solid rgba(19, 60, 51, 0.10);
        border-radius: 18px;
        box-shadow: 0 18px 40px rgba(19, 60, 51, 0.10);
        overflow: hidden;
    }
    .table-card-spaced {
        margin-bottom: 1.4rem;
    }
    .table-wrap {
        overflow-x: auto;
        scrollbar-width: thin;
        scrollbar-color: rgba(19, 60, 51, 0.45) rgba(19, 60, 51, 0.10);
    }
    .table-wrap::-webkit-scrollbar {
        height: 12px;
    }
    .table-wrap::-webkit-scrollbar-track {
        background: rgba(19, 60, 51, 0.10);
        border-radius: 999px;
    }
    .table-wrap::-webkit-scrollbar-thumb {
        background: linear-gradient(90deg, rgba(19, 60, 51, 0.70), rgba(36, 85, 72, 0.86));
        border-radius: 999px;
        border: 2px solid rgba(255, 255, 255, 0.55);
    }
    .table-wrap::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(90deg, rgba(19, 60, 51, 0.82), rgba(36, 85, 72, 0.96));
    }
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.95rem;
        color: #17362f;
        background: transparent;
    }
    .custom-table thead th {
        text-align: left;
        padding: 0.52rem 0.72rem;
        background: rgba(19, 60, 51, 0.06);
        color: #49625a;
        font-size: 0.79rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        border-bottom: 1px solid rgba(19, 60, 51, 0.10);
        white-space: nowrap;
    }
    .custom-table tbody td {
        padding: 0.28rem 0.72rem;
        border-bottom: 1px solid rgba(19, 60, 51, 0.07);
        white-space: nowrap;
        background: rgba(255, 255, 255, 0.76);
        vertical-align: top;
        line-height: 1.18;
    }
    .custom-table tbody tr:last-child td {
        border-bottom: none;
    }
    .custom-table tbody tr:hover td {
        background: rgba(19, 60, 51, 0.035);
    }
    .table-status-ok {
        color: #0f6d48;
        font-weight: 700;
    }
    .table-status-pending {
        color: #9c5b09;
        font-weight: 700;
    }
    .table-wrap-wide .custom-table tbody td,
    .table-wrap-wide .custom-table thead th {
        padding-top: 0.28rem;
        padding-bottom: 0.28rem;
    }
    .table-wrap-wide .custom-table tbody td.wrap-cell,
    .table-wrap-wide .custom-table thead th.wrap-cell {
        white-space: normal;
        min-width: 150px;
        line-height: 1.14;
    }
    .support-table-card {
        margin-top: 0.2rem;
        border-radius: 20px;
    }
    .support-table-card .table-wrap {
        max-height: 460px;
    }
    .support-table-card .custom-table thead th {
        position: sticky;
        top: 0;
        z-index: 2;
        background: rgba(241, 245, 242, 0.96);
        box-shadow: inset 0 -1px 0 rgba(19, 60, 51, 0.08);
    }
    .support-table-card .custom-table tbody tr:nth-child(even) td {
        background: rgba(247, 249, 248, 0.95);
    }
    .support-table-card .custom-table tbody tr:nth-child(odd) td {
        background: rgba(255, 255, 255, 0.88);
    }
    .support-table-card .custom-table tbody td:first-child,
    .support-table-card .custom-table thead th:first-child {
        position: sticky;
        left: 0;
        z-index: 1;
    }
    .support-table-card .custom-table thead th:first-child {
        z-index: 3;
    }
    .support-table-card .custom-table tbody td:first-child {
        box-shadow: 1px 0 0 rgba(19, 60, 51, 0.06);
    }
    .support-table-card .custom-table tbody tr:nth-child(even) td:first-child {
        background: rgba(247, 249, 248, 1);
    }
    .support-table-card .custom-table tbody tr:nth-child(odd) td:first-child {
        background: rgba(255, 255, 255, 1);
    }
</style>
"""


@st.cache_resource
def get_engine():
    return create_engine(settings.database_url, future=True)


def bool_to_label(value: object) -> str:
    if pd.isna(value):
        return "Nao informado"
    if isinstance(value, (bool, int)):
        return "Sim" if bool(value) else "Nao"

    normalized = str(value).strip().lower()
    if normalized in {"sim", "true", "1"}:
        return "Sim"
    if normalized in {"nao", "false", "0"}:
        return "Nao"
    return "Nao informado"


def format_currency(value: object) -> str:
    if pd.isna(value):
        return ""
    return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_datetime(value: object) -> str:
    if pd.isna(value):
        return ""
    timestamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(timestamp):
        return ""
    return timestamp.strftime("%d/%m/%Y %H:%M")


def is_true_flag(value: object) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, (bool, int)):
        return bool(value)
    normalized = str(value).strip().lower()
    return normalized in {"sim", "true", "1"}


def classify_score(score: object) -> tuple[str, str]:
    if pd.isna(score):
        return ("Sem score", "badge-score-low")
    value = float(score)
    if value >= 80:
        return (f"Score {value:.1f} | Forte", "badge-score-high")
    if value >= 60:
        return (f"Score {value:.1f} | Moderado", "badge-score-mid")
    return (f"Score {value:.1f} | Fraco", "badge-score-low")


def classify_pipeline_status(status: str) -> tuple[str, str]:
    if status == "Completo":
        return (status, "badge-status-ok")
    return (status or "Pendente", "badge-status-pending")


def classify_risk_level(risk_flags: str) -> tuple[str, str]:
    if pd.isna(risk_flags):
        return ("Sem riscos estruturados", "badge-risk-low")
    normalized = str(risk_flags).strip()
    if not normalized or normalized == "<NA>":
        return ("Sem riscos estruturados", "badge-risk-low")
    count = len([part for part in normalized.split("; ") if part.strip()])
    if count >= 2:
        return (f"{count} riscos estruturados", "badge-risk-high")
    return ("1 risco estruturado", "badge-risk-high")


def render_badges(items: list[tuple[str, str]]) -> None:
    html = "".join(
        f'<span class="badge {css_class}">{label}</span>'
        for label, css_class in items
        if label
    )
    if html:
        st.markdown(f'<div class="badge-row">{html}</div>', unsafe_allow_html=True)


def style_ranked_table(df: pd.DataFrame):
    score_columns = [column for column in ["Score", "Score moradia"] if column in df.columns]
    status_columns = [column for column in ["Status pipeline"] if column in df.columns]

    styler = df.style
    if score_columns:
        styler = styler.background_gradient(subset=score_columns, cmap="YlGn")
    if status_columns:
        styler = styler.map(
            lambda value: (
                "background-color: rgba(19, 140, 92, 0.12); color: #0f6d48;"
                if value == "Completo"
                else "background-color: rgba(204, 120, 24, 0.12); color: #9c5b09;"
            ),
            subset=status_columns,
        )
    return styler


def style_light_table(df: pd.DataFrame, status_columns: list[str] | None = None):
    status_columns = status_columns or []
    styler = df.style
    styler = styler.set_table_styles(
        [
            {
                "selector": "th",
                "props": [
                    ("background-color", "rgba(19, 60, 51, 0.08)"),
                    ("color", "#17362f"),
                    ("font-weight", "600"),
                    ("border-bottom", "1px solid rgba(19, 60, 51, 0.10)"),
                ],
            },
            {
                "selector": "td",
                "props": [
                    ("background-color", "rgba(255, 255, 255, 0.82)"),
                    ("color", "#17362f"),
                    ("border-bottom", "1px solid rgba(19, 60, 51, 0.06)"),
                ],
            },
            {
                "selector": "table",
                "props": [
                    ("border-collapse", "separate"),
                    ("border-spacing", "0"),
                    ("border", "1px solid rgba(19, 60, 51, 0.08)"),
                    ("border-radius", "16px"),
                    ("overflow", "hidden"),
                ],
            },
        ]
    )
    if status_columns:
        styler = styler.map(
            lambda value: (
                "background-color: rgba(19, 140, 92, 0.10); color: #0f6d48; font-weight: 600;"
                if value == "Completo"
                else "background-color: rgba(204, 120, 24, 0.10); color: #9c5b09; font-weight: 600;"
            ),
            subset=status_columns,
        )
    return styler


def format_table_value(value: object, column_name: str) -> str:
    if pd.isna(value):
        return ""
    if column_name in {"Preco", "Avaliacao", "Potencial bruto", "Ganho estimado"}:
        return format_currency(value)
    if column_name in {
        "Desconto (%)",
        "Score",
        "Score medio",
        "Score preco",
        "Score imovel",
        "Score localizacao",
        "Score liquidez",
        "Score risco",
        "Score moradia",
    }:
        return f"{float(value):.2f}"
    if isinstance(value, pd.Timestamp):
        return format_datetime(value)
    return str(value)


def render_custom_table(
    df: pd.DataFrame,
    status_columns: list[str] | None = None,
    wrap_columns: list[str] | None = None,
    wide: bool = False,
    link_columns: dict[str, str] | None = None,
    hidden_columns: list[str] | None = None,
    extra_class: str = "",
) -> None:
    status_columns = status_columns or []
    wrap_columns = wrap_columns or []
    link_columns = link_columns or {}
    hidden_columns = hidden_columns or []
    visible_columns = [column for column in df.columns if column not in hidden_columns]
    headers = "".join(
        f'<th class="{"wrap-cell" if column in wrap_columns else ""}">{html.escape(str(column))}</th>'
        for column in visible_columns
    )

    body_rows: list[str] = []
    for _, row in df.iterrows():
        cells: list[str] = []
        for column in visible_columns:
            value = format_table_value(row[column], str(column))
            css_class = ""
            if column in status_columns:
                css_class = "table-status-ok" if value == "Completo" else "table-status-pending"
            if column in wrap_columns:
                css_class = f"{css_class} wrap-cell".strip()
            if column in link_columns:
                url_column = link_columns[column]
                url_value = row.get(url_column, "")
                if pd.notna(url_value) and str(url_value).strip():
                    linked_value = (
                        f'<a href="{html.escape(str(url_value))}" target="_blank" '
                        f'style="color:#0f6d48;font-weight:700;text-decoration:none;">{html.escape(value)}</a>'
                    )
                    cells.append(f'<td class="{css_class}">{linked_value}</td>')
                    continue
            cells.append(f'<td class="{css_class}">{html.escape(value)}</td>')
        body_rows.append(f"<tr>{''.join(cells)}</tr>")

    st.markdown(
        f"""
        <div class="table-card {extra_class}">
            <div class="table-wrap {'table-wrap-wide' if wide else ''}">
                <table class="custom-table">
                    <thead><tr>{headers}</tr></thead>
                    <tbody>{''.join(body_rows)}</tbody>
                </table>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_chart(chart: alt.Chart) -> alt.Chart:
    return (
        chart.configure_view(stroke=None, fill="transparent")
        .configure_axis(
            labelColor="#38524a",
            titleColor="#17362f",
            gridColor="rgba(19, 60, 51, 0.10)",
            domainColor="rgba(19, 60, 51, 0.16)",
            tickColor="rgba(19, 60, 51, 0.16)",
        )
        .configure_title(color="#17362f", fontSize=18, anchor="start")
        .configure_legend(
            titleColor="#17362f",
            labelColor="#38524a",
            orient="bottom",
        )
        .properties(background="transparent")
    )


def build_risk_flag_summary(row: pd.Series) -> str:
    labels = [label for column, label in RISK_FLAG_LABELS.items() if is_true_flag(row.get(column))]
    return "; ".join(labels)


def split_score_reason(reason: object) -> dict[str, str]:
    if pd.isna(reason):
        return {
            "score_reason_preco": "",
            "score_reason_imovel": "",
            "score_reason_localizacao": "",
            "score_reason_liquidez": "",
            "score_reason_risco": "",
        }

    parts = [part.strip() for part in str(reason).split("|") if part.strip()]
    buckets = {
        "score_reason_preco": "",
        "score_reason_imovel": "",
        "score_reason_localizacao": "",
        "score_reason_liquidez": "",
        "score_reason_risco": "",
    }
    for part in parts:
        lowered = part.lower()
        if lowered.startswith("preco "):
            buckets["score_reason_preco"] = part
        elif lowered.startswith("imovel "):
            buckets["score_reason_imovel"] = part
        elif lowered.startswith("localizacao "):
            buckets["score_reason_localizacao"] = part
        elif lowered.startswith("liquidez"):
            buckets["score_reason_liquidez"] = part
        elif lowered.startswith("risco "):
            buckets["score_reason_risco"] = part
    return buckets


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    query = """
    SELECT
        property_code,
        uf,
        city,
        neighborhood,
        address,
        price,
        appraisal_value,
        discount_pct,
        financing_text,
        description,
        detail_url,
        edital_url,
        matricula_url,
        edital_sale_mode,
        edital_sale_date,
        edital_payment_details,
        edital_risk_notes,
        edital_has_occupied_risk,
        edital_has_no_visit_risk,
        edital_buyer_pays_condo,
        edital_buyer_pays_iptu,
        edital_has_judicial_risk,
        accepts_fgts,
        accepts_financing,
        expense_rules,
        payment_rules,
        property_type,
        private_area_m2,
        total_area_m2,
        land_area_m2,
        bedrooms,
        bathrooms,
        parking_spots,
        opportunity_score,
        score_reason,
        score_preco,
        score_imovel,
        score_localizacao,
        score_liquidez_residencial,
        score_risco,
        score_moradia,
        score_moradia_reason,
        imported_at,
        detail_enriched_at,
        edital_enriched_at,
        scored_at,
        scoring_version,
        created_at,
        updated_at,
        last_alerted_at
    FROM properties
    """
    with get_engine().connect() as conn:
        df = pd.read_sql(query, conn)

    numeric_cols = [
        "price",
        "appraisal_value",
        "discount_pct",
        "private_area_m2",
        "total_area_m2",
        "land_area_m2",
        "bedrooms",
        "bathrooms",
        "parking_spots",
        "opportunity_score",
        "score_preco",
        "score_imovel",
        "score_localizacao",
        "score_liquidez_residencial",
        "score_risco",
        "score_moradia",
    ]
    text_cols = [
        "property_type",
        "city",
        "uf",
        "neighborhood",
        "address",
        "description",
        "score_reason",
        "score_moradia_reason",
        "detail_url",
        "edital_url",
        "edital_sale_mode",
        "edital_sale_date",
        "edital_payment_details",
        "edital_risk_notes",
        "scoring_version",
    ]
    bool_cols = [
        "accepts_fgts",
        "accepts_financing",
        *RISK_FLAG_LABELS.keys(),
    ]
    datetime_cols = [
        "imported_at",
        "detail_enriched_at",
        "edital_enriched_at",
        "scored_at",
        "created_at",
        "updated_at",
        "last_alerted_at",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = pd.Series([None] * len(df))

    for col in text_cols:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str).str.strip()

    for col in bool_cols:
        if col not in df.columns:
            df[col] = pd.Series([None] * len(df), dtype="boolean")
        df[col] = df[col].astype("boolean")

    for col in datetime_cols:
        if col not in df.columns:
            df[col] = pd.NaT
        df[col] = pd.to_datetime(df[col], errors="coerce")

    df["opportunity_score_display"] = df["score_moradia"].where(
        df["score_moradia"].notna(),
        df["opportunity_score"],
    )
    df["estimated_gain"] = df["appraisal_value"] - df["price"]
    df["city_label"] = df["city"]
    df.loc[df["uf"] != "", "city_label"] = df["city"] + "/" + df["uf"]

    df["neighborhood_label"] = df["neighborhood"]
    has_city = df["city"] != ""
    has_uf = df["uf"] != ""
    df.loc[has_city & has_uf, "neighborhood_label"] = (
        df["neighborhood"] + " - " + df["city"] + "/" + df["uf"]
    )
    df.loc[(df["neighborhood"] == "") & has_city & has_uf, "neighborhood_label"] = df["city"] + "/" + df["uf"]

    df["description_short"] = df["description"]
    df.loc[df["description_short"].str.len() > 140, "description_short"] = (
        df["description_short"].str.slice(0, 140) + "..."
    )

    df["accepts_fgts_label"] = df["accepts_fgts"].apply(bool_to_label)
    df["accepts_financing_label"] = df["accepts_financing"].apply(bool_to_label)
    for column, label in RISK_FLAG_LABELS.items():
        df[f"{column}_label"] = df[column].apply(bool_to_label)
    df["edital_risk_flags"] = df.apply(build_risk_flag_summary, axis=1)
    score_reason_source = df["score_moradia_reason"].where(
        df["score_moradia_reason"].str.strip() != "",
        df["score_reason"],
    )
    score_reason_parts = [split_score_reason(value) for value in score_reason_source.tolist()]
    score_reason_df = pd.DataFrame(score_reason_parts)
    for column in score_reason_df.columns:
        df[column] = score_reason_df[column]
    df["pipeline_status"] = "Completo"
    df.loc[df["detail_enriched_at"].isna(), "pipeline_status"] = "Pendente detalhe"
    df.loc[df["edital_enriched_at"].isna(), "pipeline_status"] = "Pendente edital"
    df.loc[df["scored_at"].isna(), "pipeline_status"] = "Pendente score"
    df["score_band"] = df["opportunity_score_display"].apply(lambda value: classify_score(value)[0])
    df["risk_level_label"] = df["edital_risk_flags"].apply(lambda value: classify_risk_level(value)[0])
    return df


def import_uploaded_csvs(uploaded_files: list[object]) -> int:
    pipeline = CaixaScannerPipeline()
    temp_paths: list[str] = []

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            for uploaded_file in uploaded_files:
                file_path = Path(temp_dir) / uploaded_file.name
                file_path.write_bytes(uploaded_file.getvalue())
                temp_paths.append(str(file_path))

            return pipeline.import_csv_batch(temp_paths)
    finally:
        load_data.clear()


def render_csv_import_panel() -> None:
    st.markdown(
        """
        <div class="import-shell">
            <div class="import-grid">
                <div>
                    <div class="import-kicker">Onboarding de dados</div>
                    <h2 class="import-title">Traga a base da Caixa para dentro do dashboard</h2>
                    <div class="import-copy">
                        Envie um ou mais arquivos CSV e alimente a visao online sem depender de terminal,
                        script local ou acesso ao servidor.
                    </div>
                    <div class="import-code">Lista_imoveis_XX.csv</div>
                </div>
                <div class="import-steps">
                    <div class="import-step">
                        <div class="import-step-label">Passo 1</div>
                        <div class="import-step-value">Selecione arquivos de uma ou mais UFs.</div>
                    </div>
                    <div class="import-step">
                        <div class="import-step-label">Passo 2</div>
                        <div class="import-step-value">Clique em importar para calcular score e atualizar a base.</div>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="import-widget-shell">', unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        "Selecione os CSVs da Caixa",
        type=["csv"],
        accept_multiple_files=True,
        help="Voce pode enviar varios arquivos, como MG e SP, na mesma importacao.",
    )

    if st.button("Importar arquivos e atualizar dashboard", type="primary", use_container_width=True):
        if not uploaded_files:
            st.warning("Selecione ao menos um arquivo CSV para importar.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        try:
            saved = import_uploaded_csvs(uploaded_files)
        except Exception as exc:
            st.error(f"Falha ao importar os CSVs enviados: {exc}")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        st.success(f"{saved} imoveis importados com sucesso.")
        st.markdown("</div>", unsafe_allow_html=True)
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_empty_state() -> None:
    st.markdown(
        """
        <div class="empty-state">
            <h2>Banco sem dados visiveis</h2>
            <p>Nenhum dado foi encontrado na base atual do dashboard.</p>
            <p>Para popular a base, rode <code>python -m caixa_scanner.main scan --ufs SP MG</code> ou use o importador de CSV logo abaixo.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_csv_import_panel()


def render_dashboard_header(df: pd.DataFrame) -> None:
    total_properties = len(df)
    ready_count = int((df["pipeline_status"] == "Completo").sum()) if not df.empty else 0
    high_score_count = int((df["opportunity_score_display"].fillna(0) >= 80).sum()) if not df.empty else 0
    latest_score = format_datetime(df["scored_at"].max()) if "scored_at" in df.columns else ""

    st.markdown(
        f"""
        <div class="dashboard-hero">
            <h1>Caixa Scanner Dashboard</h1>
            <p>Leitura rapida do funil de oportunidades, riscos estruturados e saude da pipeline.</p>
            <div class="hero-meta">
                <span class="hero-chip">{total_properties} imoveis na visao atual</span>
                <span class="hero-chip">{ready_count} com pipeline completa</span>
                <span class="hero-chip">{high_score_count} com score >= 80</span>
                <span class="hero-chip">Ultimo score: {latest_score or 'sem registro'}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_filters(df: pd.DataFrame) -> pd.DataFrame:
    filtered = df.copy()
    st.sidebar.header("Filtros")

    if "uf" in filtered.columns:
        options = sorted([x for x in filtered["uf"].dropna().astype(str).unique().tolist() if x])
        selected = st.sidebar.multiselect("UF", options)
        if selected:
            filtered = filtered[filtered["uf"].isin(selected)]

    if "city" in filtered.columns:
        options = sorted([x for x in filtered["city"].dropna().astype(str).unique().tolist() if x])
        selected = st.sidebar.multiselect("Cidade", options)
        if selected:
            filtered = filtered[filtered["city"].isin(selected)]

    if "neighborhood" in filtered.columns:
        options = sorted([x for x in filtered["neighborhood"].dropna().astype(str).unique().tolist() if x])
        selected = st.sidebar.multiselect("Bairro", options)
        if selected:
            filtered = filtered[filtered["neighborhood"].isin(selected)]

    if "property_type" in filtered.columns:
        options = sorted([x for x in filtered["property_type"].dropna().astype(str).unique().tolist() if x])
        selected = st.sidebar.multiselect("Tipo do imovel", options)
        if selected:
            filtered = filtered[filtered["property_type"].isin(selected)]

    if "edital_sale_mode" in filtered.columns:
        options = sorted([x for x in filtered["edital_sale_mode"].dropna().astype(str).unique().tolist() if x])
        selected = st.sidebar.multiselect("Modalidade do edital", options)
        if selected:
            filtered = filtered[filtered["edital_sale_mode"].isin(selected)]

    if "scoring_version" in filtered.columns:
        options = sorted([x for x in filtered["scoring_version"].dropna().astype(str).unique().tolist() if x])
        selected = st.sidebar.multiselect("Versao do score", options)
        if selected:
            filtered = filtered[filtered["scoring_version"].isin(selected)]

    if "pipeline_status" in filtered.columns:
        status_filter = st.sidebar.selectbox(
            "Status da pipeline",
            ["Todos", "Completo", "Pendente detalhe", "Pendente edital", "Pendente score"],
        )
        if status_filter != "Todos":
            filtered = filtered[filtered["pipeline_status"] == status_filter]

    for field_name, label in [
        ("bedrooms", "Quartos"),
        ("parking_spots", "Vagas"),
    ]:
        if field_name in filtered.columns:
            options = sorted([int(x) for x in filtered[field_name].dropna().unique().tolist() if pd.notna(x)])
            selected = st.sidebar.multiselect(label, options)
            if selected:
                filtered = filtered[filtered[field_name].isin(selected)]

    if "private_area_m2" in filtered.columns and filtered["private_area_m2"].dropna().size > 0:
        min_area = float(filtered["private_area_m2"].dropna().min())
        max_area = float(filtered["private_area_m2"].dropna().max())
        area_range = (
            (min_area, max_area)
            if min_area == max_area
            else st.sidebar.slider("Area privativa (m2)", min_value=min_area, max_value=max_area, value=(min_area, max_area))
        )
        filtered = filtered[
            (filtered["private_area_m2"].fillna(0) >= area_range[0])
            & (filtered["private_area_m2"].fillna(0) <= area_range[1])
        ]

    if "price" in filtered.columns and filtered["price"].dropna().size > 0:
        min_price = float(filtered["price"].dropna().min())
        max_price = float(filtered["price"].dropna().max())
        price_range = (
            (min_price, max_price)
            if min_price == max_price
            else st.sidebar.slider("Preco (R$)", min_value=min_price, max_value=max_price, value=(min_price, max_price))
        )
        filtered = filtered[
            (filtered["price"].fillna(0) >= price_range[0])
            & (filtered["price"].fillna(0) <= price_range[1])
        ]

    if "discount_pct" in filtered.columns and filtered["discount_pct"].dropna().size > 0:
        min_discount = float(filtered["discount_pct"].dropna().min())
        max_discount = float(filtered["discount_pct"].dropna().max())
        discount_range = (
            (min_discount, max_discount)
            if min_discount == max_discount
            else st.sidebar.slider(
                "Desconto (%)",
                min_value=min_discount,
                max_value=max_discount,
                value=(min_discount, max_discount),
            )
        )
        filtered = filtered[
            (filtered["discount_pct"].fillna(0) >= discount_range[0])
            & (filtered["discount_pct"].fillna(0) <= discount_range[1])
        ]

    if "opportunity_score_display" in filtered.columns and filtered["opportunity_score_display"].dropna().size > 0:
        min_score = float(filtered["opportunity_score_display"].dropna().min())
        max_score = float(filtered["opportunity_score_display"].dropna().max())
        score_range = (
            (min_score, max_score)
            if min_score == max_score
            else st.sidebar.slider(
                "Score",
                min_value=min_score,
                max_value=max_score,
                value=(min_score, max_score),
            )
        )
        filtered = filtered[
            (filtered["opportunity_score_display"].fillna(0) >= score_range[0])
            & (filtered["opportunity_score_display"].fillna(0) <= score_range[1])
        ]

    financing_filter = st.sidebar.selectbox("Financiamento", ["Todos", "Sim", "Nao", "Nao informado"])
    if financing_filter != "Todos":
        filtered = filtered[filtered["accepts_financing_label"] == financing_filter]

    fgts_filter = st.sidebar.selectbox("FGTS", ["Todos", "Sim", "Nao", "Nao informado"])
    if fgts_filter != "Todos":
        filtered = filtered[filtered["accepts_fgts_label"] == fgts_filter]

    selected_risk_flags = st.sidebar.multiselect("Riscos estruturados do edital", list(RISK_FLAG_LABELS.values()))
    if selected_risk_flags:
        risk_columns = [column for column, label in RISK_FLAG_LABELS.items() if label in selected_risk_flags]
        mask = filtered[risk_columns].fillna(False).any(axis=1)
        filtered = filtered[mask]

    return filtered


def render_kpis(df: pd.DataFrame) -> None:
    col1, col2, col3, col4 = st.columns(4)
    score_mean = round(df["opportunity_score_display"].dropna().mean(), 2) if not df.empty else 0.0
    discount_mean = round(df["discount_pct"].dropna().mean(), 2) if not df.empty else 0.0
    gain_mean = round(df["estimated_gain"].dropna().mean(), 2) if not df.empty else 0.0
    pending_share = round((df["pipeline_status"] != "Completo").mean() * 100, 1) if not df.empty else 0.0

    cards = [
        ("Score medio", f"{score_mean:.2f}", "Media da visao filtrada"),
        ("Desconto medio", f"{discount_mean:.2f}%", "Desconto nominal medio"),
        ("Ganho bruto medio", f"{gain_mean:,.2f}", "Potencial medio em reais"),
        ("Pendentes na pipeline", f"{pending_share:.1f}%", "Imoveis ainda incompletos"),
    ]
    for column, (label, value, caption) in zip((col1, col2, col3, col4), cards, strict=False):
        with column:
            st.markdown(
                f"""
                <div class="stat-card">
                    <div class="stat-label">{label}</div>
                    <div class="stat-value">{value}</div>
                    <div class="stat-caption">{caption}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_pipeline_health(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">Saude Da Pipeline</div>', unsafe_allow_html=True)
    left, right = st.columns([1.2, 1.8])

    with left:
        status_summary = (
            df.groupby("pipeline_status", as_index=False)
            .agg(
                quantidade=("property_code", "count"),
                score_medio=("opportunity_score_display", "mean"),
            )
            .sort_values("quantidade", ascending=False)
        )
        status_summary["score_medio"] = status_summary["score_medio"].round(2)
        summary_cols = st.columns(max(len(status_summary), 1), gap="large")
        for column, (_, row) in zip(summary_cols, status_summary.iterrows(), strict=False):
            with column:
                st.markdown(
                    f"""
                    <div class="stat-card">
                        <div class="stat-label">{html.escape(str(row["pipeline_status"]))}</div>
                        <div class="stat-value">{int(row["quantidade"])}</div>
                        <div class="stat-caption">Score medio: {float(row["score_medio"]):.2f}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with right:
        health_cols = st.columns(3, gap="large")
        health_metrics = [
            (
                "Sem detalhe",
                int(df["detail_enriched_at"].isna().sum()),
                "Precisam de enriquecimento de pagina",
            ),
            (
                "Sem edital",
                int(df["edital_enriched_at"].isna().sum()),
                "Ainda nao passaram no parser de edital",
            ),
            (
                "Sem score",
                int(df["scored_at"].isna().sum()),
                "Pendentes de pontuacao",
            ),
        ]
        for column, (label, value, caption) in zip(health_cols, health_metrics, strict=False):
            with column:
                st.markdown(
                    f"""
                    <div class="stat-card">
                        <div class="stat-label">{label}</div>
                        <div class="stat-value">{value}</div>
                        <div class="stat-caption">{caption}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def render_market_spotlight(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">Radar Rapido</div>', unsafe_allow_html=True)
    spotlight_cols = st.columns(3)

    top_city = ""
    if not df.empty and "city_label" in df.columns:
        counts = df["city_label"].value_counts()
        top_city = counts.index[0] if not counts.empty else ""

    top_risk = ""
    if not df.empty and "edital_risk_flags" in df.columns:
        flagged = df[df["edital_risk_flags"] != ""]
        if not flagged.empty:
            risk_counts = flagged["edital_risk_flags"].str.split("; ").explode().value_counts()
            top_risk = risk_counts.index[0] if not risk_counts.empty else ""

    best_item = ""
    if not df.empty:
        ranked = df.sort_values("opportunity_score_display", ascending=False, na_position="last").head(1)
        if not ranked.empty:
            row = ranked.iloc[0]
            best_item = f"{row.get('property_code', '')} | {row.get('city_label', '')}"

    spotlight_data = [
        ("Cidade dominante", top_city or "Sem destaque", "Maior concentracao na visao atual"),
        ("Risco mais frequente", top_risk or "Sem riscos marcados", "Sinal mais recorrente no edital"),
        ("Melhor oportunidade", best_item or "Sem dados", "Topo do ranking filtrado"),
    ]
    for column, (label, value, caption) in zip(spotlight_cols, spotlight_data, strict=False):
        with column:
            st.markdown(
                f"""
                <div class="stat-card">
                    <div class="stat-label">{label}</div>
                    <div class="stat-value" style="font-size:1.2rem">{value}</div>
                    <div class="stat-caption">{caption}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_state_ranking(df: pd.DataFrame) -> None:
    st.subheader("Melhores oportunidades por estado")
    ranking = (
        df.sort_values(["uf", "opportunity_score_display"], ascending=[True, False])
        .groupby("uf", as_index=False)
        .first()[
            [
                "property_code",
                "uf",
                "city_label",
                "neighborhood_label",
                "property_type",
                "private_area_m2",
                "bedrooms",
                "parking_spots",
                "price",
                "appraisal_value",
                "discount_pct",
                "estimated_gain",
                "opportunity_score_display",
                "accepts_financing_label",
                "accepts_fgts_label",
                "edital_sale_mode",
                "edital_risk_flags",
                "pipeline_status",
                "scoring_version",
                "detail_url",
            ]
        ]
        .rename(
            columns={
                "property_code": "Codigo",
                "uf": "UF",
                "city_label": "Cidade",
                "neighborhood_label": "Bairro",
                "property_type": "Tipo",
                "private_area_m2": "Area privativa (m2)",
                "bedrooms": "Quartos",
                "parking_spots": "Vagas",
                "price": "Preco",
                "appraisal_value": "Avaliacao",
                "discount_pct": "Desconto (%)",
                "estimated_gain": "Ganho estimado",
                "opportunity_score_display": "Score",
                "accepts_financing_label": "Financiamento",
                "accepts_fgts_label": "FGTS",
                "edital_sale_mode": "Modalidade edital",
                "edital_risk_flags": "Riscos estruturados",
                "pipeline_status": "Status pipeline",
                "scoring_version": "Versao score",
                "detail_url": "Detalhe",
            }
        )
    )
    render_custom_table(
        ranking,
        status_columns=["Status pipeline"],
        link_columns={"Codigo": "Detalhe"},
        hidden_columns=["Detalhe"],
        extra_class="table-card-spaced",
    )


def render_charts(df: pd.DataFrame) -> None:
    left, right = st.columns(2)

    with left:
        st.subheader("Top 10 estados por score medio")
        state_scores = (
            df.groupby("uf", as_index=False)
            .agg(score_medio=("opportunity_score_display", "mean"), quantidade=("property_code", "count"))
            .sort_values(["score_medio", "quantidade"], ascending=[False, False])
            .head(10)
            .set_index("uf")
        )
        state_scores_chart = (
            alt.Chart(state_scores.reset_index())
            .mark_bar(color="#245548", cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
            .encode(
                x=alt.X("uf:N", title="UF", sort="-y", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("score_medio:Q", title="Score medio"),
                tooltip=[
                    alt.Tooltip("uf:N", title="UF"),
                    alt.Tooltip("score_medio:Q", title="Score medio", format=".2f"),
                    alt.Tooltip("quantidade:Q", title="Quantidade"),
                ],
            )
            .properties(height=280)
        )
        with st.container():
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.altair_chart(build_chart(state_scores_chart), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.subheader("Top 10 estados por quantidade")
        state_volume = (
            df.groupby("uf", as_index=False)
            .size()
            .rename(columns={"size": "quantidade"})
            .sort_values("quantidade", ascending=False)
            .head(10)
            .set_index("uf")
        )
        state_volume_chart = (
            alt.Chart(state_volume.reset_index())
            .mark_bar(color="#d8b15a", cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
            .encode(
                x=alt.X("uf:N", title="UF", sort="-y", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("quantidade:Q", title="Quantidade"),
                tooltip=[
                    alt.Tooltip("uf:N", title="UF"),
                    alt.Tooltip("quantidade:Q", title="Quantidade"),
                ],
            )
            .properties(height=280)
        )
        with st.container():
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.altair_chart(build_chart(state_volume_chart), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    st.subheader("Score x desconto")
    scatter = df[["discount_pct", "opportunity_score_display", "uf"]].dropna().copy()
    if scatter.empty:
        st.caption("Sem dados suficientes para o grafico de dispersao.")
    else:
        palette = ["#245548", "#d8b15a", "#cf6a5d", "#6aa6d8", "#7d8f69", "#8f6bb3"]
        scatter_chart = (
            alt.Chart(scatter)
            .mark_circle(size=62, opacity=0.72)
            .encode(
                x=alt.X("discount_pct:Q", title="Desconto (%)"),
                y=alt.Y("opportunity_score_display:Q", title="Score"),
                color=alt.Color("uf:N", title="UF", scale=alt.Scale(range=palette)),
                tooltip=[
                    alt.Tooltip("uf:N", title="UF"),
                    alt.Tooltip("discount_pct:Q", title="Desconto (%)", format=".2f"),
                    alt.Tooltip("opportunity_score_display:Q", title="Score", format=".2f"),
                ],
            )
            .properties(height=320)
        )
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.altair_chart(build_chart(scatter_chart), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)


def render_top_table(df: pd.DataFrame) -> None:
    st.markdown(
        """
        <div class="section-shell">
            <div class="section-header">
                <div class="section-eyebrow">Ranking principal</div>
                <h2>Ranking geral filtrado</h2>
                <div class="section-copy">Visao consolidada das melhores oportunidades da selecao atual, com prioridade para score e desconto.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="control-shell">', unsafe_allow_html=True)
    limit = st.slider("Quantidade de imoveis no ranking", min_value=10, max_value=200, value=50, step=10)
    st.markdown("</div>", unsafe_allow_html=True)
    top_df = (
        df.sort_values(["opportunity_score_display", "discount_pct"], ascending=[False, False])
        .head(limit)
        .loc[
            :,
            [
                "property_code",
                "uf",
                "city_label",
                "neighborhood_label",
                "price",
                "appraisal_value",
                "estimated_gain",
                "discount_pct",
                "private_area_m2",
                "bedrooms",
                "parking_spots",
                "accepts_financing_label",
                "accepts_fgts_label",
                "opportunity_score_display",
                "score_preco",
                "score_imovel",
                "score_localizacao",
                "score_liquidez_residencial",
                "score_risco",
                "score_reason_preco",
                "score_reason_imovel",
                "score_reason_localizacao",
                "score_reason_liquidez",
                "score_reason_risco",
                "edital_sale_mode",
                "edital_sale_date",
                "edital_risk_notes",
                "edital_risk_flags",
                "pipeline_status",
                "scoring_version",
                "scored_at",
                "detail_url",
                "edital_url",
            ]
        ]
        .rename(
            columns={
                "property_code": "Codigo",
                "uf": "UF",
                "city_label": "Cidade",
                "neighborhood_label": "Bairro",
                "price": "Preco",
                "appraisal_value": "Avaliacao",
                "estimated_gain": "Potencial bruto",
                "discount_pct": "Desconto (%)",
                "private_area_m2": "Area (m2)",
                "bedrooms": "Quartos",
                "parking_spots": "Vagas",
                "accepts_financing_label": "Financiamento",
                "accepts_fgts_label": "FGTS",
                "opportunity_score_display": "Score",
                "score_preco": "Score preco",
                "score_imovel": "Score imovel",
                "score_localizacao": "Score localizacao",
                "score_liquidez_residencial": "Score liquidez",
                "score_risco": "Score risco",
                "score_reason_preco": "Motivo preco",
                "score_reason_imovel": "Motivo imovel",
                "score_reason_localizacao": "Motivo localizacao",
                "score_reason_liquidez": "Motivo liquidez",
                "score_reason_risco": "Motivo risco",
                "edital_sale_mode": "Modalidade edital",
                "edital_sale_date": "Data edital",
                "edital_risk_notes": "Riscos em texto",
                "edital_risk_flags": "Riscos estruturados",
                "pipeline_status": "Status pipeline",
                "scoring_version": "Versao score",
                "scored_at": "Score em",
                "detail_url": "Detalhe",
                "edital_url": "Edital",
            }
        )
    )
    render_custom_table(
        top_df,
        wrap_columns=[
            "Bairro",
            "Motivo preco",
            "Motivo imovel",
            "Motivo localizacao",
            "Motivo liquidez",
            "Motivo risco",
        ],
        wide=True,
        link_columns={"Codigo": "Detalhe"},
        hidden_columns=["Detalhe"],
    )


def render_download(df: pd.DataFrame) -> None:
    ranked = df.sort_values("opportunity_score_display", ascending=False, na_position="last")
    csv_bytes = ranked.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Baixar CSV filtrado",
        data=csv_bytes,
        file_name="caixa_oportunidades_filtradas.csv",
        mime="text/csv",
    )


def render_export_workspace(df: pd.DataFrame) -> None:
    total_items = len(df)
    unique_cities = df["city_label"].nunique() if "city_label" in df.columns else 0
    avg_score = round(df["opportunity_score_display"].dropna().mean(), 2) if not df.empty else 0.0

    st.markdown(
        f"""
        <div class="section-shell">
            <div class="section-header">
                <div class="section-eyebrow">Workspace de exportacao</div>
                <h2>Base filtrada</h2>
                <div class="section-copy">Revise a amostra final e exporte a selecao atual com os principais campos ja preparados.</div>
            </div>
        </div>
        <div class="export-shell">
            <div class="export-grid">
                <div class="export-card">
                    <div class="export-label">Linhas prontas</div>
                    <div class="export-value">{total_items}</div>
                    <div class="export-copy">Quantidade de imoveis na base filtrada atual.</div>
                </div>
                <div class="export-card">
                    <div class="export-label">Cidades unicas</div>
                    <div class="export-value">{unique_cities}</div>
                    <div class="export-copy">Cobertura geografica da exportacao corrente.</div>
                </div>
                <div class="export-card">
                    <div class="export-label">Score medio</div>
                    <div class="export-value">{avg_score:.2f}</div>
                    <div class="export-copy">Media de score dos registros exportados.</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    export_columns = [
        "property_code",
        "uf",
        "city",
        "neighborhood",
        "address",
        "price",
        "appraisal_value",
        "discount_pct",
        "property_type",
        "private_area_m2",
        "bedrooms",
        "parking_spots",
        "opportunity_score_display",
        "pipeline_status",
        "detail_url",
    ]
    export_df = df[[column for column in export_columns if column in df.columns]].rename(
        columns={
            "property_code": "Codigo",
            "uf": "UF",
            "city": "Cidade",
            "neighborhood": "Bairro",
            "address": "Endereco",
            "price": "Preco",
            "appraisal_value": "Avaliacao",
            "discount_pct": "Desconto (%)",
            "property_type": "Tipo",
            "private_area_m2": "Area privativa (m2)",
            "bedrooms": "Quartos",
            "parking_spots": "Vagas",
            "opportunity_score_display": "Score",
            "pipeline_status": "Status pipeline",
            "detail_url": "Detalhe",
        }
    )
    render_custom_table(
        export_df.head(100),
        status_columns=["Status pipeline"],
        wrap_columns=["Endereco", "Bairro"],
        wide=True,
        link_columns={"Codigo": "Detalhe"},
        hidden_columns=["Detalhe"],
    )
    render_download(df)


def render_property_cards(df: pd.DataFrame, limit: int = 20) -> None:
    st.subheader("Melhores oportunidades em cards")
    if df.empty:
        st.info("Nenhum imovel encontrado com os filtros atuais.")
        return

    cards_df = df.head(limit).copy()
    for i in range(0, len(cards_df), 2):
        cols = st.columns(2, gap="large")
        for j in range(2):
            idx = i + j
            if idx >= len(cards_df):
                continue

            row = cards_df.iloc[idx]
            with cols[j]:
                with st.container():
                    title = str(row.get("property_type", "") or "").title()
                    info_parts: list[str] = []
                    if pd.notna(row.get("private_area_m2")):
                        info_parts.append(f"{float(row['private_area_m2']):.2f} m2")
                    if pd.notna(row.get("bedrooms")):
                        info_parts.append(f"{int(row['bedrooms'])} quartos")
                    if pd.notna(row.get("parking_spots")):
                        info_parts.append(f"{int(row['parking_spots'])} vagas")

                    finance_parts: list[str] = []
                    if pd.notna(row.get("price")):
                        finance_parts.append(f"Preco: {format_currency(row['price'])}")
                    if pd.notna(row.get("discount_pct")):
                        finance_parts.append(f"Desconto: {float(row['discount_pct']):.2f}%")
                    if pd.notna(row.get("opportunity_score_display")):
                        finance_parts.append(f"Score: {float(row['opportunity_score_display']):.2f}")

                    note_text = ""
                    if row.get("edital_risk_flags"):
                        note_text = f"Riscos estruturados: {row['edital_risk_flags']}"
                    elif row.get("edital_risk_notes"):
                        note_text = f"Riscos: {row['edital_risk_notes']}"
                    elif row.get("score_moradia_reason"):
                        note_text = str(row["score_moradia_reason"])
                    elif row.get("score_reason"):
                        note_text = str(row["score_reason"])

                    detail_url = str(row.get("detail_url", "") or "")
                    st.markdown(
                        f"""
                        <div class="property-card">
                            <div class="property-card-kicker">{html.escape(" | ".join(info_parts))}</div>
                            <div class="property-card-title">{html.escape(title)} | {html.escape(str(row.get("city_label", "")))}</div>
                            <div class="property-card-line"><strong>Bairro:</strong> {html.escape(str(row.get("neighborhood_label", "")))}</div>
                            <div class="property-card-line"><strong>Endereco:</strong> {html.escape(str(row.get("address", "")))}</div>
                            <div class="property-card-line"><strong>Codigo:</strong> {html.escape(str(row.get("property_code", "")))}</div>
                            <div class="property-card-meta">{html.escape(" | ".join(finance_parts))}</div>
                            <div class="property-card-note">Versao do score: {html.escape(str(row.get("scoring_version", "") or "sem versao"))}</div>
                            <div class="property-card-note">{html.escape(note_text)}</div>
                            {"<a class='property-card-cta' href='" + html.escape(detail_url) + "' target='_blank'>Abrir na Caixa</a>" if detail_url else ""}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    score_badge = classify_score(row.get("opportunity_score_display"))
                    status_badge = classify_pipeline_status(str(row.get("pipeline_status", "")))
                    risk_badge = classify_risk_level(str(row.get("edital_risk_flags", "")))
                    render_badges([score_badge, status_badge, risk_badge])

                    if row.get("edital_sale_mode"):
                        st.caption(f"Edital: {row['edital_sale_mode']} | {row.get('edital_sale_date') or 'sem data'}")
        if i + 2 < len(cards_df):
            st.markdown('<div class="card-row-gap"></div>', unsafe_allow_html=True)


def render_quick_lookup(df: pd.DataFrame) -> None:
    st.markdown(
        """
        <div class="section-shell">
            <div class="section-header">
                <div class="section-eyebrow">Explorador</div>
                <h2>Consulta rapida de imovel</h2>
                <div class="section-copy">Selecione um codigo para abrir um painel resumido do ativo, dos riscos e do status da pipeline.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="lookup-shell">', unsafe_allow_html=True)
    property_codes = df["property_code"].dropna().astype(str).unique().tolist()
    selected_code = st.selectbox("Selecione o codigo do imovel", property_codes)
    if not selected_code:
        st.markdown("</div>", unsafe_allow_html=True)
        return

    selected_row = df[df["property_code"].astype(str) == str(selected_code)].head(1)
    if selected_row.empty:
        st.markdown("</div>", unsafe_allow_html=True)
        return

    row = selected_row.iloc[0]
    st.markdown(
        f"""
        <div class="lookup-grid">
            <div class="lookup-card">
                <div class="lookup-kicker">Identificacao</div>
                <div class="lookup-title">{html.escape(str(row.get('property_type', '') or '').title())} | {html.escape(str(row.get('city_label', '')))}</div>
                <div class="lookup-meta"><strong>Codigo:</strong> {html.escape(str(row.get('property_code', '')))}</div>
                <div class="lookup-meta"><strong>Bairro:</strong> {html.escape(str(row.get('neighborhood_label', '')))}</div>
                <div class="lookup-meta"><strong>Endereco:</strong> {html.escape(str(row.get('address', '')))}</div>
            </div>
            <div class="lookup-card">
                <div class="lookup-kicker">Financeiro e produto</div>
                <div class="lookup-meta"><strong>Preco:</strong> {html.escape(format_currency(row.get('price')))}</div>
                <div class="lookup-meta"><strong>Avaliacao:</strong> {html.escape(format_currency(row.get('appraisal_value')))}</div>
                <div class="lookup-meta"><strong>Desconto:</strong> {html.escape(str(row.get('discount_pct', '')))}</div>
                <div class="lookup-meta"><strong>Area privativa:</strong> {html.escape(str(row.get('private_area_m2', '')))}</div>
                <div class="lookup-meta"><strong>Quartos:</strong> {html.escape(str(row.get('bedrooms', '')))}</div>
                <div class="lookup-meta"><strong>Vagas:</strong> {html.escape(str(row.get('parking_spots', '')))}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_badges(
        [
            classify_score(row.get("opportunity_score_display")),
            classify_pipeline_status(str(row.get("pipeline_status", ""))),
            classify_risk_level(str(row.get("edital_risk_flags", ""))),
        ]
    )
    st.markdown(
        f"""
        <div class="lookup-grid">
            <div class="lookup-card">
                <div class="lookup-kicker">Pipeline e score</div>
                <div class="lookup-meta"><strong>Status da pipeline:</strong> {html.escape(str(row.get('pipeline_status', '')))}</div>
                <div class="lookup-meta"><strong>Versao do score:</strong> {html.escape(str(row.get('scoring_version', '')))}</div>
                <div class="lookup-meta"><strong>Importado em:</strong> {html.escape(str(row.get('imported_at', '')))}</div>
                <div class="lookup-meta"><strong>Detalhe em:</strong> {html.escape(str(row.get('detail_enriched_at', '')))}</div>
                <div class="lookup-meta"><strong>Edital em:</strong> {html.escape(str(row.get('edital_enriched_at', '')))}</div>
                <div class="lookup-meta"><strong>Score em:</strong> {html.escape(str(row.get('scored_at', '')))}</div>
            </div>
            <div class="lookup-card">
                <div class="lookup-kicker">Edital e descricao</div>
                <div class="lookup-meta"><strong>Modalidade do edital:</strong> {html.escape(str(row.get('edital_sale_mode', '')))}</div>
                <div class="lookup-meta"><strong>Data do edital:</strong> {html.escape(str(row.get('edital_sale_date', '')))}</div>
                <div class="lookup-meta"><strong>Riscos estruturados:</strong> {html.escape(str(row.get('edital_risk_flags', '')))}</div>
                <div class="lookup-meta"><strong>Riscos em texto:</strong> {html.escape(str(row.get('edital_risk_notes', '')))}</div>
                <div class="lookup-description">{html.escape(str(row.get('description', '')))}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    detail_url = row.get("detail_url", "")
    if detail_url:
        st.markdown(f"[Abrir pagina do imovel]({detail_url})")
    st.markdown("</div>", unsafe_allow_html=True)


def render_support_table(table_df: pd.DataFrame) -> None:
    total_items = len(table_df)
    complete_items = int((table_df.get("Status pipeline", pd.Series(dtype=str)) == "Completo").sum())
    strong_items = int(pd.to_numeric(table_df.get("Score moradia"), errors="coerce").ge(80).sum())

    st.markdown(
        f"""
        <div class="support-shell">
            <div class="section-header">
                <div class="section-eyebrow">Base auxiliar</div>
                <h2>Tabela de apoio</h2>
                <div class="section-copy">Visao complementar com detalhes de score, risco e rastreamento para os principais itens filtrados.</div>
            </div>
            <div class="support-metrics">
                <div class="support-metric">
                    <div class="support-metric-label">Itens na mesa</div>
                    <div class="support-metric-value">{total_items}</div>
                    <div class="support-metric-copy">Recorte rapido para consulta operacional.</div>
                </div>
                <div class="support-metric">
                    <div class="support-metric-label">Pipeline completa</div>
                    <div class="support-metric-value">{complete_items}</div>
                    <div class="support-metric-copy">Ativos com todas as etapas concluídas.</div>
                </div>
                <div class="support-metric">
                    <div class="support-metric-label">Score forte</div>
                    <div class="support-metric-value">{strong_items}</div>
                    <div class="support-metric-copy">Itens com score moradia acima de 80.</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_custom_table(
        table_df,
        status_columns=["Status pipeline"],
        wrap_columns=[
            "Bairro",
            "Endereco",
            "Descricao",
            "Motivo preco",
            "Motivo imovel",
            "Motivo localizacao",
            "Motivo liquidez",
            "Motivo risco",
        ],
        wide=True,
        link_columns={"Codigo": "Link"},
        hidden_columns=["Link"],
        extra_class="support-table-card",
    )


def main() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    init_db()

    if settings.database_url.startswith("sqlite:///"):
        db_hint = Path(settings.database_url.replace("sqlite:///", ""))
        st.caption(f"Banco atual: `{db_hint}`")

    render_csv_import_panel()

    df = load_data()
    if df.empty:
        render_empty_state()
        return

    filtered = build_filters(df)
    render_dashboard_header(filtered)
    render_kpis(filtered)
    render_market_spotlight(filtered)
    render_pipeline_health(filtered)

    ranked = filtered.sort_values("opportunity_score_display", ascending=False, na_position="last")
    tab1, tab2, tab3, tab4 = st.tabs(["Radar", "Ranking", "Explorador", "Exportacao"])
    with tab1:
        render_property_cards(ranked, limit=20)
        render_state_ranking(filtered)
        render_charts(filtered)
    with tab2:
        render_top_table(filtered)
    with tab3:
        render_quick_lookup(filtered)
        top_columns = [
            "property_code",
            "city_label",
            "neighborhood_label",
            "address",
            "property_type",
            "private_area_m2",
            "bedrooms",
            "parking_spots",
            "price",
            "appraisal_value",
            "discount_pct",
            "estimated_gain",
            "score_moradia",
            "score_preco",
            "score_imovel",
            "score_localizacao",
            "score_liquidez_residencial",
            "score_risco",
            "score_reason_preco",
            "score_reason_imovel",
            "score_reason_localizacao",
            "score_reason_liquidez",
            "score_reason_risco",
            "edital_sale_mode",
            "edital_sale_date",
            "edital_risk_notes",
            "edital_risk_flags",
            "pipeline_status",
            "scoring_version",
            "imported_at",
            "detail_enriched_at",
            "edital_enriched_at",
            "scored_at",
            "detail_url",
            "description_short",
        ]
        table_df = ranked[[col for col in top_columns if col in ranked.columns]].head(20).rename(
            columns={
                "property_code": "Codigo",
                "city_label": "Cidade",
                "neighborhood_label": "Bairro",
                "address": "Endereco",
                "property_type": "Tipo",
                "private_area_m2": "Area privativa (m2)",
                "bedrooms": "Quartos",
                "parking_spots": "Vagas",
                "price": "Preco",
                "appraisal_value": "Avaliacao",
                "discount_pct": "Desconto (%)",
                "estimated_gain": "Ganho estimado",
                "score_moradia": "Score moradia",
                "score_preco": "Score preco",
                "score_imovel": "Score imovel",
                "score_localizacao": "Score localizacao",
                "score_liquidez_residencial": "Score liquidez",
                "score_risco": "Score risco",
                "score_reason_preco": "Motivo preco",
                "score_reason_imovel": "Motivo imovel",
                "score_reason_localizacao": "Motivo localizacao",
                "score_reason_liquidez": "Motivo liquidez",
                "score_reason_risco": "Motivo risco",
                "edital_sale_mode": "Modalidade edital",
                "edital_sale_date": "Data edital",
                "edital_risk_notes": "Riscos em texto",
                "edital_risk_flags": "Riscos estruturados",
                "pipeline_status": "Status pipeline",
                "scoring_version": "Versao score",
                "imported_at": "Importado em",
                "detail_enriched_at": "Detalhe em",
                "edital_enriched_at": "Edital em",
                "scored_at": "Score em",
                "detail_url": "Link",
                "description_short": "Descricao",
            }
        )
        render_support_table(table_df)
    with tab4:
        render_export_workspace(filtered)


if __name__ == "__main__":
    main()
