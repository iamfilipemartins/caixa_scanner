from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine

from caixa_scanner.config import settings


st.set_page_config(
    page_title="Caixa Scanner Dashboard",
    page_icon="🏠",
    layout="wide",
)


@st.cache_resource
def get_engine():
    return create_engine(settings.database_url, future=True)


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

    if "accepts_fgts" not in df.columns:
        df["accepts_fgts"] = None
    if "accepts_financing" not in df.columns:
        df["accepts_financing"] = None

    df["opportunity_score_display"] = df["score_moradia"].where(df["score_moradia"].notna(), df["opportunity_score"])
    df["estimated_gain"] = df["appraisal_value"] - df["price"]
    df["city_label"] = df["city"]
    df.loc[df["uf"] != "", "city_label"] = df["city"] + "/" + df["uf"]

    df["neighborhood_label"] = df["neighborhood"]
    has_city = df["city"] != ""
    has_uf = df["uf"] != ""
    df.loc[has_city & has_uf, "neighborhood_label"] = df["neighborhood"] + " - " + df["city"] + "/" + df["uf"]
    df.loc[(df["neighborhood"] == "") & has_city & has_uf, "neighborhood_label"] = df["city"] + "/" + df["uf"]

    df["description_short"] = df["description"]
    df.loc[df["description_short"].str.len() > 140, "description_short"] = (
        df["description_short"].str.slice(0, 140) + "..."
    )

    def bool_to_label(value):
        if pd.isna(value):
            return "NÃ£o informado"
        if isinstance(value, (bool, int)):
            return "Sim" if bool(value) else "NÃ£o"

        normalized = str(value).strip().lower()
        if normalized in {"sim", "true", "1"}:
            return "Sim"
        if normalized in {"nÃ£o", "nao", "false", "0"}:
            return "NÃ£o"
        return "NÃ£o informado"

    df["accepts_fgts_label"] = df["accepts_fgts"].apply(bool_to_label)
    df["accepts_financing_label"] = df["accepts_financing"].apply(bool_to_label)
    return df


def render_empty_state() -> None:
    st.title("🏠 Caixa Scanner Dashboard")
    st.info(
        "Nenhum dado encontrado no banco ainda. Rode primeiro o pipeline com "
        "`python -m caixa_scanner.main scan --ufs SP MG` e depois volte ao dashboard."
    )


