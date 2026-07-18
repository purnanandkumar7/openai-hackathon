"""
RCA API router.

Endpoints:
  GET   /rca/{incident_id}              – get RCA report for an incident
  POST  /rca/{incident_id}/approve      – approve the RCA resolution (stores for learning)
  GET   /rca/{incident_id}/export/pdf   – export the RCA as a PDF document
"""

from __future__ import annotations

import uuid
from io import BytesIO
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.incident import Incident
from app.schemas.rca import RCAReport
from app.services.learning_service import LearningService

logger = structlog.get_logger(__name__)
router = APIRouter()

DBDep = Annotated[AsyncSession, Depends(get_db)]


@router.get(
    "/{incident_id}",
    response_model=RCAReport,
    summary="Get RCA report",
)
async def get_rca_report(incident_id: uuid.UUID, db: DBDep) -> RCAReport:
    """
    Return the structured RCA report for a completed incident investigation.
    """
    incident = await _get_incident_or_404(incident_id, db)

    if not incident.rca_report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RCA report not yet generated. Trigger an investigation first.",
        )

    try:
        return RCAReport.model_validate(incident.rca_report)
    except Exception as exc:
        logger.error("Failed to deserialise RCA report", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RCA report format error",
        ) from exc


@router.post(
    "/{incident_id}/approve",
    summary="Approve RCA resolution",
    status_code=status.HTTP_200_OK,
    response_model=dict[str, Any],
)
async def approve_resolution(
    incident_id: uuid.UUID,
    resolution_text: str,
    approved_by: str = "anonymous",
    outcome_score: float = 1.0,
    db: DBDep = Depends(get_db),
) -> dict[str, Any]:
    """
    Approve the incident resolution and store it in the learning database.

    This enables similar future incidents to benefit from this resolution
    via semantic similarity retrieval.
    """
    incident = await _get_incident_or_404(incident_id, db)

    learning_svc = LearningService(db)
    case = await learning_svc.store_approved_resolution(
        incident=incident,
        resolution_text=resolution_text,
        approved_by=approved_by,
        outcome_score=outcome_score,
    )

    logger.info(
        "Resolution approved",
        incident_id=str(incident_id),
        case_id=str(case.id),
        approved_by=approved_by,
    )
    return {
        "message": "Resolution approved and stored for learning",
        "learning_case_id": str(case.id),
        "incident_id": str(incident_id),
    }


@router.get(
    "/{incident_id}/export/pdf",
    summary="Export RCA as PDF",
    response_class=StreamingResponse,
)
async def export_rca_pdf(incident_id: uuid.UUID, db: DBDep) -> StreamingResponse:
    """
    Generate and return a PDF version of the RCA report.

    Uses ReportLab for PDF generation.
    """
    incident = await _get_incident_or_404(incident_id, db)

    if not incident.rca_report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No RCA report available for this incident",
        )

    pdf_bytes = _generate_pdf(incident)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="rca-{incident_id}.pdf"'
            )
        },
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_incident_or_404(incident_id: uuid.UUID, db: AsyncSession) -> Incident:
    from sqlalchemy import select

    stmt = select(Incident).where(Incident.id == incident_id)
    result = await db.execute(stmt)
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )
    return incident


def _generate_pdf(incident: Incident) -> bytes:
    """Generate a PDF RCA report using ReportLab."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    elements = []

    rca = incident.rca_report or {}

    # Title
    elements.append(Paragraph(f"Root Cause Analysis Report", styles["h1"]))
    elements.append(Paragraph(f"Incident: {incident.title}", styles["h2"]))
    elements.append(Spacer(1, 0.5 * cm))

    # Metadata table
    meta_data = [
        ["Incident ID", str(incident.id)],
        ["Severity", incident.severity.upper()],
        ["Status", incident.status],
        ["Created", str(incident.created_at)],
        ["Resolved", str(incident.resolved_at or "Pending")],
    ]
    meta_table = Table(meta_data, colWidths=[5 * cm, 12 * cm])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])
    )
    elements.append(meta_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Executive Summary
    if rca.get("executive_summary"):
        elements.append(Paragraph("Executive Summary", styles["h3"]))
        elements.append(Paragraph(rca["executive_summary"], styles["Normal"]))
        elements.append(Spacer(1, 0.3 * cm))

    # Root Cause
    if rca.get("root_cause"):
        elements.append(Paragraph("Root Cause", styles["h3"]))
        elements.append(Paragraph(rca["root_cause"], styles["Normal"]))
        elements.append(Spacer(1, 0.3 * cm))

    # Fix Applied
    if rca.get("fix_applied"):
        elements.append(Paragraph("Fix Applied", styles["h3"]))
        elements.append(Paragraph(rca["fix_applied"], styles["Normal"]))
        elements.append(Spacer(1, 0.3 * cm))

    # Prevention Steps
    if rca.get("prevention_steps"):
        elements.append(Paragraph("Prevention Steps", styles["h3"]))
        for ps in rca["prevention_steps"]:
            action = ps.get("action", "") if isinstance(ps, dict) else str(ps)
            elements.append(Paragraph(f"• {action}", styles["Normal"]))
        elements.append(Spacer(1, 0.3 * cm))

    doc.build(elements)
    return buf.getvalue()
