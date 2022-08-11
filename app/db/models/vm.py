from sqlalchemy import (
    Column, DateTime,
    ForeignKey, Integer,
    String
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class VMModel(Base):
    """Модель ВМ."""
    __tablename__ = 'vm'
    id = Column(Integer, primary_key=True, autoincrement=True)
    vm_id = Column(String(255), nullable=False, unique=True)
    title = Column(String(255), nullable=False)
    statistics = relationship('VMStatisticsModel', back_populates='vm')


class VMStatisticsModel(Base):
    """Модель собираемой статистики ВМ из vCD."""
    __tablename__ = 'vm_statistics'
    id = Column(Integer, primary_key=True, autoincrement=True)
    vm_id = Column(Integer, ForeignKey('vm.id', ondelete='RESTRICT'))
    vm = relationship('VMModel', back_populates='statistics', lazy='joined')
    statistics = Column(JSONB, nullable=False)
    created_at = Column(DateTime, nullable=False)
