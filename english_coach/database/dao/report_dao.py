# ─── database/dao/report_dao.py ───
"""Data Access Object for evaluation reports."""

from __future__ import annotations

from sqlalchemy.orm import Session

from english_coach.database.models import ReportRecord


class ReportDAO:
    """CRUD operations for evaluation report records."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, data: dict) -> ReportRecord:
        """Create a new report record."""
        record = ReportRecord(
            report_id=data["report_id"],
            session_id=data["session_id"],
            overall_score=data.get("overall_score", 0.0),
            report_json=data.get("report", {}),
        )
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        return record

    def get_by_id(self, report_id: str) -> ReportRecord | None:
        """Retrieve a report by ID."""
        return self._db.get(ReportRecord, report_id)

    def list_by_session(self, session_id: str) -> list[ReportRecord]:
        """List all reports for a given session."""
        return (
            self._db.query(ReportRecord)
            .filter(ReportRecord.session_id == session_id)
            .all()
        )

    def delete(self, report_id: str) -> None:
        """Delete a report record."""
        record = self.get_by_id(report_id)
        if record is not None:
            self._db.delete(record)
            self._db.commit()
