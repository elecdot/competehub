from __future__ import annotations

import click
from flask import Flask

from competehub_api.seeds.development_demo import (
    DevelopmentDemoConflict,
    bootstrap_development_demo,
)
from competehub_api.seeds.recommendation_rules import (
    InitialRecommendationRuleSetConflict,
    seed_initial_recommendation_rule_set,
)


def register_cli_commands(app: Flask) -> None:
    @app.cli.command("bootstrap-development-demo")
    @click.option(
        "--reset-demo",
        is_flag=True,
        help="Replace only records owned by the development demo registry.",
    )
    def bootstrap_development_demo_command(reset_demo: bool) -> None:
        try:
            result = bootstrap_development_demo(reset_demo=reset_demo)
        except DevelopmentDemoConflict as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(f"Development demo dataset {result.action}.")

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
