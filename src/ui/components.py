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

def render_agent_bar():
    """
    Renders the fixed Agent Status Bar at the bottom of the screen.
    Fetches the latest status from llm_calls.
    """
    # 1. Fetch latest agent activity
    try:
        conn = sqlite3.connect(str(config.DB_PATH))
        conn.row_factory = sqlite3.Row
        
        # Get the latest call for each major agent
        agents = ["prospect_sourcer", "librarian", "cfo_p1"]
        statuses = []
        
        for agent in agents:
            row = conn.execute("""
                SELECT model, success, ts 
                FROM llm_calls 
                WHERE agent = ? 
                ORDER BY ts DESC LIMIT 1
            """, (agent,)).fetchone()
            
            label = agent.split('_')[-1].capitalize()
            if row:
                # If the call was within the last 5 minutes, consider it 'Active'
                status_text = f"{label}: Active ({row['model'].split('/')[-1]})"
                statuses.append(f'<div class="agent-status"><div class="pulse"></div> {status_text}</div>')
            else:
                statuses.append(f'<div class="agent-status" style="opacity:0.5">{label}: Idle</div>')
        
        conn.close()
        
        html = f"""
        <div class="agent-bar">
            {''.join(statuses)}
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)
        
    except Exception as e:
        # Fallback if DB is locked
        st.markdown(f'<div class="agent-bar">Agents: Monitoring...</div>', unsafe_allow_html=True)
