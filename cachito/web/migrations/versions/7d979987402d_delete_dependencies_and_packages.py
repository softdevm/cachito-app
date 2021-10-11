"""Delete dependencies and packages

Revision ID: 7d979987402d
Revises: 976b7ef3ec86
Create Date: 2021-10-12 15:23:03.826535

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import context

# revision identifiers, used by Alembic.
revision = "7d979987402d"
down_revision = "976b7ef3ec86"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    if context.get_x_argument(as_dictionary=True).get("delete_data", None):
        with op.batch_alter_table("request_dependency", schema=None) as batch_op:
            batch_op.drop_index("ix_request_dependency_dependency_id")
            batch_op.drop_index("ix_request_dependency_package_id")
            batch_op.drop_index("ix_request_dependency_replaced_dependency_id")
            batch_op.drop_index("ix_request_dependency_request_id")

        op.drop_table("request_dependency")
        with op.batch_alter_table("request_package", schema=None) as batch_op:
            batch_op.drop_index("ix_request_package_package_id")
            batch_op.drop_index("ix_request_package_request_id")

        op.drop_table("request_package")
        with op.batch_alter_table("package", schema=None) as batch_op:
            batch_op.drop_index("ix_package_dev")
            batch_op.drop_index("ix_package_name")
            batch_op.drop_index("ix_package_type")
            batch_op.drop_index("ix_package_version")

        op.drop_table("package")

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "package",
        sa.Column(
            "id",
            sa.INTEGER(),
            server_default=sa.text("nextval('dependency_id_seq'::regclass)"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("name", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("type", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("version", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column(
            "dev",
            sa.BOOLEAN(),
            server_default=sa.text("false"),
            autoincrement=False,
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="dependency_pkey"),
        sa.UniqueConstraint(
            "dev", "name", "type", "version", name="dependency_dev_name_type_version_key"
        ),
        postgresql_ignore_search_path=False,
    )
    with op.batch_alter_table("package", schema=None) as batch_op:
        batch_op.create_index("ix_package_version", ["version"], unique=False)
        batch_op.create_index("ix_package_type", ["type"], unique=False)
        batch_op.create_index("ix_package_name", ["name"], unique=False)
        batch_op.create_index("ix_package_dev", ["dev"], unique=False)

    op.create_table(
        "request_package",
        sa.Column("request_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("package_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("subpath", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(
            ["package_id"], ["package.id"], name="request_package_package_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["request_id"], ["request.id"], name="request_package_request_id_fkey"
        ),
        sa.PrimaryKeyConstraint("request_id", "package_id", name="request_package_pkey"),
    )
    with op.batch_alter_table("request_package", schema=None) as batch_op:
        batch_op.create_index("ix_request_package_request_id", ["request_id"], unique=False)
        batch_op.create_index("ix_request_package_package_id", ["package_id"], unique=False)

    op.create_table(
        "request_dependency",
        sa.Column("request_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("dependency_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("replaced_dependency_id", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("package_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.ForeignKeyConstraint(
            ["dependency_id"], ["package.id"], name="request_dependency_dependency_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["package_id"], ["package.id"], name="fk_request_dependency_package_id"
        ),
        sa.ForeignKeyConstraint(
            ["replaced_dependency_id"], ["package.id"], name="fk_replaced_dependency_id"
        ),
        sa.ForeignKeyConstraint(
            ["request_id"], ["request.id"], name="request_dependency_request_id_fkey"
        ),
        sa.UniqueConstraint(
            "request_id",
            "dependency_id",
            "package_id",
            name="request_dependency_request_id_dependency_id_package_id_key",
        ),
    )
    with op.batch_alter_table("request_dependency", schema=None) as batch_op:
        batch_op.create_index("ix_request_dependency_request_id", ["request_id"], unique=False)
        batch_op.create_index(
            "ix_request_dependency_replaced_dependency_id", ["replaced_dependency_id"], unique=False
        )
        batch_op.create_index("ix_request_dependency_package_id", ["package_id"], unique=False)
        batch_op.create_index(
            "ix_request_dependency_dependency_id", ["dependency_id"], unique=False
        )

    # ### end Alembic commands ###
