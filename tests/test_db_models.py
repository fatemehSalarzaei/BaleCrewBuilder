"""
Verify that all required Builder Platform tables are registered in SQLAlchemy metadata
and that an initial Alembic migration covering those tables exists.

These tests do not touch a real database — they only inspect the ORM layer and the
migration source file, so they run without PostgreSQL or asyncpg.
"""
from pathlib import Path

import app.db.models  # noqa: F401 — side-effect import registers all models with Base.metadata
from app.db.base import Base

_MIGRATIONS_VERSIONS_DIR = (
    Path(__file__).parent.parent / "app" / "db" / "migrations" / "versions"
)

REQUIRED_TABLES = {
    "projects",
    "project_documents",
    "document_reviews",
    "blueprints",
    "blueprint_validations",
    "generation_runs",
    "generated_artifacts",
    "ai_runs",
    "uploaded_files",
}


def test_all_required_tables_registered_in_metadata():
    registered = set(Base.metadata.tables.keys())
    missing = REQUIRED_TABLES - registered
    assert not missing, f"Missing tables in Base.metadata: {missing}"


def test_no_extra_tables_in_metadata():
    registered = set(Base.metadata.tables.keys())
    unexpected = registered - REQUIRED_TABLES
    assert not unexpected, f"Unexpected tables in Base.metadata: {unexpected}"


def test_projects_table_columns():
    table = Base.metadata.tables["projects"]
    col_names = {c.name for c in table.columns}
    assert {"id", "name", "description", "status", "created_at", "updated_at"} <= col_names


def test_blueprints_table_has_unique_project_id():
    table = Base.metadata.tables["blueprints"]
    unique_cols = {
        col.name
        for constraint in table.constraints
        if hasattr(constraint, "columns")
        for col in constraint.columns
        if not getattr(constraint, "is_primary_key", False)
        and type(constraint).__name__ == "UniqueConstraint"
    }
    assert "project_id" in unique_cols, "blueprints.project_id must have a UNIQUE constraint"


def test_blueprint_validations_fk_to_blueprints():
    table = Base.metadata.tables["blueprint_validations"]
    fk_targets = {fk.target_fullname for col in table.columns for fk in col.foreign_keys}
    assert "blueprints.id" in fk_targets


def test_document_reviews_nullable_document_id():
    table = Base.metadata.tables["document_reviews"]
    doc_id_col = table.c["document_id"]
    assert doc_id_col.nullable, "document_reviews.document_id must be nullable"


def test_generation_runs_nullable_blueprint_id():
    table = Base.metadata.tables["generation_runs"]
    bp_id_col = table.c["blueprint_id"]
    assert bp_id_col.nullable, "generation_runs.blueprint_id must be nullable"


# ── Alembic migration file checks ─────────────────────────────────────────────


def test_migration_versions_directory_is_not_empty():
    version_files = [
        f for f in _MIGRATIONS_VERSIONS_DIR.iterdir()
        if f.suffix == ".py" and not f.name.startswith("__")
    ]
    assert version_files, (
        f"No migration version files found in {_MIGRATIONS_VERSIONS_DIR}. "
        "Run 'alembic revision' to create the initial migration."
    )


def test_migration_references_all_required_tables():
    version_files = [
        f for f in _MIGRATIONS_VERSIONS_DIR.iterdir()
        if f.suffix == ".py" and not f.name.startswith("__")
    ]
    assert version_files, "No migration version files to inspect."

    combined_source = "\n".join(f.read_text(encoding="utf-8") for f in version_files)
    missing = [t for t in sorted(REQUIRED_TABLES) if f'"{t}"' not in combined_source]
    assert not missing, (
        f"These required tables are not referenced in any migration file: {missing}"
    )
