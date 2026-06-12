import streamlit as st
import pandas as pd
import plotly.express as px
from utils.db.index import engine
from sqlalchemy import text

st.set_page_config(page_title="Crypto Analytics Dashboard", layout="wide")


# --- POBRANIE TICKERÓW DO FILTRÓW ---
@st.cache_data(ttl=300)
def get_available_tickers():
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT DISTINCT ticker FROM prices ORDER BY ticker")
        )
        return [row[0] for row in result]


try:
    tickers = get_available_tickers()
except Exception as e:
    st.error(f"Błąd połączenia z bazą danych podczas pobierania tickerów: {e}")
    st.stop()

if not tickers:
    st.warning("Brak danych w bazie. Upewnij się, że data_collector działa.")
    st.stop()

time_range_options = {
    "Cała historia": None,
    "Ostatnia godzina": "1 HOUR",
    "Ostatnie 4 godziny": "4 HOUR",
    "Ostatnie 24 godziny": "24 HOUR",
    "Ostatnie 7 dni": "7 DAY",
}

session_options = {
    "Cała doba (24/7)": None,
    "Sesja Azjatycka (01:00 - 08:00)": (1, 8),
    "Sesja Europejska (08:00 - 15:00)": (8, 15),
    "Sesja Amerykańska (15:00 - 22:00)": (15, 22),
}

st.sidebar.title("Nawigacja")
analysis_mode = st.sidebar.radio(
    "Wybierz moduł analityczny:", ["Szeregi Czasowe", "Analiza Ilościowa"]
)
st.sidebar.markdown("---")
st.sidebar.header("Filtry")


@st.cache_data(ttl=30)
def load_timeseries_data(
    selected_tickers, time_range, session, granularity, trend_filter
):
    if not selected_tickers:
        return pd.DataFrame()

    # Określanie agregacji czasu w SQL (PostgreSQL date_trunc / epoch)
    time_agg = "timestamp"
    if granularity == "Średnia z 4 godzin":
        time_agg = "to_timestamp(floor(extract(epoch from timestamp) / 14400) * 14400)"
    elif granularity == "Średnia z 12 godzin":
        time_agg = "to_timestamp(floor(extract(epoch from timestamp) / 43200) * 43200)"
    elif granularity == "Średnia dzienna":
        time_agg = "date_trunc('day', timestamp)"

    where_clauses = ["ticker IN :tickers"]
    params = {"tickers": tuple(selected_tickers)}

    if time_range:
        where_clauses.append(
            f"timestamp >= (SELECT MAX(timestamp) FROM prices) - INTERVAL '{time_range}'"
        )

    if session:
        where_clauses.append("EXTRACT(HOUR FROM timestamp) BETWEEN :start_h AND :end_h")
        params["start_h"] = session[0]
        params["end_h"] = session[1]

    where_str = " AND ".join(where_clauses)

    query = f"""
        SELECT 
            ticker, 
            {time_agg} AS timestamp, 
            AVG(price_usd) AS price_usd
        FROM prices
        WHERE {where_str}
        GROUP BY ticker, timestamp
        ORDER BY timestamp ASC
    """

    df = pd.read_sql(text(query), engine, params=params)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    if not df.empty and trend_filter != "Wszystkie momenty":
        df["price_change"] = df.groupby("ticker")["price_usd"].diff()
        if trend_filter == "Tylko momenty wzrostowe":
            df = df[df["price_change"] > 0]
        else:
            df = df[df["price_change"] < 0]

    return df


@st.cache_data(ttl=30)
def load_quantitative_data(selected_tickers, time_range, freq_interval, data_type):
    if not selected_tickers:
        return pd.DataFrame()

    where_clauses = ["ticker IN :tickers"]
    params = {"tickers": tuple(selected_tickers)}

    if time_range:
        where_clauses.append(
            f"timestamp >= (SELECT MAX(timestamp) FROM prices) - INTERVAL '{time_range}'"
        )

    where_str = " AND ".join(where_clauses)

    time_agg = "timestamp"
    if freq_interval == "15min":
        time_agg = "to_timestamp(floor(extract(epoch from timestamp) / 900) * 900)"
    elif freq_interval == "1h":
        time_agg = "date_trunc('hour', timestamp)"

    # Konstrukcja zapytania zależnie od metryki (Cena vs Zwroty obliczane funkcją okna LAG w SQL)
    if data_type == "Zwroty Procentowe (%)":
        query = f"""
            WITH sampled_data AS (
                SELECT 
                    ticker, 
                    {time_agg} AS timestamp, 
                    AVG(price_usd) AS avg_price
                FROM prices
                WHERE {where_str}
                GROUP BY ticker, timestamp
            ),
            calculated_returns AS (
                SELECT 
                    ticker,
                    timestamp,
                    ((avg_price - LAG(avg_price) OVER (PARTITION BY ticker ORDER BY timestamp)) / 
                    LAG(avg_price) OVER (PARTITION BY ticker ORDER BY timestamp)) * 100 AS metric
                FROM sampled_data
            )
            SELECT ticker, timestamp, metric FROM calculated_returns WHERE metric IS NOT NULL ORDER BY timestamp ASC
        """
    else:
        query = f"""
            SELECT 
                ticker, 
                {time_agg} AS timestamp, 
                AVG(price_usd) AS metric
            FROM prices
            WHERE {where_str}
            GROUP BY ticker, timestamp
            ORDER BY timestamp ASC
        """

    df = pd.read_sql(text(query), engine, params=params)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


