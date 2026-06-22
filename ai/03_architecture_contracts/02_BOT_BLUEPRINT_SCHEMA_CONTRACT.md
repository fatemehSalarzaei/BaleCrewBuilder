# 04 — Bot Blueprint Schema Contract

## Role of Bot Blueprint

Bot Blueprint is the only valid input to the deterministic Generator.

Raw documents and free-form CrewAI output cannot be used directly for code generation.

## Required properties

Every Blueprint must include:

```yaml
blueprint_version: "1.0"
project: {}
workflow: {}
actors: []
roles: []
permissions: []
bots: []
miniapp: {}
backend: {}
database: {}
flows: []
api: {}
security: {}
testing: {}
generation: {}
```

## Required project fields

```yaml
project:
  name: string
  slug: string
  platform: bale
  backend: fastapi
  frontend: miniapp_panel
  generation_mode: documentation_first
```

## Required workflow fields

```yaml
workflow:
  documentation_required: true
  human_approval_required: true
  document_status: DOCUMENT_APPROVED
  implementation_starts_after: BLUEPRINT_VALIDATED
```

## Required bot fields

Each bot must include:

```yaml
bots:
  - key: user_bot
    title: string
    audience: users|admins|operators|custom
    token_env: string
    webhook_path: string
    allowed_roles: []
    miniapp_default_route: string
    commands: []
    handlers: []
    security_policy: {}
```

## Multi-bot requirements

If project has admin/operator roles and admin operations, the Blueprint must include an `admin_bot`, unless the Project Bot Document explicitly justifies single-bot mode.

User Bot and Admin Bot must not share:

- token env name;
- webhook path;
- command namespace;
- handler folder;
- authorization policy.

They must share:

- backend service layer;
- database;
- RBAC;
- audit log;
- frontend app.

## API endpoint fields

Each endpoint must include:

```yaml
api:
  endpoints:
    - name: string
      method: GET|POST|PUT|PATCH|DELETE
      path: string
      auth_required: boolean
      allowed_roles: []
      request_schema: string|null
      response_schema: string|null
      service_method: string
      audit_required: boolean
```

No generated API endpoint may omit `allowed_roles` when `auth_required=true`.

## Database entity fields

```yaml
database:
  entities:
    - name: string
      table_name: string
      fields: []
      relationships: []
      indexes: []
      audit: boolean
```

Core entities must always be present:

- users;
- roles;
- permissions;
- user_roles;
- role_permissions;
- bale_accounts;
- bots;
- bot_conversations;
- processed_updates;
- audit_logs;
- app_settings.

## Mini App fields

```yaml
miniapp:
  enabled: true
  routes:
    - path: /user/dashboard
      allowed_roles: []
      page_type: dashboard|list|form|detail|settings|report
      api_dependencies: []
    - path: /admin/dashboard
      allowed_roles: []
      page_type: dashboard
      api_dependencies: []
```

Routes under `/admin/*` must not allow ordinary user roles.

## Generator fields

```yaml
generation:
  template_profile: fastapi_react_bale_v1
  enabled_modules: []
  custom_logic_blocks: []
  output_format: zip|repository
```

## Validation rules

Blueprint validation must fail if:

- `workflow.document_status != DOCUMENT_APPROVED`;
- no bot exists;
- user/admin bots share webhook path or token env;
- admin route allows ordinary user role;
- endpoint has auth but no roles;
- admin operation has no audit rule;
- database core tables are missing;
- Mini App enabled but auth route missing;
- generation references unknown template/module.
