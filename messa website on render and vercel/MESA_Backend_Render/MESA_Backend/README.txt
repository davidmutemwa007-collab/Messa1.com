MESA BACKEND — LOCAL AND PRODUCTION
===================================

Local Windows use:
- Keep MESA_Frontend and MESA_Backend beside each other as in the original package.
- Run start.bat / start.ps1.
- Local SQLite database and secret are stored in data/.

Production deployment:
- Use DEPLOY-RENDER.md and render.yaml to deploy this Python HTTP server to Render.
- Deploy MESA_Frontend separately to Vercel using its DEPLOY-VERCEL.md.
- Set MESA_ALLOWED_ORIGINS to the exact Vercel origin.
- Set the frontend API URL in static/js/api-config.js.
- Render must have a persistent disk because this version uses SQLite.

The server is a standard-library HTTP server. It is not a Flask or FastAPI app export, which is why Vercel's Python function detection fails.
