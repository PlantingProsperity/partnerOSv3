# macOS 2026 "Tahoe" High-Contrast Dark Mode Styles
import streamlit as st

CSS = """
<style>
    /* 1. ROOT VARIABLES */
    :root {
        --mac-bg: #000000;
        --mac-glass: rgba(28, 28, 30, 0.7);
        --mac-border: 1px solid rgba(255, 255, 255, 0.15);
        --mac-text: #ffffff;
        --mac-sub: #a1a1a6;
        --mac-accent: #0a84ff;
        --mac-radius: 24px;
    }

    /* 2. MAIN APP CONTAINER */
    .stApp {
        background: var(--mac-bg);
        background-image: radial-gradient(circle at 50% -20%, #1c1c1e 0%, #000000 100%);
        color: var(--mac-text);
    }

    /* 3. SIDEBAR (THE DOCK) */
    [data-testid="stSidebar"] {
        background-color: var(--mac-glass);
        backdrop-filter: blur(50px);
        -webkit-backdrop-filter: blur(50px);
        border-right: var(--mac-border);
    }
/* 4. BENTO CARDS */
.bento-card {
    background: var(--mac-glass);
    backdrop-filter: blur(30px);
    -webkit-backdrop-filter: blur(30px);
    border: var(--mac-border);
    border-radius: var(--mac-radius);
    padding: 24px;
    margin-bottom: 20px;
    box-shadow: 0 12px 40px rgba(0,0,0,0.4); /* Deeper shadow for depth */
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.bento-card:hover {
    transform: translateY(-4px) scale(1.01);
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.3);
    box-shadow: 0 20px 60px rgba(0,0,0,0.6);
}

    /* 5. TYPOGRAPHY */
    h1, h2, h3 {
        color: var(--mac-text);
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif;
        font-weight: 700 !important;
        letter-spacing: -0.5px;
    }

    p, span, div {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif;
    }

    .mac-subtext {
        color: var(--mac-sub);
        font-size: 14px;
    }

    /* 6. AGENT STATUS BAR */
    .agent-bar {
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: var(--mac-glass);
        backdrop-filter: blur(20px);
        border: var(--mac-border);
        border-radius: 16px;
        padding: 10px 24px;
        display: flex;
        gap: 30px;
        z-index: 999;
    }

    .pulse {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #34c759;
        display: inline-block;
        margin-right: 8px;
        box-shadow: 0 0 8px #34c759;
    }

    /* 7. SCROLLBARS */
    ::-webkit-scrollbar {
        width: 8px;
    }
    ::-webkit-scrollbar-track {
        background: transparent;
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
    }
</style>
"""

def inject_mac_styles():
    st.markdown(CSS, unsafe_allow_html=True)
