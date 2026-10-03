# Fair Drop Simulator Dashboard

## Quick Start
1. Generate data: `python3 -m Dhanya_Sim.runner.engine --generate-demo-assets --mock-mode`
2. Serve: `cd Dhanya_Sim/ui && python3 -m http.server 8080`
3. Open: http://localhost:8080

## Files
- `index.html` — single page dashboard
- `style.css` — sketch/notebook theme
- `app.js` — fetches `../output/dashboard_feed.json` and renders

## Data Source
Reads `../output/dashboard_feed.json`. Regenerate anytime with the engine.
