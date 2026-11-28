# DMRoot Instagram Integration: How It Works

A plain-language guide. Read the first two sections to understand the whole system; use the rest as a reference.

---

## 1. What this does (30 seconds)

DMRoot needs to do two things with Instagram:

1. **Connect** a customer's Instagram account to their workspace (login with Meta).
2. **Listen** to what happens on that account (new comments, new DMs) and hand each event to the automation engine, so it can send a DM back.

This code covers connecting and listening. The automation engine and the "send DM" task come next.

```
Customer's Instagram  <---- Meta ---->  DMRoot API  ---->  Redis queue  ---->  Worker  ---->  Automation engine (later)
                                            |                                     |
                                        PostgreSQL <------------------------------+
```

---

## 2. The three main flows

### A. Connecting an account

```
1. Admin clicks "Connect Instagram" in the frontend
2. Frontend  -> GET /connected-accounts/instagram/authorize
   API       -> makes a one-time "state" (saved in Redis for 10 min), returns a Meta login URL
3. Browser goes to Meta, the customer approves
4. Meta sends the browser back to  /connected-accounts/instagram/callback?code=...&state=...
5. API:  uses the state to know WHO is connecting (the callback has no login token)
         exchanges the code for an access token (server-side only)
         saves the account + encrypted token
         subscribes the account to webhooks (so Meta starts sending us its events)
6. API redirects the browser to the frontend with the result:  ?status=success
```

Why the **state**? It is a random one-time ticket. It proves the callback belongs to a login we started, tells us which user and workspace it was, and cannot be reused (it is deleted the moment it is read).

Why **save first, subscribe second**? If subscribing fails, we mark the account `disconnected` again. Nothing is left half-connected.

### B. Receiving events (webhooks)

```
Meta -> POST /webhooks/instagram
  1. Check the signature (proves it really came from Meta)
  2. Split the payload into single events (one per comment or message)
  3. Find which workspace owns the account (only ACTIVE accounts)
  4. Save each event in webhook_events (duplicates are ignored)
  5. Put one job per new event on the "webhooks" queue
  6. Answer 200 immediately
Worker picks up the job:
  7. Claim the event (only one worker can)
  8. Skip it if the account was disconnected, or it is our own comment/echo
  9. Hand it to dispatch_inbound_event()  <- the automation engine plugs in here
 10. Mark it processed
```

The endpoint must answer fast. Meta stops sending to apps that keep failing, so all real work happens in the worker.

### C. Keeping tokens alive

| Login setup | Token | What we do |
|---|---|---|
| Instagram Login | Lasts 60 days | Refresh it automatically once it is within 10 days of expiry (and at least 24h old) |
| Unified Login | Lifetime depends on your Meta config | Cannot refresh; when it expires the account becomes `expired` and the customer reconnects |

If Meta says a token is invalid (error 190), the account is marked `expired` right away.

---

## 3. Folder map

```
app/
  integrations/                  <- talks to the outside world (no business rules)
    events.py                    InboundEvent: one common shape for any platform's event
    meta/
      meta_constants.py          ALL tunable numbers: limits, scopes, windows, error codes
      errors.py                  Typed Meta errors (token invalid, rate limited, window closed, ...)
      signature.py               Webhook signature + signed_request checks
      http.py                    One shared HTTP client for Meta
    instagram/
      oauth.py                   The two login setups (Unified and Instagram Login)
      client.py                  Subscribe, unsubscribe, send private reply / message, refresh token
      rate_limiter.py            Redis limiter per account (e.g. 750 private replies per hour)
      webhook_parser.py          Raw Instagram payload -> InboundEvent
  modules/
    connected_accounts/
      oauth_router.py            /authorize and /callback endpoints
      oauth_service.py           The connect workflow + disconnect with unsubscribe
      token_service.py           Token refresh and expiry
      integration_repository.py  Raw SQL for the above
      bridge.py                  The ONLY file that calls your Phase 5 service
    webhooks/
      router.py                  Webhook + Meta compliance endpoints
      service.py                 Receive flow, deauthorize, data deletion
      processing.py              Handles one stored event (claim, retry, dead-letter)
      dispatcher.py              Hand-off to the automation engine
      maintenance.py             Requeue stuck events, purge old ones
      repository.py              Raw SQL for webhook tables
  workers/
    celery_app.py                Celery config + schedule
    runtime.py                   Lets sync Celery tasks run our async code safely
    tasks/                       Thin task wrappers (webhook_tasks.py, token_tasks.py)
database/migrations/             3 new migrations (see section 6)
docs/                            Setup checklist, production list, pending tests
```