def build_filters(df: pd.DataFrame) -> pd.DataFrame:
    filtered = df.copy()
    st.sidebar.header("Filtros")

    if "uf" in filtered.columns:
        ufs = sorted([x for x in filtered["uf"].dropna().astype(str).unique().tolist() if x])
        selected_ufs = st.sidebar.multiselect("UF", ufs)
        if selected_ufs:
            filtered = filtered[filtered["uf"].isin(selected_ufs)]

    if "city" in filtered.columns:
        cities = sorted([x for x in filtered["city"].dropna().astype(str).unique().tolist() if x])
        selected_cities = st.sidebar.multiselect("Cidade", cities)
        if selected_cities:
            filtered = filtered[filtered["city"].isin(selected_cities)]

    if "neighborhood" in filtered.columns:
        neighborhoods = sorted([x for x in filtered["neighborhood"].dropna().astype(str).unique().tolist() if x])
        selected_neighborhoods = st.sidebar.multiselect("Bairro", neighborhoods)
        if selected_neighborhoods:
            filtered = filtered[filtered["neighborhood"].isin(selected_neighborhoods)]

    if "property_type" in filtered.columns:
        property_types = sorted([x for x in filtered["property_type"].dropna().astype(str).unique().tolist() if x])
        selected_property_types = st.sidebar.multiselect("Tipo do imÃ³vel", property_types)
        if selected_property_types:
            filtered = filtered[filtered["property_type"].isin(selected_property_types)]

    if "bedrooms" in filtered.columns:
        bedroom_values = sorted([int(x) for x in filtered["bedrooms"].dropna().unique().tolist() if pd.notna(x)])
        selected_bedrooms = st.sidebar.multiselect("Quartos", bedroom_values)
        if selected_bedrooms:
            filtered = filtered[filtered["bedrooms"].isin(selected_bedrooms)]

    if "parking_spots" in filtered.columns:
        parking_values = sorted([int(x) for x in filtered["parking_spots"].dropna().unique().tolist() if pd.notna(x)])
        selected_parking = st.sidebar.multiselect("Vagas", parking_values)
        if selected_parking:
            filtered = filtered[filtered["parking_spots"].isin(selected_parking)]

    if "private_area_m2" in filtered.columns and filtered["private_area_m2"].dropna().size > 0:
        min_area = float(filtered["private_area_m2"].dropna().min())
        max_area = float(filtered["private_area_m2"].dropna().max())
        selected_area = (
            (min_area, max_area)
            if min_area == max_area
            else st.sidebar.slider(
                "Ãrea privativa (mÂ²)",
                min_value=min_area,
                max_value=max_area,
                value=(min_area, max_area),
            )
        )
        filtered = filtered[
            (filtered["private_area_m2"].fillna(0) >= selected_area[0])
            & (filtered["private_area_m2"].fillna(0) <= selected_area[1])
        ]

    if "price" in filtered.columns and filtered["price"].dropna().size > 0:
        min_price = float(filtered["price"].dropna().min())
        max_price = float(filtered["price"].dropna().max())
        selected_price = (
            (min_price, max_price)
            if min_price == max_price
            else st.sidebar.slider(
                "PreÃ§o (R$)",
                min_value=min_price,
                max_value=max_price,
                value=(min_price, max_price),
            )
        )
        filtered = filtered[
            (filtered["price"].fillna(0) >= selected_price[0])
            & (filtered["price"].fillna(0) <= selected_price[1])
        ]

    if "discount_pct" in filtered.columns and filtered["discount_pct"].dropna().size > 0:
        min_discount = float(filtered["discount_pct"].dropna().min())
        max_discount = float(filtered["discount_pct"].dropna().max())
        selected_discount = (
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
            (filtered["discount_pct"].fillna(0) >= selected_discount[0])
            & (filtered["discount_pct"].fillna(0) <= selected_discount[1])
        ]

    if "opportunity_score_display" in filtered.columns and filtered["opportunity_score_display"].dropna().size > 0:
        min_score = float(filtered["opportunity_score_display"].dropna().min())
        max_score = float(filtered["opportunity_score_display"].dropna().max())
        selected_score = (
            (min_score, max_score)
            if min_score == max_score
            else st.sidebar.slider(
                "Score moradia",
                min_value=min_score,
                max_value=max_score,
                value=(min_score, max_score),
            )
        )
        filtered = filtered[
            (filtered["opportunity_score_display"].fillna(0) >= selected_score[0])
            & (filtered["opportunity_score_display"].fillna(0) <= selected_score[1])
        ]

    if "accepts_financing_label" in filtered.columns:
        financing_filter = st.sidebar.selectbox("Financiamento", ["Todos", "Sim", "NÃ£o", "NÃ£o informado"])
        if financing_filter != "Todos":
            filtered = filtered[filtered["accepts_financing_label"] == financing_filter]

    if "accepts_fgts_label" in filtered.columns:
        fgts_filter = st.sidebar.selectbox("FGTS", ["Todos", "Sim", "NÃ£o", "NÃ£o informado"])
        if fgts_filter != "Todos":
            filtered = filtered[filtered["accepts_fgts_label"] == fgts_filter]

    return filtered


def render_kpis(df: pd.DataFrame) -> None:
    col1, col2, col3, col4 = st.columns(4)
    score_medio = round(df["opportunity_score_display"].dropna().mean(), 2) if not df.empty else 0
    desconto_medio = round(df["discount_pct"].dropna().mean(), 2) if not df.empty else 0
    ganho_medio = round(df["estimated_gain"].dropna().mean(), 2) if not df.empty else 0
    area_media = round(df["private_area_m2"].dropna().mean(), 2) if not df.empty else 0

    col1.metric("Score mÃ©dio moradia", score_medio)
    col2.metric("Desconto mÃ©dio (%)", desconto_medio)
    col3.metric("Ganho bruto mÃ©dio (R$)", f"{ganho_medio:,.2f}")
    col4.metric("Ãrea privativa mÃ©dia (mÂ²)", area_media)


