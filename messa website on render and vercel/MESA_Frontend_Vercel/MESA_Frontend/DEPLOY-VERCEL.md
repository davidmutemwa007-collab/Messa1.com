# MESA Website — Vercel deployment

1. Upload the contents of this folder to a GitHub repository (or set this folder as the Vercel Root Directory in a monorepo).
2. In Vercel, import the repository. Select **Other** as the framework preset if asked; no build command is required and the output is the project root.
3. After the Render API is deployed, edit `static/js/api-config.js` and replace `https://YOUR-RENDER-SERVICE.onrender.com` with the actual Render service origin. Commit and push the change.
4. Add the exact Vercel production origin to Render's `MESA_ALLOWED_ORIGINS` environment variable. Include any custom domain as a second comma-separated origin.
5. Redeploy the frontend. Test registration, login, menu loading, bookings, and order submission.

The frontend uses credentialed cross-origin requests. The API must allow the exact frontend origin and set secure `SameSite=None` cookies.
