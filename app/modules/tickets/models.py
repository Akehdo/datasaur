import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Enum
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from geoalchemy2 import Geography


Base = declarative_base()


# =====================================================
# OFFICE (PostGIS)
# =====================================================

class Office(Base):
    __tablename__ = "offices"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    city = Column(String(120), unique=True, nullable=False)
    address = Column(String(255), nullable=False)

    # PostGIS geography point
    location = Column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=False,
    )

    managers = relationship("Manager", back_populates="office")


# =====================================================
# MANAGER
# =====================================================

class Manager(Base):
    __tablename__ = "managers"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name = Column(String(200), nullable=False)
    position = Column(String(100), nullable=False)

    # FK на офис
    office_id = Column(
        UUID(as_uuid=True),
        ForeignKey("offices.id"),
        nullable=False,
    )

    office = relationship("Office", back_populates="managers")

    # PostgreSQL ARRAY
    skills = Column(ARRAY(String), default=[])

    workload = Column(Integer, default=0)

    tickets = relationship("Ticket", back_populates="manager")

    def has_skill(self, skill: str) -> bool:
        if not self.skills:
            return False
        return skill.strip() in self.skills


# =====================================================
# TICKET
# =====================================================

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    guid = Column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )

    status = Column(String(20), default="NEW")

    # Клиент
    gender = Column(String(20))
    birth_date = Column(String(30))
    description = Column(Text)
    attachment = Column(String(500))

    segment = Column(String(20))      # Mass / VIP / Priority
    country = Column(String(100))
    region = Column(String(150))
    city = Column(String(100))
    street = Column(String(200))
    house = Column(String(50))

    lat = Column(String)
    lon = Column(String)

    # ===== AI analysis =====
    ticket_type = Column(String(50))
    tone = Column(String(20))
    priority = Column(Integer)
    language = Column(String(5))     # RU / KZ / ENG
    summary = Column(Text)
    recommendation = Column(Text)

    # ===== Assignment =====
    assigned_manager_id = Column(
        UUID(as_uuid=True),
        ForeignKey("managers.id"),
    )

    assigned_office_id = Column(
        UUID(as_uuid=True),
        ForeignKey("offices.id"),
    )

    processed_at = Column(DateTime, default=datetime.utcnow)

    manager = relationship("Manager", back_populates="tickets")
    assigned_office = relationship("Office")


# =====================================================
# ROUND ROBIN STATE
# =====================================================

class RoundRobinState(Base):
    __tablename__ = "round_robin_state"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    office_id = Column(
        UUID(as_uuid=True),
        ForeignKey("offices.id"),
        unique=True,
        nullable=False,
    )

    slot = Column(Integer, default=0)

    office = relationship("Office")