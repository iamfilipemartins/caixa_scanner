from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine

SRC_ROOT = Path(__file__).resolve().parents[2]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from caixa_scanner.config import settings
from caixa_scanner.database import init_db


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


def build_risk_flag_summary(row: pd.Series) -> str:
    labels = [label for column, label in RISK_FLAG_LABELS.items() if bool(row.get(column))]
    return "; ".join(labels)


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
    ]
    bool_cols = [
        "accepts_fgts",
        "accepts_financing",
        *RISK_FLAG_LABELS.keys(),
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
    return df


def render_empty_state() -> None:
    st.title("Caixa Scanner Dashboard")
    st.info(
        "Nenhum dado encontrado no banco ainda. Rode primeiro o pipeline com "
        "`python -m caixa_scanner.main scan --ufs SP MG` e depois volte ao dashboard."
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
    occupied_share = round(df["edital_has_occupied_risk"].fillna(False).mean() * 100, 1) if not df.empty else 0.0

    col1.metric("Score medio", score_mean)
    col2.metric("Desconto medio (%)", discount_mean)
    col3.metric("Ganho bruto medio (R$)", f"{gain_mean:,.2f}")
    col4.metric("Com risco de ocupacao (%)", occupied_share)


def render_state_ranking(df: pd.DataFrame) -> None:
    st.subheader("Melhores oportunidades por estado")
    ranking = (
        df.sort_values(["uf", "opportunity_score_display"], ascending=[True, False])
        .groupby("uf", as_index=False)
        .first()[
            [
                "uf",
                "property_code",
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
                "detail_url",
            ]
        ]
        .rename(
            columns={
                "uf": "UF",
                "property_code": "Codigo",
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
                "detail_url": "Detalhe",
            }
        )
    )
    st.dataframe(ranking, use_container_width=True, hide_index=True)


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
        st.bar_chart(state_scores[["score_medio"]])

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
        st.bar_chart(state_volume)

    st.subheader("Score x desconto")
    scatter = df[["discount_pct", "opportunity_score_display", "uf"]].dropna().copy()
    if scatter.empty:
        st.caption("Sem dados suficientes para o grafico de dispersao.")
    else:
        st.scatter_chart(scatter, x="discount_pct", y="opportunity_score_display", color="uf")


def render_top_table(df: pd.DataFrame) -> None:
    st.subheader("Ranking geral filtrado")
    limit = st.slider("Quantidade de imoveis no ranking", min_value=10, max_value=200, value=50, step=10)
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
                "score_reason",
                "edital_sale_mode",
                "edital_sale_date",
                "edital_risk_notes",
                "edital_risk_flags",
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
                "score_reason": "Motivos do score",
                "edital_sale_mode": "Modalidade edital",
                "edital_sale_date": "Data edital",
                "edital_risk_notes": "Riscos em texto",
                "edital_risk_flags": "Riscos estruturados",
                "detail_url": "Detalhe",
                "edital_url": "Edital",
            }
        )
    )
    st.dataframe(top_df, use_container_width=True, hide_index=True)


def render_download(df: pd.DataFrame) -> None:
    st.subheader("Exportacao")
    ranked = df.sort_values("opportunity_score_display", ascending=False, na_position="last")
    csv_bytes = ranked.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Baixar CSV filtrado",
        data=csv_bytes,
        file_name="caixa_oportunidades_filtradas.csv",
        mime="text/csv",
    )


def render_property_cards(df: pd.DataFrame, limit: int = 20) -> None:
    st.subheader("Melhores oportunidades em cards")
    if df.empty:
        st.info("Nenhum imovel encontrado com os filtros atuais.")
        return

    cards_df = df.head(limit).copy()
    for i in range(0, len(cards_df), 2):
        cols = st.columns(2)
        for j in range(2):
            idx = i + j
            if idx >= len(cards_df):
                continue

            row = cards_df.iloc[idx]
            with cols[j]:
                with st.container(border=True):
                    title = str(row.get("property_type", "") or "").title()
                    st.markdown(f"### {title} | {row.get('city_label', '')}")
                    st.markdown(f"**Bairro:** {row.get('neighborhood_label', '')}")
                    st.markdown(f"**Endereco:** {row.get('address', '')}")
                    st.markdown(f"**Codigo:** {row.get('property_code', '')}")

                    info_parts: list[str] = []
                    if pd.notna(row.get("private_area_m2")):
                        info_parts.append(f"{float(row['private_area_m2']):.2f} m2")
                    if pd.notna(row.get("bedrooms")):
                        info_parts.append(f"{int(row['bedrooms'])} quartos")
                    if pd.notna(row.get("parking_spots")):
                        info_parts.append(f"{int(row['parking_spots'])} vagas")
                    if info_parts:
                        st.markdown(" | ".join(info_parts))

                    finance_parts: list[str] = []
                    if pd.notna(row.get("price")):
                        finance_parts.append(f"Preco: {format_currency(row['price'])}")
                    if pd.notna(row.get("discount_pct")):
                        finance_parts.append(f"Desconto: {float(row['discount_pct']):.2f}%")
                    if pd.notna(row.get("opportunity_score_display")):
                        finance_parts.append(f"Score: {float(row['opportunity_score_display']):.2f}")
                    if finance_parts:
                        st.markdown(" | ".join(finance_parts))

                    if row.get("edital_sale_mode"):
                        st.caption(f"Edital: {row['edital_sale_mode']} | {row.get('edital_sale_date') or 'sem data'}")
                    if row.get("edital_risk_flags"):
                        st.caption(f"Riscos estruturados: {row['edital_risk_flags']}")
                    elif row.get("edital_risk_notes"):
                        st.caption(f"Riscos: {row['edital_risk_notes']}")
                    elif row.get("score_moradia_reason"):
                        st.caption(row["score_moradia_reason"])
                    elif row.get("score_reason"):
                        st.caption(row["score_reason"])

                    if row.get("detail_url"):
                        st.link_button("Abrir na Caixa", row["detail_url"], use_container_width=True)


