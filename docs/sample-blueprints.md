# Sample Blueprints

Two sample Blueprint fixtures are provided for Phase 8 end-to-end testing. They demonstrate how different Blueprint configurations produce different generated projects.

Both fixtures live under [`tests/fixtures/blueprints/`](../tests/fixtures/blueprints/).

---

## `support_ticket_like.yaml` — Multi-bot support platform

**Project name:** Support Ticket Platform  
**Bot configuration:** **two bots** — `user_bot` (audience: users) + `admin_bot` (audience: admins)

### What it defines

- **Domain entities:** core RBAC/auth/audit tables plus `tickets` and `ticket_comments`
- **API endpoints:** 6 endpoints including admin-only routes with `audit_required: true`
  - `GET /health`
  - `POST /auth/bale-miniapp`
  - `POST /api/v1/tickets` — submit a ticket (member + admin)
  - `GET /api/v1/tickets` — list own tickets (member + admin)
  - `GET /api/v1/admin/tickets` — admin list all tickets (admin only, audited)
  - `POST /api/v1/admin/tickets/{ticket_id}/close` — close a ticket (admin only, audited)
- **Miniapp routes:** `/user/dashboard` (member) and `/admin/dashboard` (admin)
- **User Bot commands:** `/start`, `/my_tickets`, `/new_ticket`
- **Admin Bot commands:** `/start`, `/pending_tickets`, `/close_ticket`

### What the generator produces

- `bale/user_bot/webhook.py`, `bale/user_bot/commands.py`
- `bale/admin_bot/webhook.py`, `bale/admin_bot/commands.py`
- `bale/tests/test_user_bot_webhook.py`, `bale/tests/test_admin_bot_webhook.py`
- `backend/app/models/tickets.py`, `backend/app/models/ticket_comments.py` (and their schemas/services/routes/tests)
- `frontend/src/pages/UserDashboardPage.tsx`, `frontend/src/pages/AdminDashboardPage.tsx`
- `backend/app/core/config.py` includes both `user_bot_token` and `admin_bot_token`
- **116 total files**

---

## `appointment_form_like.yaml` — User-only appointment platform

**Project name:** Appointment Booking Platform  
**Bot configuration:** **one bot** — `user_bot` only (audience: users), **no Admin Bot**

### What it defines

- **Domain entities:** core RBAC/auth/audit tables plus `appointments` and `appointment_slots`
- **API endpoints:** 5 endpoints, all member-facing
  - `GET /health`
  - `POST /auth/bale-miniapp`
  - `POST /api/v1/appointments` — book an appointment (member)
  - `GET /api/v1/appointments` — list own appointments (member)
  - `DELETE /api/v1/appointments/{appointment_id}` — cancel an appointment (member)
- **Miniapp routes:** `/dashboard` (member only, no admin route)
- **User Bot commands:** `/start`, `/my_appointments`, `/book_appointment`

### What the generator produces

- `bale/user_bot/webhook.py`, `bale/user_bot/commands.py`
- **No** `bale/admin_bot/` directory or files
- `bale/tests/test_user_bot_webhook.py` only
- `backend/app/models/appointments.py`, `backend/app/models/appointment_slots.py` (and their schemas/services/routes/tests)
- `frontend/src/pages/DashboardPage.tsx`
- `backend/app/core/config.py` includes only `user_bot_token`
- **111 total files**

---

## Key differences between the two fixtures

| Aspect | support_ticket_like | appointment_form_like |
|--------|--------------------|-----------------------|
| Bots | user_bot + admin_bot | user_bot only |
| Admin Bot files generated | Yes | No |
| Domain entities | tickets, ticket_comments | appointments, appointment_slots |
| Admin-only API routes | Yes (with audit) | No |
| Admin miniapp route | `/admin/dashboard` | No |
| Config bot tokens | USER_BOT_TOKEN + ADMIN_BOT_TOKEN | USER_BOT_TOKEN only |
| Total generated files | 116 | 111 |

---

## How to run the Phase 8 E2E tests

Run all 48 E2E tests:

```bash
pytest tests/test_e2e_sample_generation.py -v
```

Run a specific group:

```bash
# Domain isolation checks only
pytest tests/test_e2e_sample_generation.py -k "keyword"

# Bot file presence/absence checks
pytest tests/test_e2e_sample_generation.py -k "admin_bot"

# Python compile checks
pytest tests/test_e2e_sample_generation.py -k "compile"
```

---

## Using sample fixtures for manual testing

You can POST either fixture as a Blueprint to a running Builder Platform instance. Convert the YAML to JSON first:

```bash
python3 -c "
import yaml, json
with open('tests/fixtures/blueprints/support_ticket_like.yaml') as f:
    print(json.dumps(yaml.safe_load(f), indent=2))
" > /tmp/support_ticket.json

# Then submit it:
curl -X POST http://localhost:8000/projects/{PROJECT_ID}/blueprint \
  -H "Content-Type: application/json" \
  -d @/tmp/support_ticket.json
```

After storing the Blueprint, validate it and then trigger generation:

```bash
curl -X POST http://localhost:8000/projects/{PROJECT_ID}/blueprint/validate
curl -X POST http://localhost:8000/projects/{PROJECT_ID}/generate
```

---

## Adding your own Blueprint fixture

1. Copy one of the sample fixtures as a starting point.
2. Change `project.name`, `project.slug`, entities, bots, and API endpoints.
3. Validate it parses without error:

```bash
python3 -c "
import yaml
from app.schemas.blueprint import BotBlueprint
with open('tests/fixtures/blueprints/your_fixture.yaml') as f:
    bp = BotBlueprint.model_validate(yaml.safe_load(f))
print('valid:', bp.project.name)
"
```

4. Generate from it programmatically (verify in your environment):

```bash
python3 -c "
import yaml, tempfile
from pathlib import Path
from app.schemas.blueprint import BotBlueprint
from app.generator import GeneratorCore

with open('tests/fixtures/blueprints/your_fixture.yaml') as f:
    bp = BotBlueprint.model_validate(yaml.safe_load(f))

out = Path(tempfile.mkdtemp()) / 'output'
out.mkdir()
result = GeneratorCore().run(bp, out)
print('Generated', len(result.generated_files), 'files in', out)
"
```
