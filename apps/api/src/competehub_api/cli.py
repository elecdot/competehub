from __future__ import annotations

import click
from flask import Flask

from competehub_api.seeds.recommendation_rules import (
    InitialRecommendationRuleSetConflict,
    seed_initial_recommendation_rule_set,
)


def register_cli_commands(app: Flask) -> None:
    @app.cli.command("seed-recommendation-rules")
    def seed_recommendation_rules() -> None:
        try:
            rule_set = seed_initial_recommendation_rule_set()
        except InitialRecommendationRuleSetConflict as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(
            "Verified reproducible recommendation rule-set "
            f"v{rule_set.version} (status: {rule_set.status.value})."
        )


def main() -> None:
    from competehub_api.app import create_app

    app = create_app()
    click.echo(f"CompeteHub API ready: {app.name}")
