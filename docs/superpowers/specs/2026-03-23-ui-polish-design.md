# Design Spec: PartnerOS macOS "Liquid Glass" Command Center

**Date:** 2026-03-23
**Status:** Approved
**Aesthetic:** macOS 2026 "Tahoe" High-Contrast Dark Mode

---

## 1. Vision & Personality
PartnerOS is an autonomous digital back-office. The UI must transition from a passive "Dashboard" to an active "Command Center" where the Fasahov brothers (Roman & Daniil) act as Principals leading an elite AI staff.

*   **The Unified Manager:** All communication occurs through a single entity—The Manager. It represents the "Third Partner" who synthesizes deal-level facts with global Pinneo doctrine and market context.
*   **Ambient Intelligence:** Global market data and doctrine citations are woven into deal-specific conversations without requiring context switching.

## 2. Visual Language (macOS "Tahoe" Style)
*   **Theme:** High-Contrast Dark Mode.
*   **Materials:** Obsidian Glass (`rgba(28, 28, 30, 0.7)`) with `backdrop-filter: blur(50px)`.
*   **Typography:** Apple System Fonts (SF Pro Display, SF Pro Text).
*   **Layout:** Bento Grid modules with 24px corner radii.
*   **Accents:** macOS System Blue (`#0a84ff`) for primary actions and status indicators.

## 3. Core Architecture: The Triple-Pane Workspace
The interface is split into three functional vertical zones to ensure context isolation and productivity.

### Pane 1: The Dock (240px)
*   **Global Navigation:** "Morning Brief" (Synthesis) and "Command Center" (Agent Monitor).
*   **The Deal List:** Dynamic list of active pursuits. Clicking a deal switches the context of Panes 2 and 3.

### Pane 2: The Mentor (380px)
*   **Unified Chat:** A persistent messaging interface with the Manager.
*   **Thought Disclosure:** Uses collapsible "Thinking" tags to show internal logic (Lease parsing, Zoning lookup, Doctrine alignment).
*   **Course Correction:** Supports natural language redlining ("Increase the interest rate to 5.5%").

### Pane 3: The Stage (Fluid)
*   **Top (The Forensics):** Bento cards showing CFO-extracted metrics (DSCR, Cap Rate) with source citations.
*   **Middle (The Vault):** A glass container for deal-specific files (PDFs, Transcripts, Audio).
*   **Bottom (The Draft):** A live editor for LOIs and Bird Letters that updates as the conversation in Pane 2 progresses.

## 4. Page Specifications

### Page 1: The Morning Brief
The landing experience for the partners.
*   **Priority Leads Bento:** High-equity targets found by background agents.
*   **Agent Activity Bar:** Translucent tray showing live status of the "Autonomic System" (e.g., *CFO is Underwriting...*).
*   **Doctrine Nudge:** A "Thought of the Day" or strategic reminder from the Pinneo Brain.

### Page 2: The Workspace
The active deal analysis view using the Triple-Pane architecture.

## 5. Technical Requirements (Streamlit)
*   **Custom CSS:** Injection of `src/ui/styles.py` for glassmorphism and bento grids.
*   **State Management:** Unified `st.session_state` for deal context and thread isolation.
*   **Component Hardening:** High-contrast text rendering to solve legibility issues.

---
*Fasahov Bros. Brokerage • March 2026*
