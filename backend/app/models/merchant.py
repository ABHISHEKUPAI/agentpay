from sqlalchemy import Column, Integer, String, Float
from app.core.database import Base


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String)
    min_margin = Column(Float, default=80)
    max_discount = Column(Float, default=15)