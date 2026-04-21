import streamlit as st

def apply_custom_style():
    st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1400px;
        }

        .metric-card {
            background: linear-gradient(180deg, rgba(22,27,34,0.95), rgba(13,17,23,0.95));
            border: 1px solid rgba(255,255,255,0.08);
            padding: 18px 20px;
            border-radius: 16px;
            box-shadow: 0 6px 20px rgba(0,0,0,0.18);
        }

        .section-title {
            font-size: 1.15rem;
            font-weight: 700;
            margin-bottom: 0.3rem;
        }

        .section-subtle {
            color: #9AA4B2;
            font-size: 0.95rem;
            margin-bottom: 1rem;
        }

        div[data-testid="stMetric"] {
            background: linear-gradient(180deg, rgba(22,27,34,0.95), rgba(13,17,23,0.95));
            border: 1px solid rgba(255,255,255,0.08);
            padding: 16px;
            border-radius: 16px;
        }

        div[data-testid="stDataFrame"] {
            border-radius: 16px;
            overflow: hidden;
        }
    </style>
    """, unsafe_allow_html=True)