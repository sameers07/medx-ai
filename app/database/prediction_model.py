"""ORM model for Predictions / history log. Schema only, no insert logic."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship

from app.database.connection import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    study_id = Column(Integer, ForeignKey("studies.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    disease_labels = Column(JSON, nullable=True)     # {"pneumonia": 0.92, ...}
    gradcam_path = Column(String, nullable=True)
    report_text = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    study = relationship("Study")
    user = relationship("User")
