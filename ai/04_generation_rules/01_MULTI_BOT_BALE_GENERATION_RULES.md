# 07 — Multi-Bot Bale Generation Rules

## Purpose

This file defines how the Builder Platform must generate Bale bot layers per project. It does not define a fixed User Bot or Admin Bot for every generated project.

## Required platform capability

The Builder must support:

- one-bot projects;
- two-bot projects with User Bot and Admin Bot;
- future multi-bot projects with custom bot keys.

## Default recommended architecture

For projects with ordinary users and administrative workflows, generate:

```text
User Bot
Admin Bot
Shared Backend
Shared Service Layer
Shared Database
Shared Mini App/Web Panel
```

## Required generated backend structure

```text
backend/app/bot/bale/
  client.py
  models.py
  webhook.py
  router.py
  keyboards.py
  shared/
    state.py
    permissions.py
    miniapp.py
    idempotency.py
  user_bot/
    commands.py
    keyboards.py
    handlers/
  admin_bot/
    commands.py
    keyboards.py
    handlers/
```

If Blueprint does not define `admin_bot`, do not generate `admin_bot/` except as optional disabled template documentation.

## Webhook rules

Each bot must have a separate webhook path.

Examples:

```text
POST /webhooks/bale/user-bot
POST /webhooks/bale/admin-bot
```

Generic webhook is allowed only if it still enforces bot key validation:

```text
POST /webhooks/bale/{bot_key}
```

`bot_key` must map to a known bot in database/config. Unknown bot keys must be rejected.

## Token rules

Each bot must use a separate env variable:

```env
BALE_USER_BOT_TOKEN=...
BALE_ADMIN_BOT_TOKEN=...
```

Do not store tokens in generated source code.

## User Bot generation rules

User Bot may include:

- onboarding;
- simple commands;
- user-facing notifications;
- Mini App entry to `/user/*` routes;
- simple callback actions.

User Bot must not include admin-only commands.

## Admin Bot generation rules

Admin Bot may include:

- admin onboarding;
- alerts;
- pending item summaries;
- approval/rejection actions;
- quick reports;
- Mini App entry to `/admin/*` routes.

Admin Bot must enforce backend authorization on every update. Unauthorized users receive a generic denial message and no internal details.

## Admin Bot security rules

Admin Bot operations require:

- role check against backend user/role store;
- audit log for sensitive actions;
- confirmation for destructive or approval actions;
- idempotency protection for repeated callbacks;
- no sensitive data in logs.

## Bot handler rules

Bot handlers must call backend services. They must not contain business logic.

Allowed in handler:

- parse command/callback;
- call service;
- send response;
- render keyboard;
- route to Mini App.

Forbidden in handler:

- direct SQL business updates;
- permission decisions without service/dependency;
- long-running work;
- hidden admin bypass.

## Bale API client rules

Generated Bale API layer must use direct HTTP abstraction:

```text
BaleClient.send_message(...)
BaleClient.answer_callback_query(...)
BaleClient.set_webhook(...)
BaleClient.send_document(...)
```

Implementation should use `httpx.AsyncClient` and expose typed methods.

## Tests required

Generated project must include tests for:

- User Bot webhook accepts valid update;
- Admin Bot webhook rejects unauthorized user;
- duplicate update is ignored;
- command dispatch works by bot key;
- Admin Bot sensitive callback writes audit log;
- bot token env missing produces controlled startup/config error.
