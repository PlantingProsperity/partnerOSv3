import datetime
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from src.database.db import get_connection
from src.utils.logger import get_logger
from src.firehouse.sourcer import analyze_uncontacted_prospects
import config

log = get_logger("firehouse.scheduler")

def generate_morning_brief():
    """
    Generates the daily Morning Brief summarizing pipeline stats and AI Prospect picks.
    """
    log.info("generating_morning_brief")
    now = datetime.datetime.now(datetime.UTC)
    
    # 1. Pipeline Stats
    conn = get_connection()
    # Active deals are those without a final verdict
    active_deals = conn.execute("""
        SELECT COUNT(*) FROM deals 
        WHERE deal_id NOT IN (SELECT deal_id FROM verdicts)
    """).fetchone()[0]
    total_prospects = conn.execute("SELECT COUNT(*) FROM prospects").fetchone()[0]
    
    # 2. Token Budget Stats
    yesterday = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    token_usage = conn.execute(
        "SELECT pct_of_daily_budget FROM v_daily_token_usage WHERE date = ?", 
        (yesterday,)
    ).fetchone()
    budget_used = token_usage[0] if token_usage else 0.0
    conn.close()
    
    # 3. AI Prospect Sourcing
    report = analyze_uncontacted_prospects()
    
    # 4. Format Markdown
    md = f"# 🌅 Morning Brief — {now.strftime('%A, %B %d, %Y')}\n\n"
    
    md += "### 📊 System Health\n"
    md += f"- **Active Deals in Pipeline:** {active_deals}\n"
    md += f"- **Total Prospects:** {total_prospects}\n"
    md += f"- **Yesterday's Gemini Token Budget Used:** {budget_used}%\n\n"
    
    md += "### 🎯 AI Sourced Prospects (Top Picks)\n"
    if report and report.top_picks:
        for pick in report.top_picks:
            md += f"#### {pick.address} ({pick.owner_name})\n"
            md += f"- **Parcel:** `{pick.parcel_number}`\n"
            md += f"- **Pinneo Rationale:** {pick.reasoning}\n"
            md += f"- **Strategy:** {pick.suggested_strategy}\n\n"
    else:
        md += "*No new high-priority targets found today or API limit reached.*\n\n"
        
    md += "---\n*The OS handles the Firehouse. The principals handle Showtime.*\n"
    
    # Save to disk
    brief_path = config.DATA_DIR / "morning_brief.md"
    with open(brief_path, "w", encoding="utf-8") as f:
        f.write(md)
        
    log.info("morning_brief_generated", path=str(brief_path))

# Global scheduler instance
scheduler = BackgroundScheduler()

def start_firehouse():
    """
    Initializes and starts the APScheduler.
    """
    if not scheduler.running:
        # Schedule the Morning Brief for 7:00 AM every day
        scheduler.add_job(generate_morning_brief, 'cron', hour=7, minute=0, id='morning_brief_job')
        scheduler.start()
        log.info("firehouse_scheduler_started")
        
        # Optionally run immediately on startup for testing/dev purposes if the brief doesn't exist
        if not (config.DATA_DIR / "morning_brief.md").exists():
            log.info("no_morning_brief_found_running_immediately")
            scheduler.add_job(generate_morning_brief, next_run_time=datetime.datetime.now())

if __name__ == "__main__":
    # If run directly, just generate the brief immediately and exit.
    generate_morning_brief()