Rule of thumb: **routers** handle HTTP, **services** hold the logic, **repositories** hold SQL, **integrations** talk to Meta, **tasks** only call services.

---

## 4. Endpoints

| Method | Path (under `/api/v1`) | Who calls it | Auth |
|---|---|---|---|
| GET | `/connected-accounts/instagram/authorize` | Frontend | Admin JWT |
| GET | `/connected-accounts/instagram/callback` | Meta (browser redirect) | None (uses state) |
| GET | `/webhooks/instagram` | Meta, once, to verify the URL | Verify token |
| POST | `/webhooks/instagram` | Meta, for every event | Signature |
| POST | `/webhooks/meta/deauthorize` | Meta, when the user removes the app | signed_request |
| POST | `/webhooks/meta/data-deletion` | Meta, when the user asks for deletion | signed_request |
| GET | `/webhooks/meta/data-deletion/status/{code}` | The user | Unguessable code |

The callback redirects to the frontend with `status` (`success`, `partial`, `error`) and, on problems, a `reason`:
`invalid_state`, `access_denied`, `missing_permissions`, `no_instagram_accounts`, `exchange_failed`, `account_in_use`, `store_failed`, `webhook_subscription_failed`.

---

## 5. Safety ideas used everywhere

| Idea | How it is done |
|---|---|
| **No duplicate processing** | `webhook_events` has a unique key per event; workers must "claim" an event before handling it |
| **Nothing lost** | Event is saved before queueing; a sweeper requeues anything never queued or whose retry was lost |
| **Retries that stop** | Up to 5 attempts with growing delays, then status `dead` and an ERROR log |
| **Tenant isolation** | Every query filters by organization. The one exception is the webhook lookup "which workspace owns this Instagram account?", and it only matches active accounts |
| **Secrets protected** | Tokens are encrypted at rest, decrypted only in memory, sent in headers, never logged. Secrets live in `.env` |
| **Customer data protected** | Comment and message text is kept out of logs and `repr`; stored events are purged after 30 days and deleted on deletion requests |
| **Meta limits respected** | Redis limiter keeps us at 90% of Meta's limits and backs off when Meta reports high usage |

---

## 6. Database

| Table | Purpose |
|---|---|
| `connected_accounts` (extended) | Added: `auth_flow`, `token_type`, `external_business_id`, `granted_permissions`, `token_issued_at`, `webhook_subscribed_at`; `token_expires_at` may now be empty |
| `webhook_events` | Every received event, its status (`received`, `processing`, `processed`, `skipped`, `failed`, `dead`), attempts, last error. Built for other platforms too |
| `data_deletion_requests` | Meta deletion requests and their outcome |

Apply the three `XXXX_` migrations in this order: connected_accounts additions, webhook_events, data_deletion_requests. Rename `XXXX` to your next numbers first.

---

## 7. Configuration (`.env`)

| Variable | Needed for |
|---|---|
| `META_ENABLED_LOGIN_SETUPS` | `unified`, `instagram_login`, or both (comma-separated) |
| `META_APP_ID`, `META_APP_SECRET` | Unified Login, and possibly webhook signatures |
| `META_UNIFIED_LOGIN_CONFIG_ID` | Unified Login |
| `INSTAGRAM_APP_ID`, `INSTAGRAM_APP_SECRET` | Instagram Login, and possibly webhook signatures |
| `META_WEBHOOK_VERIFY_TOKEN` | Meta verifying your webhook URL |
| `META_OAUTH_REDIRECT_URI` | Must match the dashboard exactly (HTTPS in production) |
| `META_API_VERSION` | e.g. `v27.0` |
| `FRONTEND_CONNECT_RESULT_URL` | Where the browser lands after connecting |
| `PUBLIC_API_BASE_URL` | Your public HTTPS URL (the tunnel in development) |
| `TOKEN_ENCRYPTION_KEYS`, `SECRET_KEY` | Already in use; the encryption key must differ from `SECRET_KEY` |

