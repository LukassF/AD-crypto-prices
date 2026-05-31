import streamlit as st
import pandas as pd
import plotly.express as px
from utils.db.index import engine

st.set_page_config(page_title="Crypto Analytics Dashboard", layout="wide")
@st.cache_data(ttl=60)
def load_data():
    query = "SELECT ticker, price_usd, timestamp FROM prices ORDER BY timestamp ASC"
    df = pd.read_sql(query, engine)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Błąd bazy danych: {e}")
    st.stop()

if df_raw.empty:
    st.warning("Brak danych w bazie. Upewnij się, że data_collector działa.")
    st.stop()

tickers = df_raw['ticker'].unique().tolist()
time_range_options = {
    "Cała historia": None,
    "Ostatnia godzina": pd.Timedelta(hours=1),
    "Ostatnie 4 godziny": pd.Timedelta(hours=4),
    "Ostatnie 24 godziny": pd.Timedelta(hours=24),
    "Ostatnie 7 dni": pd.Timedelta(days=7)
}

st.sidebar.title("Nawigacja")
analysis_mode = st.sidebar.radio("Wybierz moduł analityczny:", ["Szeregi Czasowe", "Analiza Ilościowa"])

st.sidebar.markdown("---")
st.sidebar.header("Filtry")

if analysis_mode == "Szeregi Czasowe":
    st.title("Analiza Szeregów Czasowych")
    st.markdown("Analiza ciągłości trendu oraz zachowania cen w czasie.")

    selected_tickers = st.sidebar.multiselect("1. Wybierz aktywo", tickers, default=tickers)
    selected_time_range = st.sidebar.selectbox("2. Przedział czasowy", list(time_range_options.keys()), index=4)
    
    session_options = {
        "Cała doba (24/7)": range(0, 24),
        "Sesja Azjatycka (01:00 - 08:00)": range(1, 9),
        "Sesja Europejska (08:00 - 15:00)": range(8, 16),
        "Sesja Amerykańska (15:00 - 22:00)": range(15, 23)
    }
    selected_session = st.sidebar.selectbox("3. Filtruj pory dnia (Sesje)", list(session_options.keys()))
    
    granularity = st.sidebar.selectbox("4. Agregacja czasu na osi X", ["Surowe dane", "Średnia z 4 godzin", "Średnia z 12 godzin", "Średnia dzienna"])
    trend_filter = st.sidebar.radio("5. Kierunek trendu", ["Wszystkie momenty", "Tylko momenty wzrostowe", "Tylko momenty spadkowe"])

    df_ts = df_raw.copy()
    df_ts = df_ts[df_ts['ticker'].isin(selected_tickers)]
    
    if time_range_options[selected_time_range] is not None and not df_ts.empty:
        df_ts = df_ts[df_ts['timestamp'] >= df_ts['timestamp'].max() - time_range_options[selected_time_range]]
    if not df_ts.empty:
        df_ts = df_ts[df_ts['timestamp'].dt.hour.isin(session_options[selected_session])]

    if not df_ts.empty:
        if granularity == "Średnia z 4 godzin":
            df_ts = df_ts.groupby(['ticker', pd.Grouper(key='timestamp', freq='4h')])['price_usd'].mean().reset_index()
        elif granularity == "Średnia z 12 godzin":
            df_ts = df_ts.groupby(['ticker', pd.Grouper(key='timestamp', freq='12h')])['price_usd'].mean().reset_index()
        elif granularity == "Średnia dzienna":
            df_ts = df_ts.groupby(['ticker', pd.Grouper(key='timestamp', freq='1D')])['price_usd'].mean().reset_index()
            
    if not df_ts.empty and trend_filter != "Wszystkie momenty":
        df_ts = df_ts.sort_values(by=['ticker', 'timestamp'])
        df_ts['price_change'] = df_ts.groupby('ticker')['price_usd'].diff()
        if trend_filter == "Tylko momenty wzrostowe":
            df_ts = df_ts[df_ts['price_change'] > 0]
        else:
            df_ts = df_ts[df_ts['price_change'] < 0]

    if df_ts.empty:
        st.info("Brak danych dla wybranego filtru.")
    else:
        fig_time = px.line(df_ts, x="timestamp", y="price_usd", color="ticker", markers=True, title=f"Wykres zmian cen")
        st.plotly_chart(fig_time, use_container_width=True)


