# Fair Drop — Adversarial Simulation Module

**Owner:** Dhanya  
**Scope:** AI / Adversarial Simulation Testing  

## Overview
This module is the adversarial simulation testing harness for the **Fair Drop** event registration and limited-seat allocation system (500 seats / 50,000 participants).

## Key Principles & Boundaries
- **HTTP API Only:** The simulator interacts with the Fair Drop system strictly via documented HTTP endpoints (`/api/campaigns/...`, `/api/entitlements/...`, `/api/challenges/...`).
- **No Backend Internals:** It never imports backend Python modules, database models, or FastAPI internals, and does not directly connect to PostgreSQL.
- **Reproducible Evidence:** Uses deterministic seeds and scenario configurations to evaluate fairness invariants, request outcomes, latency percentiles, error rates, and inventory integrity under normal and abusive traffic patterns.
