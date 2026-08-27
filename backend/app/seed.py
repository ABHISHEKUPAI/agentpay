from app.core.database import SessionLocal
from app.models.merchant import Merchant
from app.models.product import Product


db = SessionLocal()

db.query(Product).delete()
db.query(Merchant).delete()
db.commit()

# =========================
# MERCHANT 1 - FitGear
# =========================

fitgear = Merchant(
    name="FitGear",
    category="sports",
    min_margin=80,
    max_discount=15
)

db.add(fitgear)
db.commit()
db.refresh(fitgear)

fitgear_products = [
    Product(
        merchant_id=fitgear.id,
        name="Velocity Runner",
        category="running_shoes",
        price=3299,
        cost=2600,
        stock=23,
        rating=4.5,
        attributes="beginner,road"
    ),
    Product(
        merchant_id=fitgear.id,
        name="Performance Running Shirt",
        category="running_shirt",
        price=699,
        cost=450,
        stock=30,
        rating=4.3,
        attributes="beginner,breathable"
    ),
    Product(
        merchant_id=fitgear.id,
        name="Running Shorts",
        category="running_shorts",
        price=499,
        cost=300,
        stock=25,
        rating=4.4,
        attributes="beginner,lightweight"
    ),
    Product(
        merchant_id=fitgear.id,
        name="Performance Socks",
        category="running_socks",
        price=249,
        cost=149,
        stock=40,
        rating=4.6,
        attributes="running,breathable"
    )
]

db.add_all(fitgear_products)


# =========================
# MERCHANT 2 - RunPro
# =========================

runpro = Merchant(
    name="RunPro",
    category="sports",
    min_margin=80,
    max_discount=15
)

db.add(runpro)
db.commit()
db.refresh(runpro)

runpro_products = [
    Product(
        merchant_id=runpro.id,
        name="SprintX Running Shoes",
        category="running_shoes",
        price=3499,
        cost=2750,
        stock=18,
        rating=4.4,
        attributes="beginner,road,durable"
    ),
    Product(
        merchant_id=runpro.id,
        name="AirFlow Running Shirt",
        category="running_shirt",
        price=599,
        cost=380,
        stock=35,
        rating=4.2,
        attributes="beginner,breathable"
    ),
    Product(
        merchant_id=runpro.id,
        name="Flex Running Shorts",
        category="running_shorts",
        price=499,
        cost=310,
        stock=28,
        rating=4.3,
        attributes="beginner,flexible"
    ),
    Product(
        merchant_id=runpro.id,
        name="RunPro Performance Socks",
        category="running_socks",
        price=299,
        cost=180,
        stock=45,
        rating=4.5,
        attributes="running,breathable"
    )
]

db.add_all(runpro_products)


# =========================
# MERCHANT 3 - AthleteHub
# =========================

athletehub = Merchant(
    name="AthleteHub",
    category="sports",
    min_margin=80,
    max_discount=15
)

db.add(athletehub)
db.commit()
db.refresh(athletehub)

athletehub_products = [
    Product(
        merchant_id=athletehub.id,
        name="Road Runner Pro",
        category="running_shoes",
        price=3799,
        cost=3000,
        stock=15,
        rating=4.7,
        attributes="beginner,road,premium"
    ),
    Product(
        merchant_id=athletehub.id,
        name="AthleteDry Running Shirt",
        category="running_shirt",
        price=499,
        cost=320,
        stock=32,
        rating=4.5,
        attributes="beginner,lightweight"
    ),
    Product(
        merchant_id=athletehub.id,
        name="SprintFlex Shorts",
        category="running_shorts",
        price=399,
        cost=250,
        stock=30,
        rating=4.4,
        attributes="beginner,lightweight"
    ),
    Product(
        merchant_id=athletehub.id,
        name="AthleteHub Running Socks",
        category="running_socks",
        price=199,
        cost=110,
        stock=50,
        rating=4.7,
        attributes="running,breathable"
    )
]

db.add_all(athletehub_products)


# Save everything
db.commit()

print("All merchants and products added successfully!")

db.close()