if analysis_mode == "Szeregi Czasowe":
    st.title("Analiza Szeregów Czasowych")
    st.markdown(
        "Analiza ciągłości trendu oraz zachowania cen w czasie (agregacja po stronie bazy SQL)."
    )

    selected_tickers = st.sidebar.multiselect(
        "1. Wybierz aktywo", tickers, default=tickers[:3]
    )
    selected_time_range = st.sidebar.selectbox(
        "2. Przedział czasowy", list(time_range_options.keys()), index=4
    )
    selected_session = st.sidebar.selectbox(
        "3. Filtruj pory dnia (Sesje)", list(session_options.keys())
    )
    granularity = st.sidebar.selectbox(
        "4. Agregacja czasu na osi X",
        ["Surowe dane", "Średnia z 4 godzin", "Średnia z 12 godzin", "Średnia dzienna"],
    )
    trend_filter = st.sidebar.radio(
        "5. Kierunek trendu",
        ["Wszystkie momenty", "Tylko momenty wzrostowe", "Tylko momenty spadkowe"],
    )

    df_ts = load_timeseries_data(
        selected_tickers,
        time_range_options[selected_time_range],
        session_options[selected_session],
        granularity,
        trend_filter,
    )

    if df_ts.empty:
        st.info("Brak danych dla wybranych filtrów.")
    else:
        fig_time = px.line(
            df_ts,
            x="timestamp",
            y="price_usd",
            color="ticker",
            markers=True,
            title="Wykres zmian cen",
        )
        st.plotly_chart(fig_time, use_container_width=True)


elif analysis_mode == "Analiza Ilościowa":
    st.title("Analiza Ilościowa (Quantitative Analysis)")
    st.markdown(
        "Statystyczne badanie zmienności wykonywane bezpośrednio na danych z bazy SQL."
    )

    selected_tickers = st.sidebar.multiselect(
        "1. Wybierz aktywa do porównania", tickers, default=tickers[:3]
    )
    selected_time_range = st.sidebar.selectbox(
        "2. Próbka historyczna", list(time_range_options.keys()), index=4
    )

    freq_options = {
        "Brak (Surowe próbki)": None,
        "Próbkowanie co 15 minut": "15min",
        "Próbkowanie co 1 godzinę": "1h",
    }
    selected_freq = st.sidebar.selectbox(
        "3. Częstotliwość próbkowania", list(freq_options.keys()), index=1
    )
    data_type = st.sidebar.radio(
        "4. Badana zmienna (Wybór metryki)",
        ["Cena Nominalna (USD)", "Zwroty Procentowe (%)"],
    )
    outlier_cutoff = st.sidebar.slider(
        "5. Filtr Wartości Skrajnych (%)", min_value=0, max_value=15, value=0, step=1
    )

    df_qa = load_quantitative_data(
        selected_tickers,
        time_range_options[selected_time_range],
        freq_options[selected_freq],
        data_type,
    )

    # Filtr percentyli (Outliers) zostaje w Pandas, ponieważ wymaga wyliczenia kwantyli per wybrana grupa na gotowej próbie
    if not df_qa.empty and outlier_cutoff > 0:
        lower_bound = outlier_cutoff / 100.0
        upper_bound = 1.0 - lower_bound
        filtered_dfs = []
        for ticker in selected_tickers:
            t_df = df_qa[df_qa["ticker"] == ticker]
            if not t_df.empty:
                q_low = t_df["metric"].quantile(lower_bound)
                q_high = t_df["metric"].quantile(upper_bound)
                filtered_dfs.append(
                    t_df[(t_df["metric"] >= q_low) & (t_df["metric"] <= q_high)]
                )
        df_qa = pd.concat(filtered_dfs) if filtered_dfs else pd.DataFrame()

    y_axis_label = (
        "Zmiana procentowa (%)"
        if data_type == "Zwroty Procentowe (%)"
        else "Cena (USD)"
    )

    if df_qa.empty:
        st.info("Brak danych po nałożeniu filtrów.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Rozkład zmienności (Box Plot)")
            fig_box = px.box(
                df_qa,
                x="ticker",
                y="metric",
                color="ticker",
                labels={"metric": y_axis_label, "ticker": "Aktywo"},
            )
            st.plotly_chart(fig_box, use_container_width=True)

        with col2:
            st.subheader("Częstotliwość występowania (Histogram)")
            fig_hist = px.histogram(
                df_qa,
                x="metric",
                color="ticker",
                barmode="overlay",
                nbins=40,
                labels={"metric": y_axis_label, "count": "Liczba próbek"},
            )
            st.plotly_chart(fig_hist, use_container_width=True)

        st.markdown("---")
        st.subheader("Tablica statystyk opisowych dla wybranej metryki")

        stats_data = []
        for ticker in selected_tickers:
            t_df = df_qa[df_qa["ticker"] == ticker]["metric"]
            if not t_df.empty:
                stats_data.append(
                    {
                        "Kryptowaluta": ticker,
                        "Liczba próbek": t_df.count(),
                        "Średnia": f"{t_df.mean():.4f}",
                        "Mediana": f"{t_df.median():.4f}",
                        "Min": f"{t_df.min():.4f}",
                        "Max": f"{t_df.max():.4f}",
                        "Odchylenie Std.": f"{t_df.std():.4f}",
                        "Skew": f"{t_df.skew():.4f}",
                    }
                )
        if stats_data:
            st.dataframe(pd.DataFrame(stats_data), use_container_width=True)
