import sqlite3
import datetime
from pathlib import Path
import config
from src.utils import llm
from src.utils.logger import get_logger
from src.database.db import get_connection

log = get_logger("brain.sleep_cycle")

def distill_context():
    """
    Implements OPCD (On-Policy Context Distillation).
    Summarizes recent raw transcripts into high-density semantic weights.
    """
    log.info("initiating_sleep_cycle_distillation")
    try:
        conn = get_connection()
        # Fetch transcripts added in the last 7 days
        seven_days_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
        
        # We find files that are transcripts and have been processed recently
        rows = conn.execute("""
            SELECT file_path FROM files 
            WHERE content_class = 'SELLER_CORRESPONDENCE' 
            AND status = 'PROCESSED'
            AND discovered_at > ?
        """, (seven_days_ago,)).fetchall()
        
        if not rows:
            log.info("no_new_transcripts_to_distill")
            conn.close()
            return
            
        combined_text = ""
        for row in rows:
            path = Path(row[0])
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    # Take only the first 5000 chars of each to fit in context window
                    combined_text += f"\n--- Transcript: {path.name} ---\n{f.read()[:5000]}"
                    
        if not combined_text.strip():
            conn.close()
            return

        # 2. Distill using Llama 4 Scout (High Context)
        prompt = f"""
        You are a Real Estate Strategy AI undergoing 'Sleep Cycle' memory consolidation.
        Analyze the following raw meeting transcripts from the past week.
        Distill the core strategic lessons, 'Transaction Engineering' ideas, and negotiation tactics discussed by the Principal Broker.
        Output a highly dense, bulleted 'Doctrine Distillation' document. Do not include conversational filler.
        
        Raw Memory:
        {combined_text}
        """
        
        log.info("calling_nemotron_super_for_distillation")
        distilled_knowledge = llm.complete(
            prompt=prompt,
            tier="quality",
            agent="scribe" # Re-using Nemotron Super 120B mapped here
        )
        
        # 3. Save as a 'Golden Rule' chunk
        out_name = f"DISTILLED_DOCTRINE_{datetime.date.today().isoformat()}.md"
        out_path = config.KNOWLEDGE_DIR / "reference" / out_name
        
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(distilled_knowledge)
            
        log.info("sleep_cycle_complete", output=str(out_path))
        conn.close()
        
    except Exception as e:
        log.error("sleep_cycle_failed", error=str(e))

if __name__ == "__main__":
    distill_context()