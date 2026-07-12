from __future__ import annotations

from competehub_api.services.outbound_clicks import aggregate_outbound_clicks
from competehub_api.tasks.celery_app import celery_app


@celery_app.task(name="competehub.outbound_clicks.aggregate")
def aggregate_recorded_outbound_clicks() -> dict[str, bool]:
    aggregate_outbound_clicks()
    return {"aggregated": True}