def render_quick_lookup(df: pd.DataFrame) -> None:
    st.subheader("Consulta rapida de imovel")
    property_codes = df["property_code"].dropna().astype(str).unique().tolist()
    selected_code = st.selectbox("Selecione o codigo do imovel", property_codes)
    if not selected_code:
        return

    selected_row = df[df["property_code"].astype(str) == str(selected_code)].head(1)
    if selected_row.empty:
        return

    row = selected_row.iloc[0]
    st.markdown(f"**Codigo:** {row.get('property_code', '')}")
    st.markdown(f"**Cidade/Bairro:** {row.get('city_label', '')} | {row.get('neighborhood_label', '')}")
    st.markdown(f"**Endereco:** {row.get('address', '')}")
    st.markdown(f"**Tipo:** {row.get('property_type', '')}")
    st.markdown(f"**Area privativa:** {row.get('private_area_m2', '')}")
    st.markdown(f"**Quartos:** {row.get('bedrooms', '')}")
    st.markdown(f"**Vagas:** {row.get('parking_spots', '')}")
    st.markdown(f"**Preco:** {format_currency(row.get('price'))}")
    st.markdown(f"**Avaliacao:** {format_currency(row.get('appraisal_value'))}")
    st.markdown(f"**Desconto:** {row.get('discount_pct', '')}")
    st.markdown(f"**Score moradia:** {row.get('score_moradia', '')}")
    st.markdown(f"**Modalidade do edital:** {row.get('edital_sale_mode', '')}")
    st.markdown(f"**Data do edital:** {row.get('edital_sale_date', '')}")
    st.markdown(f"**Riscos estruturados:** {row.get('edital_risk_flags', '')}")
    st.markdown(f"**Riscos em texto:** {row.get('edital_risk_notes', '')}")
    st.markdown(f"**Descricao completa:** {row.get('description', '')}")
    detail_url = row.get("detail_url", "")
    if detail_url:
        st.markdown(f"[Abrir pagina do imovel]({detail_url})")


def main() -> None:
    st.title("Caixa Scanner Dashboard")
    st.caption("Visao rapida das melhores oportunidades por estado, com filtros e ranking geral.")

    init_db()

    if settings.database_url.startswith("sqlite:///"):
        db_hint = Path(settings.database_url.replace("sqlite:///", ""))
        st.caption(f"Banco atual: `{db_hint}`")

    df = load_data()
    if df.empty:
        render_empty_state()
        return

    filtered = build_filters(df)
    render_kpis(filtered)

    ranked = filtered.sort_values("opportunity_score_display", ascending=False, na_position="last")
    render_property_cards(ranked, limit=20)
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
        "score_moradia_reason",
        "edital_sale_mode",
        "edital_sale_date",
        "edital_risk_notes",
        "edital_risk_flags",
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
            "score_moradia_reason": "Justificativa",
            "edital_sale_mode": "Modalidade edital",
            "edital_sale_date": "Data edital",
            "edital_risk_notes": "Riscos em texto",
            "edital_risk_flags": "Riscos estruturados",
            "detail_url": "Link",
            "description_short": "Descricao",
        }
    )
    st.dataframe(table_df, use_container_width=True, hide_index=True)

    tab1, tab2, tab3 = st.tabs(["Visao por estado", "Ranking detalhado", "Dados exportaveis"])
    with tab1:
        render_state_ranking(filtered)
        render_charts(filtered)
    with tab2:
        render_top_table(filtered)
    with tab3:
        st.subheader("Base filtrada")
        st.dataframe(filtered, use_container_width=True, hide_index=True)
        render_download(filtered)


if __name__ == "__main__":
    main()