def render_state_ranking(df: pd.DataFrame) -> None:
    st.subheader("Melhores oportunidades por estado")
    ranking = (
        df.sort_values(["uf", "opportunity_score_display"], ascending=[True, False])
        .groupby("uf", as_index=False)
        .first()[[
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
            "score_preco",
            "score_imovel",
            "score_localizacao",
            "score_liquidez_residencial",
            "score_risco",
            "accepts_financing_label",
            "accepts_fgts_label",
            "detail_url",
            "description_short",
            "address",
        ]]
        .rename(
            columns={
                "uf": "UF",
                "property_code": "CÃ³digo",
                "city_label": "Cidade",
                "neighborhood_label": "Bairro",
                "property_type": "Tipo",
                "private_area_m2": "Ãrea privativa (mÂ²)",
                "bedrooms": "Quartos",
                "parking_spots": "Vagas",
                "price": "PreÃ§o",
                "appraisal_value": "AvaliaÃ§Ã£o",
                "discount_pct": "Desconto (%)",
                "estimated_gain": "Ganho estimado",
                "opportunity_score_display": "Score moradia",
                "score_preco": "Score preÃ§o",
                "score_imovel": "Score imÃ³vel",
                "score_localizacao": "Score localizaÃ§Ã£o",
                "score_liquidez_residencial": "Score liquidez",
                "score_risco": "Score risco",
                "accepts_financing_label": "Financiamento",
                "accepts_fgts_label": "FGTS",
                "detail_url": "Detalhe",
                "description_short": "DescriÃ§Ã£o",
                "address": "EndereÃ§o",
            }
        )
    )
    st.dataframe(ranking, use_container_width=True, hide_index=True)


def render_charts(df: pd.DataFrame) -> None:
    left, right = st.columns(2)

    with left:
        st.subheader("Top 10 estados por score mÃ©dio")
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
        st.caption("Sem dados suficientes para o grÃ¡fico de dispersÃ£o.")
    else:
        st.scatter_chart(scatter, x="discount_pct", y="opportunity_score_display", color="uf")


def render_top_table(df: pd.DataFrame) -> None:
    st.subheader("Ranking geral filtrado")
    limit = st.slider("Quantidade de imÃ³veis no ranking", min_value=10, max_value=200, value=50, step=10)
    top_df = (
        df.sort_values(["opportunity_score_display", "discount_pct"], ascending=[False, False])
        .head(limit)
        .loc[:, [
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
            "detail_url",
            "edital_url",
        ]]
        .rename(
            columns={
                "property_code": "CÃ³digo",
                "uf": "UF",
                "city_label": "Cidade",
                "neighborhood_label": "Bairro",
                "price": "PreÃ§o",
                "appraisal_value": "AvaliaÃ§Ã£o",
                "estimated_gain": "Potencial bruto",
                "discount_pct": "Desconto (%)",
                "private_area_m2": "Ãrea (mÂ²)",
                "bedrooms": "Quartos",
                "parking_spots": "Vagas",
                "accepts_financing_label": "Financiamento",
                "accepts_fgts_label": "FGTS",
                "opportunity_score_display": "Score",
                "score_reason": "Motivos do score",
                "detail_url": "Detalhe",
                "edital_url": "Edital",
            }
        )
    )
    st.dataframe(top_df, use_container_width=True, hide_index=True)


