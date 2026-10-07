# FindVision AI Android emergency alert companion

This companion listens to Android notifications, immediately displays the original missing-person alert in a heads-up notification and (when the user enables Android's draw-over-apps permission) a floating popup. It sends the alert text to the configured private API, creates a reference image, then updates the popup so the image appears below the original text. Tapping the Android notification opens the same text-above-image layout.

It does **not** read the SMS database and does not request `READ_SMS`. Android notification access is granted manually by the user. Android/OEM versions may not expose every cell-broadcast emergency alert as a notification, so automatic detection cannot be guaranteed on every phone. The companion currently filters for Korean missing-person terms to avoid generating people for weather and other unrelated alerts.

## What needs to be deployed

The Streamlit site cannot receive device SMS by itself. The Android companion talks to the FastAPI bridge in `mobile/api`; the bridge calls Cloudflare Workers AI using server-side credentials. Deploy the bridge as its own HTTPS service (the included Render blueprint is one option). Set these secrets in the hosting dashboard; never commit them:

- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_API_TOKEN` (AI inference permission only)
- `MOBILE_ACCESS_KEY` (a random, revocable team connection code at least 20 characters)

The Android settings screen needs the deployed HTTPS API URL and the team connection code. The service key is checked with constant-time comparison. Raw alert text is processed in memory and is not stored in the usage database; generated images are held in memory on the server and cached on the phone. The phone cache keeps the latest 24 generated images.

## Android setup

Open `mobile/android` in Android Studio and build/install the `app` debug variant. On the phone:

1. Enter the API HTTPS URL and the team connection code. Review the data-transfer notice and enable automatic analysis.
2. Enable **FindVision AI 재난문자 감지** under Android Notification access.
3. Enable **Display over other apps** for the original-message popup with the image underneath. If this permission is off, the app still posts a heads-up notification; tap it to open the full result.
4. Allow notifications. Keep the app installed and avoid force-stopping it.

## Local API development

From `mobile/`:

```sh
python -m venv .venv
python -m pip install -r api/requirements.txt
$env:CLOUDFLARE_ACCOUNT_ID = "..."
$env:CLOUDFLARE_API_TOKEN = "..."
$env:MOBILE_ACCESS_KEY = "..."
python -m uvicorn api.server:app --reload
```

Use HTTPS in real deployments. The local API protects each request with the team connection code and a same-origin check. It allows sparse alerts; absent appearance details remain illustrative and default to a Korean person, as configured for the product.

The Android app uses a high-priority notification and an explicitly user-enabled system overlay. Android may still delay or suppress the popup due to Do Not Disturb, notification settings, battery management, or an OEM that does not publish cell-broadcast messages to notification listeners. Full-screen takeover without user interaction is restricted by Android, so tapping the notification remains the fallback.
