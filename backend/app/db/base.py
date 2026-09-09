from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Central SQLAlchemy Declarative Base for DevLens.
    All ORM models must inherit from this shared Base.
    """
    pass
