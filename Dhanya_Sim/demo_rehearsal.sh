#!/bin/bash
set -e

# Change to workspace directory if not already there
cd "$(dirname "$0")/.."

# Prefer python3 in virtualenv if present
if [ -f "Dhanya_Sim/.venv/bin/python" ]; then
  PYTHON="Dhanya_Sim/.venv/bin/python"
else
  PYTHON="python3"
fi

echo "🎬 Fair Drop Simulator — Full Demo Rehearsal"
echo "============================================="

# Step 1: Dry run validation
echo "[1/5] Validating configs and profiles..."
$PYTHON -m Dhanya_Sim.runner.engine --dry-run

# Step 2: Run full test suite in mock mode
echo "[2/5] Running 15-scenario automated test suite..."
$PYTHON tests/simulation/test_adversarial_suite.py

# Step 3: Generate demo assets
echo "[3/5] Generating demo assets (dashboard feed, attack report, raw CSV)..."
$PYTHON -m Dhanya_Sim.runner.engine --generate-demo-assets --mock-mode

# Step 4: Verify outputs
echo "[4/5] Verifying output artifacts..."
test -f Dhanya_Sim/output/dashboard_feed.json && echo "  ✅ dashboard_feed.json"
test -f Dhanya_Sim/output/attack_report.md && echo "  ✅ attack_report.md"
test -f Dhanya_Sim/output/raw_metrics.csv && echo "  ✅ raw_metrics.csv"

# Step 5: Print judge-ready summary
echo "[5/5] Demo rehearsal complete."
echo ""
echo "📊 Dashboard feed for Rohan: Dhanya_Sim/output/dashboard_feed.json"
echo "📝 Attack report for judges: Dhanya_Sim/output/attack_report.md"
echo "📈 Raw metrics for audit:    Dhanya_Sim/output/raw_metrics.csv"
echo ""
echo "✅ Simulator ready for midnight demo."
