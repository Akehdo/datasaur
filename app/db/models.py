import uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geography

class Base(DeclarativeBase):
    pass

class Office(Base):
    __tablename__ = "offices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    city: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)

    location: Mapped[str] = mapped_column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=False
    )