def render_download(df: pd.DataFrame) -> None:
    st.subheader("ExportaÃ§Ã£o")
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
        st.info("Nenhum imÃ³vel encontrado com os filtros atuais.")
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
                    st.markdown(f"### {str(row.get('property_type', '') or '').title()} • {row.get('city_label', '')}")
                    st.markdown(f"**Bairro:** {row.get('neighborhood_label', '')}")
                    st.markdown(f"**EndereÃ§o:** {row.get('address', '')}")
                    st.markdown(f"**CÃ³digo:** {row.get('property_code', '')}")

                    info_parts = []
                    if pd.notna(row.get("private_area_m2")):
                        info_parts.append(f"{float(row['private_area_m2']):.2f} mÂ²")
                    if pd.notna(row.get("bedrooms")):
                        info_parts.append(f"{int(row['bedrooms'])} quartos")
                    if pd.notna(row.get("parking_spots")):
                        info_parts.append(f"{int(row['parking_spots'])} vagas")
                    if info_parts:
                        st.markdown(" | ".join(info_parts))

                    finance_parts = []
                    if pd.notna(row.get("price")):
                        finance_parts.append(
                            f"PreÃ§o: R$ {float(row['price']):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        )
                    if pd.notna(row.get("discount_pct")):
                        finance_parts.append(f"Desconto: {float(row['discount_pct']):.2f}%")
                    if pd.notna(row.get("opportunity_score_display")):
                        finance_parts.append(f"Score: {float(row['opportunity_score_display']):.2f}")
                    if finance_parts:
                        st.markdown(" • ".join(finance_parts))

                    if row.get("score_moradia_reason"):
                        st.caption(row["score_moradia_reason"])
                    elif row.get("score_reason"):
                        st.caption(row["score_reason"])

                    if row.get("detail_url"):
                        st.link_button("Abrir na Caixa", row["detail_url"], use_container_width=True)


def render_quick_lookup(df: pd.DataFrame) -> None:
    st.subheader("Consulta rÃ¡pida de imÃ³vel")
    property_codes = df["property_code"].dropna().astype(str).unique().tolist()
    selected_code = st.selectbox("Selecione o cÃ³digo do imÃ³vel", property_codes)

    if not selected_code:
        return

    selected_row = df[df["property_code"].astype(str) == str(selected_code)].head(1)
    if selected_row.empty:
        return

    row = selected_row.iloc[0]
    st.markdown(f"**CÃ³digo:** {row.get('property_code', '')}")
    st.markdown(f"**Cidade/Bairro:** {row.get('city_label', '')} | {row.get('neighborhood_label', '')}")
    st.markdown(f"**EndereÃ§o:** {row.get('address', '')}")
    st.markdown(f"**Tipo:** {row.get('property_type', '')}")
    st.markdown(f"**Ãrea privativa:** {row.get('private_area_m2', '')}")
    st.markdown(f"**Quartos:** {row.get('bedrooms', '')}")
    st.markdown(f"**Vagas:** {row.get('parking_spots', '')}")
    st.markdown(f"**PreÃ§o:** R$ {row.get('price', 0):,.2f}" if pd.notna(row.get("price")) else "**PreÃ§o:**")
    st.markdown(
        f"**AvaliaÃ§Ã£o:** R$ {row.get('appraisal_value', 0):,.2f}"
        if pd.notna(row.get("appraisal_value"))
        else "**AvaliaÃ§Ã£o:**"
    )
    st.markdown(f"**Desconto:** {row.get('discount_pct', '')}")
    st.markdown(f"**Score moradia:** {row.get('score_moradia', '')}")
    st.markdown(f"**DescriÃ§Ã£o completa:** {row.get('description', '')}")
    detail_url = row.get("detail_url", "")
    if detail_url:
        st.markdown(f"[Abrir pÃ¡gina do imÃ³vel]({detail_url})")


def main() -> None:
    st.title("🏠 Caixa Scanner Dashboard")
    st.caption("VisÃ£o rÃ¡pida das melhores oportunidades por estado, com filtros e ranking geral.")

    db_hint = Path(settings.database_url.replace("sqlite:///", "")) if settings.database_url.startswith("sqlite:///") else None
    if db_hint:
        st.caption(f"Banco atual: `{db_hint}`")

    df = load_data()
    if df.empty:
        render_empty_state()
        return

    filtered = build_filters(df)
    render_kpis(filtered)
    render_property_cards(filtered.sort_values("opportunity_score_display", ascending=False, na_position="last"), limit=20)
    render_quick_lookup(filtered)

    top_moradia_cols = [
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
        "detail_url",
        "description_short",
    ]
    ranked = filtered.sort_values("opportunity_score_display", ascending=False, na_position="last")
    table_df = ranked[[col for col in top_moradia_cols if col in ranked.columns]].head(20).rename(
        columns={
            "property_code": "CÃ³digo",
            "city_label": "Cidade",
            "neighborhood_label": "Bairro",
            "address": "EndereÃ§o",
            "property_type": "Tipo",
            "private_area_m2": "Ãrea privativa (mÂ²)",
            "bedrooms": "Quartos",
            "parking_spots": "Vagas",
            "price": "PreÃ§o",
            "appraisal_value": "AvaliaÃ§Ã£o",
            "discount_pct": "Desconto (%)",
            "estimated_gain": "Ganho estimado",
            "score_moradia": "Score moradia",
            "score_preco": "Score preÃ§o",
            "score_imovel": "Score imÃ³vel",
            "score_localizacao": "Score localizaÃ§Ã£o",
            "score_liquidez_residencial": "Score liquidez",
            "score_risco": "Score risco",
            "score_moradia_reason": "Justificativa",
            "detail_url": "Link",
            "description_short": "DescriÃ§Ã£o",
        }
    )
    st.dataframe(table_df, use_container_width=True, hide_index=True)

    tab1, tab2, tab3 = st.tabs(["VisÃ£o por estado", "Ranking detalhado", "Dados exportÃ¡veis"])
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
