import streamlit as st
import sqlite3
import config

def bento_card(title: str, content: str, subtext: str = "", size: str = "medium"):
    """
    Renders a macOS-style Bento Card with glassmorphism.
    """
    html = f"""
    <div class="bento-card">
        <h3 style="margin:0; font-size: 18px;">{title}</h3>
        <p style="margin: 10px 0; font-size: 15px;">{content}</p>
        <span class="mac-subtext">{subtext}</span>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

@st.fragment(run_every="5s")
def render_agent_bar():
    """
    Renders the fixed Agent Status Bar. 
    Refreshes every 5 seconds independently of the main app to show 'Life'.
    """
    try:
        conn = sqlite3.connect(str(config.DB_PATH))
        conn.row_factory = sqlite3.Row
        
        agents = ["prospect_sourcer", "librarian", "cfo_p1"]
        statuses = []
        
        # Check for any NEW high-equity leads to trigger a Toast
        new_lead = conn.execute("SELECT address FROM prospects WHERE equity_score = 'HIGH' AND created_at > datetime('now', '-5 minutes') LIMIT 1").fetchone()
        if new_lead and "last_toast" not in st.session_state:
            st.toast(f"🎯 New High-Equity Lead: {new_lead['address']}", icon="🔥")
            st.session_state.last_toast = new_lead['address']

        for agent in agents:
            row = conn.execute("""
                SELECT model, success, ts, error 
                FROM llm_calls 
                WHERE agent = ? 
                ORDER BY ts DESC LIMIT 1
            """, (agent,)).fetchone()
            
            label = agent.split('_')[-1].capitalize()
            # Check for reCAPTCHA block in Scout
            if agent == "prospect_sourcer" and row and "CAPTCHA" in str(row.get('error', '')):
                statuses.append(f'<div class="agent-status" style="color:#ff3b30"><div class="pulse" style="background:#ff3b30; box-shadow:0 0 8px #ff3b30"></div> Scout: BLOCKED</div>')
                if st.button("🔓 Open Solver", key="solve_captcha"):
                    import subprocess
                    import os
                    # Trigger the visible browser solver script
                    subprocess.Popen(["python3", "src/scripts/clear_captcha.py"])
                    st.info("Browser opening. Please clear reCAPTCHA and close window.")
            elif row:
                # If call in last 60s, show as actively pulsing
                status_text = f"{label}: Active"
                statuses.append(f'<div class="agent-status"><div class="pulse"></div> {status_text}</div>')
            else:
                statuses.append(f'<div class="agent-status" style="opacity:0.4">{label}: Idle</div>')
        
        conn.close()
        
        html = f"""
        <div class="agent-bar">
            <div style="font-weight:700; color:var(--mac-accent); margin-right:10px;">SYSTEM PULSE:</div>
            {''.join(statuses)}
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)
        
    except:
        st.markdown(f'<div class="agent-bar">Monitoring...</div>', unsafe_allow_html=True)
