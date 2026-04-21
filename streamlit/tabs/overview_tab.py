import streamlit as st
from charts import make_price_chart, make_sentiment_chart

def render_overview_tab(filtered, latest, prob_up, pred):
    st.markdown("### Historical Trends")
    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(make_price_chart(filtered, latest, prob_up), use_container_width=True)

    with col2:
        st.plotly_chart(make_sentiment_chart(filtered), use_container_width=True)

    st.markdown("### Prediction for Next Trading Day")
    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("Predicted Direction", "UP 📈" if pred == 1 else "DOWN 📉")

    with c2:
        st.metric("Probability of UP", f"{prob_up:.3f}")

    with c3:
        st.metric("Reference Date", str(latest["trading_day"].iloc[0].date()))