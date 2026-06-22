# 10 — Security, Auth, RBAC, Audit Rules

## Security is a generation requirement

Security cannot be added later as optional cleanup. It must exist in the Builder Platform and generated projects.

## Mini App auth

Generated backend must implement:

- endpoint: `POST /auth/bale-miniapp`;
- raw initData parsing;
- HMAC verification using bot token rules;
- `auth_date` freshness validation;
- user creation/update by Bale user id;
- JWT/session issuance;
- invalid request rejection.

Frontend must never authorize based on `initDataUnsafe`.

## RBAC

Generated projects must include:

```text
users
roles
permissions
user_roles
role_permissions
```

Every protected endpoint must declare roles.

No admin endpoint may be generated without admin/operator role restriction.

## Audit log

Audit is mandatory for:

- admin actions;
- role changes;
- approvals/rejections;
- destructive actions;
- system setting changes;
- sensitive bot callbacks;
- document approval in Builder Platform;
- generation run creation.

Audit record should include:

- actor id;
- action;
- target type;
- target id;
- metadata;
- timestamp;
- source: web_panel, miniapp, user_bot, admin_bot, builder.

## Bot webhook security

Generated projects must implement:

- bot key validation;
- token mapping by bot key;
- update idempotency;
- structured logging;
- safe error handling;
- no sensitive token in logs.

## Admin Bot authorization

Admin Bot must verify the Bale sender maps to an internal user with allowed role before any admin response or action.

Unauthorized users should receive a generic rejection.

## Secrets

Secrets must be configured through environment variables. No token, API key, database password, or signing secret may appear in code or generated docs except `.env.example` placeholders.

## Tests required

- Mini App invalid HMAC rejected.
- Expired auth_date rejected.
- User Bot cannot call admin-only API.
- Admin Bot unauthorized Bale user rejected.
- Admin action writes audit log.
- Duplicate webhook update ignored.
- Missing bot token fails safely.
