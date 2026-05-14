import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.services import export_service, storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/export", tags=["export"])


class ExportRequest(BaseModel):
    itinerary: dict


@router.get("/{trip_id}/markdown")
async def export_markdown(trip_id: str):
    try:
        trip = storage_service.get_by_id(trip_id)
        if trip is None:
            raise HTTPException(status_code=404, detail="行程不存在")
        md = export_service.export_markdown(trip)
        return Response(
            content=md,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="trip_{trip_id[:8]}.md"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Markdown export failed trip_id=%s: %s", trip_id, e)
        raise HTTPException(status_code=500, detail=f"导出失败: {e}")


@router.get("/{trip_id}/pdf")
async def export_pdf(trip_id: str):
    try:
        trip = storage_service.get_by_id(trip_id)
        if trip is None:
            raise HTTPException(status_code=404, detail="行程不存在")
        pdf_bytes = export_service.export_pdf(trip)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="trip_{trip_id[:8]}.pdf"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("PDF export failed trip_id=%s: %s", trip_id, e)
        raise HTTPException(status_code=500, detail=f"导出失败: {e}")


@router.post("/markdown")
async def export_markdown_direct(body: ExportRequest):
    """Export markdown directly from itinerary JSON (no save required)."""
    try:
        md = export_service.export_markdown(body.itinerary)
        return Response(
            content=md,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="trip.md"'},
        )
    except Exception as e:
        logger.error("Direct markdown export failed: %s", e)
        raise HTTPException(status_code=500, detail=f"导出失败: {e}")


@router.post("/pdf")
async def export_pdf_direct(body: ExportRequest):
    """Export PDF directly from itinerary JSON (no save required)."""
    try:
        pdf_bytes = export_service.export_pdf(body.itinerary)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="trip.pdf"'},
        )
    except Exception as e:
        logger.error("Direct PDF export failed: %s", e)
        raise HTTPException(status_code=500, detail=f"导出失败: {e}")
