"""initial_builder_platform_schema

Revision ID: 0474661fd116
Revises:
Create Date: 2026-06-22 12:50:03.810611

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0474661fd116"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1 ── projects ────────────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2 ── project_documents ───────────────────────────────────────────────────
    op.create_table(
        "project_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(50), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # 3 ── document_reviews ────────────────────────────────────────────────────
    op.create_table(
        "document_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("reviewer_name", sa.String(200), nullable=True),
        sa.Column("decision", sa.String(50), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("previous_status", sa.String(50), nullable=False),
        sa.Column("next_status", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["project_documents.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # 4 ── blueprints ──────────────────────────────────────────────────────────
    op.create_table(
        "blueprints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("blueprint_data", sa.JSON(), nullable=False),
        sa.Column("stored_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id"),
    )

    # 5 ── blueprint_validations ───────────────────────────────────────────────
    op.create_table(
        "blueprint_validations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("blueprint_id", sa.Uuid(), nullable=False),
        sa.Column("is_valid", sa.Boolean(), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["blueprint_id"], ["blueprints.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # 6 ── generation_runs ─────────────────────────────────────────────────────
    op.create_table(
        "generation_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("blueprint_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("template_profile", sa.String(200), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["blueprint_id"], ["blueprints.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # 7 ── generated_artifacts ─────────────────────────────────────────────────
    op.create_table(
        "generated_artifacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("generation_run_id", sa.Uuid(), nullable=False),
        sa.Column("artifact_type", sa.String(100), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["generation_run_id"], ["generation_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # 8 ── ai_runs ─────────────────────────────────────────────────────────────
    op.create_table(
        "ai_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("run_type", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("input_data", sa.JSON(), nullable=True),
        sa.Column("output_data", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # 9 ── uploaded_files ──────────────────────────────────────────────────────
    op.create_table(
        "uploaded_files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(200), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    # Drop in reverse FK dependency order
    op.drop_table("uploaded_files")
    op.drop_table("ai_runs")
    op.drop_table("generated_artifacts")
    op.drop_table("generation_runs")
    op.drop_table("blueprint_validations")
    op.drop_table("blueprints")
    op.drop_table("document_reviews")
    op.drop_table("project_documents")
    op.drop_table("projects")
