# 05 — Generator Contract

## Definition

The Generator is a deterministic module inside the Builder Platform. It converts a validated Bot Blueprint into project files.

It is not CrewAI.
It is not a free-form LLM code writer.
It must be testable.

## Generator input

The only valid input is a validated Bot Blueprint.

## Generator output

The output is a generated project directory or ZIP containing:

```text
backend/
frontend/
docs/
docker-compose.yml
.env.example
README.md
```

## Required Generator modules

```text
generator/
  __init__.py
  renderer.py
  template_registry.py
  context_builder.py
  validators.py
  packager.py
  file_manifest.py
  modules/
    core.py
    backend.py
    bot.py
    frontend.py
    docs.py
    docker.py
    tests.py
  templates/
    backend/
    bot/
    frontend/
    docs/
    docker/
    tests/
```

## Generation pipeline

```text
1. Load Blueprint
2. Validate Blueprint
3. Build render context
4. Select modules from Blueprint
5. Resolve templates
6. Render backend core
7. Render database models/migrations
8. Render services
9. Render API routes
10. Render Bale bot shared client/webhook/router
11. Render User Bot files
12. Render Admin Bot files if Blueprint requires it
13. Render frontend Mini App/Web Panel
14. Render docs
15. Render tests
16. Render Docker/env files
17. Build manifest
18. Run format/lint/test commands if available
19. Package ZIP/repository
```

## Determinism requirements

For the same Blueprint and template version, Generator output must be stable.

- No random filenames.
- No undeclared services.
- No invented routes.
- No invented commands.
- No domain-specific code outside Blueprint.
- No LLM call inside deterministic generation path.

## AI-assisted custom blocks

AI-assisted custom logic is allowed only in explicit custom blocks:

```yaml
generation:
  custom_logic_blocks:
    - name: appointment_availability_rule
      target_file: backend/app/services/custom_rules/appointment_rules.py
      description: "..."
      required_tests:
        - tests/test_appointment_rules.py
```

Custom blocks require:

- explicit Blueprint declaration;
- generated tests;
- lint/test execution;
- code review marker;
- isolated location under `services/custom_rules/` or equivalent.

## Generator must reject

Generator must reject generation if:

- Blueprint is invalid;
- project document is not approved;
- template profile is unknown;
- required module template is missing;
- output path escapes generated project root;
- duplicate generated file path exists without explicit overwrite policy;
- core security files would be omitted.

## File manifest

Every generation run must produce:

```text
docs/generation_manifest.json
```

Manifest must include:

- blueprint hash;
- template profile and version;
- generated file list;
- module list;
- custom block list;
- validation result;
- test command results if run.