In development the app starts without Meta values. In production it refuses to start if an enabled login setup is missing something.

**To change a limit, window, scope or retry setting, edit `app/integrations/meta/meta_constants.py`.** Nothing else.

---

## 8. Running it

```bash
# API (your usual command), then:
celery -A app.workers.celery_app worker -Q webhooks,default -l info
celery -A app.workers.celery_app beat -l info     # only ONE Beat instance
```

Windows without Docker: add `-P solo` to the worker. Redis must be 6.2 or newer.

Scheduled jobs:

| Job | When |
|---|---|
| Requeue stuck events | Every 2 minutes |
| Refresh Instagram Login tokens | Every 6 hours |
| Expire overdue tokens | Hourly |
| Purge old events | Daily, 03:30 UTC |

---

## 9. First-time setup order

1. Follow `meta-app-setup-checklist.md` (Meta app, test accounts, HTTPS tunnel).
2. Fill the `ADAPT` lines (section 10), run the migrations, wire the routers.
3. Start API, worker, Beat.
4. Call `/authorize` as an admin and open the URL it returns.
5. Approve with your test account, and check you land on the frontend with `status=success`.
6. In the dashboard, verify the webhook URL, then comment from a second test account and watch `webhook_events`.

---

## 10. Things you must adapt (I could not see your code)

Search the project for `ADAPT`:

| File | What to check |
|---|---|
| `connected_accounts/bridge.py` | Signatures of `upsert_connection`, `mark_expired`, `disconnect_account` |
| `connected_accounts/integration_repository.py` | `_TOKEN` = your encrypted-token column name |
| `oauth_service.py`, `rate_limiter.py` | `get_redis` import |
| `workers/runtime.py` | Your DB and Redis init/close function names |
| `oauth_router.py` | `require_admin` and `CurrentUser` import |

Also: call `oauth_service.disconnect_with_unsubscribe(...)` from the existing disconnect endpoint, and call `close_http_client()` on shutdown.

---

## 11. Troubleshooting

| Symptom | Likely cause |
|---|---|
| Webhook verification fails (403) | `META_WEBHOOK_VERIFY_TOKEN` differs from the dashboard, or the tunnel URL changed |
| Events rejected with 403 | Signature secret mismatch; check both app secrets are set |
| No real events arrive in dev | App may need to be Live, or comment events may need Advanced Access; dashboard Test events still work |
| Events stay `received` | Worker is not running or not listening on the `webhooks` queue (the sweeper requeues after 2 minutes) |
| Events end as `dead` | Handler keeps failing; read `last_error`, fix, then requeue |
| Connect ends with `webhook_subscription_failed` | Permission missing, or account not a professional account |
| Connect ends with `account_in_use` | Another workspace already has this account connected |
| Account suddenly `expired` | Token invalid or past expiry; customer must reconnect |
| App will not start in production | A setting for an enabled login setup is missing; the error names the variable |

---

## 12. Not built yet

- The automation engine and templates (comment-to-DM first, then more templates and custom automations). It registers with `dispatcher.register_event_handler(...)`.
- The outgoing-message task. The client and rate limiter are ready for it.
- Automated tests (see `instagram-testing-pending.md`).
- Production items (see `meta-production-requirements.md`).

## 13. Still to confirm during development

- The account ID we store matches the webhook account ID.
- Which app secret signs Instagram webhooks.
- Details of Unified Login responses and the unsubscribe call.
- Meta's usage header names and the real message length limit.

---

## 14. Glossary

- **Webhook**: Meta calling our URL when something happens.
- **OAuth / state / code**: the login handshake; the state is our one-time ticket, the code is Meta's one-time ticket.
- **Private reply**: a DM sent in response to a comment (one per comment, within 7 days).
- **Messaging window**: 24 hours after a customer messages us, during which we can message them.
- **Idempotent**: safe to run twice with the same result.
- **Dead letter**: an event we gave up on and parked for a human to look at.
- **Dev mode**: Meta app limited to people with a role on it (admins, developers, testers).