elif analysis_mode == "Analiza Ilościowa":
    st.title("Analiza Ilościowa (Quantitative Analysis)")
    st.markdown("Statystyczne badanie zmienności, ryzyka i rozkładu danych w wybranej próbie, z pominięciem osi czasu.")

    selected_tickers = st.sidebar.multiselect("1. Wybierz aktywa do porównania", tickers, default=tickers)
    selected_time_range = st.sidebar.selectbox("2. Próbka historyczna", list(time_range_options.keys()), index=4)
    
    freq_options = {"Brak (Surowe próbki)": None, "Próbkowanie co 15 minut": "15min", "Próbkowanie co 1 godzinę": "1h"}
    selected_freq = st.sidebar.selectbox("3. Częstotliwość próbkowania", list(freq_options.keys()), index=1)
    
    data_type = st.sidebar.radio("4. Badana zmienna (Wybór metryki)", ["Cena Nominalna (USD)", "Zwroty Procentowe (%)"])
    
    outlier_cutoff = st.sidebar.slider("5. Filtr Wartości Skrajnych (%)", min_value=0, max_value=15, value=0, step=1, 
                                       help="Obcina X% najwyższych i najniższych odczytów, aby usunąć rynkowe anomalie i szum (tzw. percentyle).")

    df_qa = df_raw.copy()
    df_qa = df_qa[df_qa['ticker'].isin(selected_tickers)]
    
    if time_range_options[selected_time_range] is not None and not df_qa.empty:
        df_qa = df_qa[df_qa['timestamp'] >= df_qa['timestamp'].max() - time_range_options[selected_time_range]]
    if freq_options[selected_freq] is not None and not df_qa.empty:
        df_qa = df_qa.groupby(['ticker', pd.Grouper(key='timestamp', freq=freq_options[selected_freq])])['price_usd'].mean().reset_index()

    if not df_qa.empty:
        df_qa = df_qa.sort_values(['ticker', 'timestamp'])
        
        if data_type == "Zwroty Procentowe (%)":
            df_qa['Metric'] = df_qa.groupby('ticker')['price_usd'].pct_change() * 100
            df_qa = df_qa.dropna(subset=['Metric'])
            y_axis_label = "Zmiana procentowa (%)"
        else:
            df_qa['Metric'] = df_qa['price_usd']
            y_axis_label = "Cena (USD)"

        if outlier_cutoff > 0:
            lower_bound = outlier_cutoff / 100.0
            upper_bound = 1.0 - lower_bound
            
            filtered_dfs = []
            for ticker in selected_tickers:
                t_df = df_qa[df_qa['ticker'] == ticker]
                if not t_df.empty:
                    q_low = t_df['Metric'].quantile(lower_bound)
                    q_high = t_df['Metric'].quantile(upper_bound)
                    t_filtered = t_df[(t_df['Metric'] >= q_low) & (t_df['Metric'] <= q_high)]
                    filtered_dfs.append(t_filtered)
            df_qa = pd.concat(filtered_dfs) if filtered_dfs else pd.DataFrame()

    if df_qa.empty:
        st.info("Brak danych po nałożeniu filtrów.")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Rozkład zmienności (Box Plot)")
            st.markdown("Środek pudełka to mediana. Długość 'wąsów' to miara rozrzutu i ryzyka.")
            fig_box = px.box(df_qa, x="ticker", y="Metric", color="ticker", 
                             labels={"Metric": y_axis_label, "ticker": "Aktywo"})
            st.plotly_chart(fig_box, use_container_width=True)
            
        with col2:
            st.subheader("Częstotliwość występowania (Histogram)")
            st.markdown("Pokazuje, jakie wartości metryki zdarzały się najczęściej w badanej próbce.")
            fig_hist = px.histogram(df_qa, x="Metric", color="ticker", barmode="overlay", nbins=40,
                                    labels={"Metric": y_axis_label, "count": "Liczba próbek"})
            st.plotly_chart(fig_hist, use_container_width=True)

        st.markdown("---")
        st.subheader("Tablica statystyk opisowych dla wybranej metryki")
        
        stats_data = []
        for ticker in selected_tickers:
            t_df = df_qa[df_qa['ticker'] == ticker]['Metric']
            if not t_df.empty:
                stats_data.append({
                    "Kryptowaluta": ticker,
                    "Liczba próbek": t_df.count(),
                    "Średnia": f"{t_df.mean():.4f}",
                    "Mediana": f"{t_df.median():.4f}",
                    "Min": f"{t_df.min():.4f}",
                    "Max": f"{t_df.max():.4f}",
                    "Odchylenie Std.": f"{t_df.std():.4f}",
                    "Skew": f"{t_df.skew():.4f}"
                })
                
        if stats_data:
            st.dataframe(pd.DataFrame(stats_data), use_container_width=True)