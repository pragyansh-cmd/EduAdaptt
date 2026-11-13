EduAdapt — IBM Granite backend package

This package keeps your original EduAdapt interface and adds a Flask backend that calls IBM watsonx.ai Granite. It is not live until deployed and configured with your own IBM credentials and the correct watsonx region URL.

## Deploy on Render
1. Upload the contents of this folder to the root of a GitHub repository (the `index.html`, `backend/`, `render.yaml`, and README must be at repository root).
2. In Render, create a Blueprint from that GitHub repository.
3. In the Render service Environment settings, enter `IBM_API_KEY`, `IBM_PROJECT_ID`, and `IBM_URL` as secret/private values. Never put secrets in HTML or GitHub.#
4. `IBM_URL` must match the region shown by your watsonx.ai project. Example format: `https://us-south.ml.cloud.ibm.com` (this is only an example, not a guess about your project).
5. Deploy. Open the Render service URL. The same service serves the page and API.

## Important
- Keep the IBM API key private. If it was ever committed to GitHub or shared publicly, revoke it and create a new one.
- The model ID may need adjustment depending on models enabled in your watsonx.ai region/account.
- Check `/api/health` after deployment. `mode: live` means all three configuration values are present; it does not by itself prove a successful model inference. Test Adapt content to verify IBM inference.
