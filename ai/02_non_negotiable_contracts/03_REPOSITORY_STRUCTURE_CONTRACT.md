# 14 — Repository Structure Contract

## Builder Platform repository

Claude must structure the platform repository like this or justify any minimal deviation before coding.

```text
bale-bot-builder/
  app/
    main.py
    core/
      config.py
      logging.py
      security.py
    db/
      session.py
      base.py
      models/
      migrations/
    api/
      deps.py
      routes/
        projects.py
        documents.py
        approvals.py
        blueprints.py
        generator.py
        runs.py
    schemas/
      project.py
      document.py
      approval.py
      blueprint.py
      generation.py
    services/
      project_service.py
      document_service.py
      approval_service.py
      blueprint_service.py
      validation_service.py
      generation_service.py
      artifact_service.py
      ai_run_service.py
    crews/
      document_analyzer/
      documentation_architect/
      human_approval_coordinator/
      product_agent_designer/
      multi_bot_architect/
      flow_architect/
      backend_architect/
      bale_integration/
      frontend_architect/
      security_reviewer/
    flows/
      documentation_flow.py
      approval_flow.py
      blueprint_flow.py
      project_builder_flow.py
    generator/
      renderer.py
      template_registry.py
      context_builder.py
      validators.py
      packager.py
      file_manifest.py
      modules/
      templates/
        backend/
        bot/
        frontend/
        docs/
        docker/
        tests/
    workers/
      celery_app.py
      tasks.py
  tests/
    fixtures/
      blueprints/
  docker-compose.yml
  pyproject.toml
  README.md
  CLAUDE.md
```

## Generated project repository

Generator output must follow:

```text
generated_project/
  backend/
    app/
      main.py
      core/
      db/
      models/
      schemas/
      api/
      services/
      bot/
        bale/
          client.py
          models.py
          webhook.py
          router.py
          shared/
          user_bot/
          admin_bot/   # only if Blueprint defines it
      miniapp/
      workers/
    tests/
    Dockerfile
    pyproject.toml
  frontend/
    src/
      routes/
        user/
        admin/         # only if Blueprint defines admin routes
      lib/
      components/
      features/
      schemas/
    package.json
    Dockerfile
  docs/
    project_bot_document.md
    bot_blueprint.yaml
    generation_manifest.json
    architecture.md
    api_contract.yaml
    user_bot_spec.md
    admin_bot_spec.md  # only if Blueprint defines admin bot
  docker-compose.yml
  .env.example
  README.md
```

## Path safety

Generator must never write outside the output root. Blueprint names must be sanitized before becoming filenames or paths.

## Naming rules

- Python files: snake_case.
- TypeScript components: PascalCase for components, kebab-case or route convention for route files.
- Bot keys: snake_case.
- Env vars: UPPER_SNAKE_CASE.
- API paths: kebab-case or plural resource names.
