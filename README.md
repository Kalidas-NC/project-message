# WhatsApp Cloud API agent

FastAPI webhook for [WhatsApp Cloud API](https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started). Meta POSTs inbound messages to `/webhook`; a [Gemini](https://ai.google.dev/gemini-api/docs) call produces the reply; the server sends it through the Graph API. `/help` and `/status` stay local. Each other message is a fresh prompt (no chat history).

## Run

Copy `.env.example` to `.env` at the **repo root** (next to `README.md`). Settings always load that file, even if you start uvicorn from another directory.

```bash
cp .env.example .env
uv sync
uv run uvicorn project_message.app:app --reload --port 8765
```

| Variable | Role |
| --- | --- |
| `WHATSAPP_VERIFY_TOKEN` | String you invent. Meta GET handshake. |
| `WHATSAPP_APP_SECRET` | App settings → Basic. HMAC on POST. Leave empty to skip the check locally. |
| `WHATSAPP_ACCESS_TOKEN` | API Setup → Generate access token. Sending only. |
| `WHATSAPP_PHONE_NUMBER_ID` | API Setup, next to the test number. |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) key. Required for LLM replies. |
| `GEMINI_MODEL` | Optional. Defaults to `gemini-3.6-flash`. |

## Try locally (no Meta)

Handshake:

```bash
curl -s "http://127.0.0.1:8765/webhook?hub.mode=subscribe&hub.verify_token=change-me&hub.challenge=1158201444"
```

Should print `1158201444`.

Inbound sample (`/help`):

```bash
curl -s -X POST http://127.0.0.1:8765/webhook \
  -H "Content-Type: application/json" \
  -d @samples/webhook_text.json
```

Server terminal prints `[server] received` / `[server] sending`. Without Graph credentials it does not send a WhatsApp message.

## Point Meta at this server

1. Create a WhatsApp use-case app: [Cloud API Get Started](https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started).
2. Tunnel port 8765 (ngrok or cloudflared). Meta needs public HTTPS; self-signed certs are rejected.
3. Dashboard → Use cases → Customize → Configuration. Callback URL `https://<tunnel>/webhook`, verify token matching `.env`. Subscribe to `messages`.
4. Add your personal number as a Meta test recipient, then text the test number `/help`.

If Meta shows the inbound JSON in the dashboard but uvicorn never logs `POST /webhook`, the WhatsApp Business account is not subscribed to **your** app. Handshake only proves the URL; `subscribed_apps` is what routes live events to that app’s callback.

Load `.env`, then replace `WABA_ID` with the WhatsApp Business account ID (API Setup, or `entry[].id` on a sample payload).

**List apps already subscribed** (GET). You should see your app name (for example `nc-test`). Meta’s debugger app **WA DevX Webhook Events 1P App** may also appear; that is normal and does not replace yours.

```bash
cd ~/code/personal/project-message
set -a && source .env && set +a

curl -sS "https://graph.facebook.com/v23.0/WABA_ID/subscribed_apps" \
  -H "Authorization: Bearer $WHATSAPP_ACCESS_TOKEN"
```

**Subscribe this app** (POST). Uses the app that owns `WHATSAPP_ACCESS_TOKEN`. It does not send a WhatsApp message and does not call FastAPI; it only tells Meta to POST future inbound events to your Callback URL. Safe to run again; `{ "success": true }` means it worked.

```bash
curl -sS -X POST "https://graph.facebook.com/v23.0/WABA_ID/subscribed_apps" \
  -H "Authorization: Bearer $WHATSAPP_ACCESS_TOKEN"
```

Send another text from your phone. The server terminal should show `POST /webhook` then `[server] received`.
