"""Initial empty migration for M0 skeleton."""

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tables will be created by init_db for MVP.
    # Production will use real migrations.
    pass


def downgrade() -> None:
    pass