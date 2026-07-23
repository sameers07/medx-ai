"""
Importing this package registers every ORM model on Base's mapper registry.

Necessary even if a module only needs one model directly — SQLAlchemy resolves the string-based
relationship() targets (e.g. Prediction.user = relationship("User")) by looking up whatever
classes have been imported somewhere, not just the ones a given module happens to reference.
"""
from app.database import patient_model, prediction_model, user_model  # noqa: F401
