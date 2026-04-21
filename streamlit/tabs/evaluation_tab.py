import streamlit as st
import plotly.graph_objects as go

def render_evaluation_tab(filtered, model, scaler, feature_cols):
    st.markdown("### Model Comparison in Selected Period")

    eval_df = filtered.copy()
    X_eval = scaler.transform(eval_df[feature_cols])
    eval_df["pred_up"] = model.predict(X_eval)
    eval_df["actual_up"] = eval_df["target_up"]
    eval_df["correct"] = (eval_df["pred_up"] == eval_df["actual_up"]).astype(int)

    accuracy = eval_df["correct"].mean()
    total_preds = len(eval_df)
    total_up_pred = int(eval_df["pred_up"].sum())
    total_down_pred = int((eval_df["pred_up"] == 0).sum())

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Window Accuracy", f"{accuracy:.2%}")
    with m2:
        st.metric("Total Predictions", total_preds)
    with m3:
        st.metric("Predicted UP", total_up_pred)
    with m4:
        st.metric("Predicted DOWN", total_down_pred)

    st.markdown("### Actual vs Predicted Direction")

    compare_fig = go.Figure()

    compare_fig.add_trace(go.Scatter(
        x=eval_df["trading_day"],
        y=eval_df["actual_up"],
        mode="lines+markers",
        name="Actual Direction",
        line=dict(width=3)
    ))

    compare_fig.add_trace(go.Scatter(
        x=eval_df["trading_day"],
        y=eval_df["pred_up"],
        mode="lines+markers",
        name="Predicted Direction",
        line=dict(width=2, dash="dash"),
        opacity=0.75
    ))

    compare_fig.update_layout(
        template="plotly_dark",
        xaxis_title="Date",
        yaxis_title="Direction (0 = Down, 1 = Up)",
        height=420,
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", y=1.02, x=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    compare_fig.update_yaxes(tickmode="array", tickvals=[0, 1])

    st.plotly_chart(compare_fig, use_container_width=True)

    st.markdown("### Prediction Correctness")

    correctness_fig = go.Figure()
    correctness_fig.add_trace(go.Bar(
        x=eval_df["trading_day"],
        y=eval_df["correct"],
        name="Correct Prediction"
    ))

    correctness_fig.update_layout(
        template="plotly_dark",
        xaxis_title="Date",
        yaxis_title="Correct (1 = Yes, 0 = No)",
        height=320,
        margin=dict(l=20, r=20, t=30, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    correctness_fig.update_yaxes(range=[0, 1.1])

    st.plotly_chart(correctness_fig, use_container_width=True)

    eval_df["actual_label"] = eval_df["actual_up"].map({0: "Down", 1: "Up"})
    eval_df["pred_label"] = eval_df["pred_up"].map({0: "Down", 1: "Up"})

    with st.expander("Show Detailed Comparison Table"):
        show_cols = ["trading_day", "price", "avg_sentiment", "actual_label", "pred_label", "correct"]
        st.dataframe(
            eval_df[show_cols].reset_index(drop=True),
            use_container_width=True
        )