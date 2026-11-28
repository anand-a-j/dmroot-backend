# Build Guide: Write It Yourself, In This Order

Rule: write things that depend on nothing first, then build upward. After every step, run the small check before moving on.
Keep the delivered files open on the side and read them; type your own version.

---

## Phase 1: Building blocks (no database, no Meta needed)

| # | File | Write this | Check |
|---|---|---|---|
| 1 | `integrations/meta/meta_constants.py` | Names and numbers only: URLs, scopes, 7-day and 24-hour windows, rate limits, error codes, retry settings | `import` it without errors |
| 2 | `core/config.py` | Add the Meta settings, a startup check, and `enabled_login_setups` | App starts; wrong `META_API_VERSION` fails |
| 3 | `integrations/meta/errors.py` | One error class per case (token invalid, rate limit, window closed...) and `build_error()` that maps a Meta response to one | Feed it fake `{"error": {"code": 190}}` bodies |
| 4 | `integrations/meta/signature.py` | `verify_signature()`: HMAC-SHA256 of the raw body, constant-time compare | Sign a string yourself, expect True; change one character, expect False |
| 5 | `integrations/events.py` | The `InboundEvent` dataclass | Create one by hand |
| 6 | `integrations/instagram/webhook_parser.py` | `split_instagram_payload()` then `to_inbound_event()` | Paste a sample payload: 1 comment gives 1 event; your own comment gives `None` |

## Phase 2: Database

| # | File | Write this | Check |
|---|---|---|---|
| 7 | 3 migrations | Extra columns on `connected_accounts`, then `webhook_events`, then `data_deletion_requests` | Run them; inspect the tables |
| 8 | `webhooks/repository.py` | `find_active_account`, `insert_event`, `claim_for_processing`, `set_outcome` | Insert the same event twice: second returns `None` |
| 9 | `connected_accounts/integration_repository.py` | Update auth details, force disconnect, list tokens due for refresh | Run each query in psql with a test row |

## Phase 3: Connect an Instagram account

| # | File | Write this | Check |
|---|---|---|---|
| 10 | `integrations/meta/http.py` | One shared HTTP client, one `graph_request()` that turns errors into your typed errors | Call any Graph URL with a bad token; expect your auth error |
| 11 | `integrations/instagram/oauth.py` | Two classes with the same two methods: build the login URL, exchange the code | Print the login URL; open it in a browser |
| 12 | `integrations/instagram/client.py` | `subscribe_webhooks`, `send_private_reply`, `send_message`, `refresh_token` | Subscribe your test account |
| 13 | `connected_accounts/bridge.py` | 3 small functions calling your existing Phase 5 service | Call `store_connection` with fake data |
| 14 | `connected_accounts/oauth_service.py` | `start_connect` (save one-time state in Redis) and `complete_connect` (read state once, exchange code, save, subscribe, roll back on failure) | Run the connect flow once |
| 15 | `connected_accounts/oauth_router.py` | `/authorize` (admin) and `/callback` (redirect to frontend) | **Milestone: account shows as connected** |

## Phase 4: Receive events

| # | File | Write this | Check |
|---|---|---|---|
| 16 | `workers/celery_app.py` | Celery app, `webhooks` queue, schedule | Worker starts |
| 17 | `workers/runtime.py` | One event loop per worker process; `run_async()` | Run a trivial async task |
| 18 | `webhooks/dispatcher.py` | A handler list and `dispatch_inbound_event()` that only logs | Call it with a fake event |
| 19 | `webhooks/processing.py` | Claim, skip if inactive or own activity, dispatch, record outcome, retry or dead-letter | Run one stored event by hand |
| 20 | `workers/tasks/webhook_tasks.py` | A task that calls `process_event` with backoff retries | Queue one job; watch it complete |
| 21 | `webhooks/service.py` + `router.py` | GET verify, POST receive: check signature, split, find tenant, insert, queue, answer 200 | **Milestone: comment from a 2nd test account becomes a `processed` row** |

## Phase 5: Keep it healthy

| # | File | Write this | Check |
|---|---|---|---|
| 22 | `webhooks/maintenance.py` + beat entries | Requeue stuck events, purge old ones | Stop the worker, send an event, restart; it still gets processed |
| 23 | `connected_accounts/token_service.py` + `token_tasks.py` | Refresh near-expiry tokens; expire overdue ones | Set a token's expiry to tomorrow; run the task |
| 24 | `integrations/instagram/rate_limiter.py` | Redis sliding window per account | Call it more than the limit; expect a wait time |
| 25 | compliance in `webhooks/service.py` | Deauthorize and data-deletion callbacks | Post a self-signed test request |

---

## Habits that keep it clean

- Router talks HTTP, service holds logic, repository holds SQL, integrations talk to Meta, tasks only call services.
- Never log tokens, comment text or usernames.
- Every limit or window lives in `meta_constants.py`, nowhere else.
- Each worker task must be safe to run twice.