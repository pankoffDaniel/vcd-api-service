from sqlalchemy import (
    Column, ForeignKey,
    Integer, String
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class TemplateCatalogModel(Base):
    """Модель шаблона, состоящая из каталога, vApp и ВМ."""
    __tablename__ = 'template_catalog'
    id = Column(Integer, primary_key=True, autoincrement=True)
    catalog_template_id = Column(
        Integer,
        ForeignKey('catalog_template.id', ondelete='RESTRICT'),
        nullable=False
    )
    vapp_template_id = Column(
        Integer,
        ForeignKey('vapp_template.id', ondelete='RESTRICT'),
        nullable=False
    )
    vm_template_id = Column(
        Integer,
        ForeignKey('vm_template.id', ondelete='RESTRICT'),
        nullable=False,
        unique=True
    )
    catalog_template = relationship(
        'CatalogTemplateModel',
        back_populates='template_catalogs',
        lazy='joined'
    )
    vapp_template = relationship(
        'VAppTemplateModel',
        back_populates='template_catalogs',
        lazy='joined'
    )
    vm_template = relationship(
        'VMTemplateModel',
        back_populates='template_catalogs',
        lazy='joined'
    )


class CatalogTemplateModel(Base):
    """Модель каталога шаблонов."""
    __tablename__ = 'catalog_template'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False, unique=True)
    template_catalogs = relationship(
        'TemplateCatalogModel',
        back_populates='catalog_template'
    )


class VAppTemplateModel(Base):
    """Модель vApp шаблона."""
    __tablename__ = 'vapp_template'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False, unique=True)
    template_catalogs = relationship(
        'TemplateCatalogModel',
        back_populates='vapp_template'
    )


class VMTemplateModel(Base):
    """Модель ВМ шаблона."""
    __tablename__ = 'vm_template'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False, unique=True)
    template_catalogs = relationship(
        'TemplateCatalogModel',
        back_populates='vm_template'
    )
