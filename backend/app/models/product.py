from sqlalchemy import Column, Integer, String, Float
from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, nullable=False)

    name = Column(String, nullable=False)
    category = Column(String)

    price = Column(Float, nullable=False)
    cost = Column(Float, nullable=False)

    stock = Column(Integer, default=0)
    rating = Column(Float, default=0)

    attributes = Column(String)