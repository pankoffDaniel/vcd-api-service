from sqlalchemy import Column, Integer, String

from app.db.base import Base


class SettingsModel(Base):
    """Модель настроек приложения."""
    __tablename__ = 'settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    vcd_api_jwt = Column(String(1023), nullable=True, unique=True)
    default_vdc = Column(String(255), nullable=True, unique=True)
    default_vapp = Column(String(255), nullable=True, unique=True)
