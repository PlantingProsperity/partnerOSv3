# PartnerOS — Local Mandates & Operational Context

This file contains foundational mandates for all Gemini CLI sessions working within the `partner_os` repository. These instructions take absolute precedence over global defaults.

## 🏗️ Architectural Core
- **Hardware:** Intel i7-950 (No AVX). Ensure all PyTorch/ML operations are CPU-only.
- **Model Stack:** Strictly follow the Primary Deployments in `docs/NVIDIA_STRATEGY_2026.md`.
- **Database:** Single source of truth is `data/partner_os.db`. State persists in `data/checkpoints.sqlite`.

## 📜 Documentation Protocol (Contextual Isolation)
- **Local Audit Trail:** You MUST log all file creations, deletions, and structural changes to `./FILE_OPS_LOG.md` within this directory. 
- **DO NOT** attempt to write to the global `~/FILE_OPS_LOG.md`. That file belongs to a separate project.
- **Strategic History:** Record all significant technical decisions and Architectural Decision Records (ADRs) in `./BUILD_JOURNAL.md`.

## 🚀 Operational Workflow
- **Launcher:** Use `./launch.sh` to start the Streamlit dashboard and background Firehouse scheduler.
- **Testing:** Always run `pytest tests/ -v` before committing.
- **Security:** Never hardcode API keys. Use `os.getenv` and ensure `.env` is ignored by git.

---
*The OS handles the Firehouse. The principals handle Showtime.*
