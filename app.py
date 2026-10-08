from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from src.solution import handle_request

ROOT = Path(__file__).resolve().parent
REQUESTS = json.loads((ROOT / "data" / "requests.json").read_text(encoding="utf-8"))
BY_ID = {r["request_id"]: r for r in REQUESTS}

st.set_page_config(
    page_title="Procurement Copilot",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.block-container {padding-top: 2rem; padding-bottom: 3rem;}
.hero {
    padding: 1.4rem 1.6rem;
    border: 1px solid #d9dee7;
    border-radius: 16px;
    background: linear-gradient(135deg, #f8fafc, #eef2ff);
    color: #111827;
}

.hero h1 {
    margin: 0 0 0.35rem 0;
    color: #111827 !important;
    font-size: 2rem;
    font-weight: 700;
}

.hero p {
    margin: 0;
    color: #4b5563 !important;
    font-size: 1rem;
}
.card {padding:1rem; border:1px solid #d9dee7; border-radius:14px; margin-bottom:.75rem; background:white;}
.risk {padding:.55rem .7rem; border-left:4px solid #dc2626; background:#fef2f2; border-radius:6px; margin:.3rem 0;}
.approval {padding:.55rem .7rem; border-left:4px solid #2563eb; background:#eff6ff; border-radius:6px; margin:.3rem 0;}
.missing {padding:.55rem .7rem; border-left:4px solid #d97706; background:#fffbeb; border-radius:6px; margin:.3rem 0;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>AI Procurement Request Copilot</h1>
  <p>Gather evidence → run deterministic policy checks → generate a recommendation → hand off to humans.</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Analysis")
    request_id = st.selectbox(
        "Purchase request",
        list(BY_ID.keys()),
        format_func=lambda rid: f"{rid} · {BY_ID[rid]['product_name']}",
    )
    architecture = st.radio(
        "Architecture",
        ["single", "staged"],
        format_func=lambda x: "A · Single agent" if x == "single" else "B · Staged / 2-agent",
    )
    st.caption("Architecture B adds an evidence analyst before the decision reviewer.")
    run = st.button("Run procurement analysis", type="primary", use_container_width=True)

req = BY_ID[request_id]

st.subheader("Request details")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Vendor", req["vendor_name"])
c2.metric("Annual cost", "Unknown" if req["annual_cost_usd"] is None else f"${req['annual_cost_usd']:,.0f}")
c3.metric("Users", "Unknown" if req["user_count"] is None else str(req["user_count"]))
c4.metric("Data access", str(req["data_access_level"]))

with st.expander("Business request", expanded=True):
    st.write(req["business_justification"])
    st.json({
        "product": req["product_name"],
        "category": req["category"],
        "integrations": req["requested_integrations"],
        "urgency": req["urgency"],
    })

if run:
    with st.spinner("Gathering evidence and running policy checks..."):
        try:
            result = handle_request(request_id, architecture=architecture)
        except Exception as exc:
            st.error("Analysis failed")
            st.exception(exc)
            st.stop()

    st.divider()
    st.subheader("Recommendation")
    st.success(result.recommendation)
    st.info(result.next_step)

    left, right = st.columns(2)
    with left:
        st.markdown("### Approvals required")
        if result.required_approvals:
            for item in result.required_approvals:
                st.markdown(f'<div class="approval">👤 {item}</div>', unsafe_allow_html=True)
        else:
            st.write("No threshold approval was determinable from the available request data.")

        st.markdown("### Missing information")
        if result.missing_information:
            for item in result.missing_information:
                st.markdown(f'<div class="missing">⚠️ {item}</div>', unsafe_allow_html=True)
        else:
            st.write("No required request information is missing.")

    with right:
        st.markdown("### Risk flags")
        if result.risk_flags:
            for item in result.risk_flags:
                st.markdown(f'<div class="risk">🚩 {item}</div>', unsafe_allow_html=True)
        else:
            st.write("No additional risk flags.")

        st.markdown("### Human control")
        if result.human_review_required:
            st.warning("Human review remains required. The copilot cannot purchase, approve spend, or override Security/Privacy/Legal.")

    st.markdown("### Evidence panel")
    for item in result.evidence:
        with st.container(border=True):
            st.markdown(f"**{item.source}**")
            st.write(item.finding)
            if item.reference:
                st.caption(f"Reference: {item.reference}")

    st.markdown("### Run telemetry")
    t1, t2, t3 = st.columns(3)
    t1.metric("LLM calls", result.telemetry.llm_calls if result.telemetry else "—")
    t2.metric("Tool calls", result.telemetry.tool_calls if result.telemetry else "—")
    t3.metric("Architecture", "Single" if architecture == "single" else "Staged / 2-agent")
else:
    st.divider()
    st.info("Choose a request and architecture, then click **Run procurement analysis**.")
    st.markdown("""
    **What this product deliberately keeps deterministic**
    - Required-field checks
    - Budget threshold checks
    - Approval thresholds
    - Security / privacy / legal triggers
    - Vendor evidence conflicts and outages
    - Human-review requirement

    **What Groq handles**
    - Interpreting business context
    - Summarizing evidence
    - Producing a concise recommendation narrative
    """)
