import logging
from logging.config import fileConfig

from alembic import context
from flask import current_app

config = context.config
fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")
database = current_app.extensions["migrate"].db
config.set_main_option(
    "sqlalchemy.url",
    database.engine.url.render_as_string(hide_password=False).replace("%", "%%"),
)


def run_migrations_offline():
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=database.metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def process_revision_directives(context, revision, directives):
    if getattr(config.cmd_opts, "autogenerate", False):
        if directives[0].upgrade_ops.is_empty():
            directives[:] = []
            logger.info("No changes in schema detected.")


def run_migrations_online():
    options = dict(current_app.extensions["migrate"].configure_args)
    options.setdefault("process_revision_directives", process_revision_directives)
    with database.engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=database.metadata,
            **options,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
