from app.core.database import SessionLocal
from app.models.merchant import Merchant
from app.models.product import Product

db = SessionLocal()

# Clear existing products and merchants
db.query(Product).delete()
db.query(Merchant).delete()
db.commit()

# =========================================================
# MERCHANT 1 - FitGear (Specializes in Performance & Value)
# =========================================================

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
    # Running
    Product(merchant_id=fitgear.id, name="SpeedRunner Pro", category="running_shoes", price=4299, cost=3100, stock=20, rating=4.6, attributes="experienced,road,performance"),
    Product(merchant_id=fitgear.id, name="Velocity Runner", category="running_shoes", price=2499, cost=1800, stock=25, rating=4.5, attributes="beginner,budget,road,value"),
    Product(merchant_id=fitgear.id, name="Pro Thermo Performance Shirt", category="running_shirt", price=999, cost=650, stock=20, rating=4.7, attributes="experienced,pro,moisture_wicking"),
    Product(merchant_id=fitgear.id, name="Carbon Ultra Shorts", category="running_shorts", price=899, cost=550, stock=18, rating=4.8, attributes="experienced,pro,lightweight"),
    Product(merchant_id=fitgear.id, name="FitGear Cushion Running Socks", category="running_socks", price=249, cost=149, stock=40, rating=4.5, attributes="running,breathable,anti_blister"),

    # Badminton
    Product(merchant_id=fitgear.id, name="Yonex Muscle Power 29 Racket", category="badminton_racket", price=2499, cost=1700, stock=15, rating=4.5, attributes="beginner,intermediate,balanced,durable"),
    Product(merchant_id=fitgear.id, name="Li-Ning G-Force Superlite Racket", category="badminton_racket", price=1999, cost=1350, stock=22, rating=4.3, attributes="beginner,lightweight,budget,value"),
    Product(merchant_id=fitgear.id, name="FitGear Non-Marking Badminton Shoes", category="badminton_shoes", price=2299, cost=1500, stock=14, rating=4.4, attributes="beginner,grip,cushioning"),
    Product(merchant_id=fitgear.id, name="Yonex Super Grap Overgrip 3-Pack", category="badminton_grip", price=299, cost=180, stock=50, rating=4.8, attributes="absorbent,anti_slip"),
    Product(merchant_id=fitgear.id, name="Yonex Mavis 350 Nylon Shuttlecock (6-Pack)", category="shuttlecock", price=699, cost=450, stock=30, rating=4.8, attributes="durable,nylon,flight_accuracy"),

    # Football
    Product(merchant_id=fitgear.id, name="Adidas Predator Turf Boots", category="football_boots", price=3899, cost=2700, stock=12, rating=4.7, attributes="experienced,turf,control"),
    Product(merchant_id=fitgear.id, name="Puma Future Firm Ground Boots", category="football_boots", price=2799, cost=1900, stock=18, rating=4.4, attributes="beginner,fg,agility"),
    Product(merchant_id=fitgear.id, name="FitGear Pro Shin Guards", category="shin_guards", price=499, cost=300, stock=25, rating=4.5, attributes="lightweight,impact_protection"),
    Product(merchant_id=fitgear.id, name="Nike Squad Football Socks", category="football_socks", price=399, cost=240, stock=35, rating=4.6, attributes="cushioned,durable"),

    # Cricket
    Product(merchant_id=fitgear.id, name="SG Kashmir Willow Bat", category="cricket_bat", price=2299, cost=1550, stock=15, rating=4.4, attributes="beginner,kashmir_willow,power_stroke"),
    Product(merchant_id=fitgear.id, name="SG Campus Batting Gloves", category="cricket_gloves", price=699, cost=420, stock=20, rating=4.5, attributes="cotton_padded,flexible"),

    # Tennis
    Product(merchant_id=fitgear.id, name="Babolat Drive Tennis Racket", category="tennis_racket", price=2899, cost=1950, stock=10, rating=4.5, attributes="beginner,intermediate,spin,power"),
    Product(merchant_id=fitgear.id, name="Wilson US Open Tennis Ball Can", category="tennis_balls", price=499, cost=320, stock=40, rating=4.8, attributes="pressurized,durable_felt"),

    # Swimming
    Product(merchant_id=fitgear.id, name="Speedo Futura Biofuse Goggles", category="swimming_goggles", price=1299, cost=850, stock=20, rating=4.7, attributes="anti_fog,uv_protection,comfortable"),
    Product(merchant_id=fitgear.id, name="Speedo Endurance Swim Jammers", category="swimwear", price=1499, cost=980, stock=16, rating=4.6, attributes="chlorine_resistant,quick_dry")
]
db.add_all(fitgear_products)

# =========================================================
# MERCHANT 2 - RunPro (Specializes in Value & Training Gear)
# =========================================================

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
    # Running
    Product(merchant_id=runpro.id, name="SprintX Running Shoes", category="running_shoes", price=3499, cost=2450, stock=18, rating=4.4, attributes="beginner,intermediate,road,durable"),
    Product(merchant_id=runpro.id, name="AirFlow Running Shirt", category="running_shirt", price=599, cost=380, stock=35, rating=4.2, attributes="beginner,breathable"),
    Product(merchant_id=runpro.id, name="Flex Running Shorts", category="running_shorts", price=499, cost=310, stock=28, rating=4.3, attributes="beginner,flexible"),
    Product(merchant_id=runpro.id, name="Pro Elite Compression Socks", category="running_socks", price=499, cost=300, stock=30, rating=4.8, attributes="experienced,pro,compression"),

    # Badminton
    Product(merchant_id=runpro.id, name="Li-Ning Windstorm 72 Racket", category="badminton_racket", price=3199, cost=2200, stock=10, rating=4.6, attributes="intermediate,ultralight,speed"),
    Product(merchant_id=runpro.id, name="Li-Ning Synthetic Badminton Grip", category="badminton_grip", price=149, cost=80, stock=60, rating=4.4, attributes="value,budget,anti_slip"),
    Product(merchant_id=runpro.id, name="Victor Feather Shuttlecock (12-Pack)", category="shuttlecock", price=1199, cost=800, stock=15, rating=4.7, attributes="duck_feather,tournament,flight_stability"),

    # Football
    Product(merchant_id=runpro.id, name="Nivia Premier Football Boots", category="football_boots", price=1599, cost=1050, stock=25, rating=4.2, attributes="beginner,budget,durable,value"),
    Product(merchant_id=runpro.id, name="Puma Football Training Jersey", category="football_jersey", price=649, cost=420, stock=30, rating=4.3, attributes="lightweight,dryfit"),
    Product(merchant_id=runpro.id, name="Adidas Tiro Shin Guards", category="shin_guards", price=449, cost=280, stock=22, rating=4.5, attributes="ergonomic,hard_shell"),

    # Cricket
    Product(merchant_id=runpro.id, name="DSC Club Kashmir Willow Bat", category="cricket_bat", price=1699, cost=1100, stock=20, rating=4.2, attributes="beginner,budget,lightweight_pick"),
    Product(merchant_id=runpro.id, name="SG Club Batting Pads", category="cricket_pads", price=1499, cost=980, stock=14, rating=4.4, attributes="beginner,high_density_foam"),
    Product(merchant_id=runpro.id, name="Nivia Heavy Tennis Cricket Ball 6-Pack", category="cricket_ball", price=299, cost=180, stock=45, rating=4.5, attributes="durable_rubber,heavy_bounce"),

    # Tennis
    Product(merchant_id=runpro.id, name="Head Spark Tennis Racket", category="tennis_racket", price=2199, cost=1450, stock=15, rating=4.3, attributes="beginner,budget,alloy_frame"),
    Product(merchant_id=runpro.id, name="Head XtremeSoft Overgrip", category="tennis_grip", price=249, cost=150, stock=40, rating=4.6, attributes="tacky_feel,sweat_absorption"),

    # Swimming
    Product(merchant_id=runpro.id, name="Arena Cobra Goggles", category="swimming_goggles", price=899, cost=550, stock=25, rating=4.4, attributes="beginner,budget,silicone_gasket"),
    Product(merchant_id=runpro.id, name="Speedo Silicone Swimming Cap", category="swimming_cap", price=349, cost=210, stock=50, rating=4.8, attributes="100%_silicone,snug_fit")
]
db.add_all(runpro_products)

# =========================================================
# MERCHANT 3 - AthleteHub (Specializes in High Performance)
# =========================================================

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
    # Running
    Product(merchant_id=athletehub.id, name="Ultra Pro Carbon Shoe", category="running_shoes", price=4899, cost=3500, stock=15, rating=4.8, attributes="experienced,pro,carbon_plate,road"),
    Product(merchant_id=athletehub.id, name="AthleteDry Running Shirt", category="running_shirt", price=499, cost=320, stock=32, rating=4.5, attributes="beginner,lightweight"),
    Product(merchant_id=athletehub.id, name="SprintFlex Shorts", category="running_shorts", price=399, cost=250, stock=30, rating=4.4, attributes="beginner,lightweight"),
    Product(merchant_id=athletehub.id, name="AthleteHub Running Socks", category="running_socks", price=199, cost=110, stock=50, rating=4.7, attributes="beginner,breathable,value"),

    # Badminton
    Product(merchant_id=athletehub.id, name="Yonex Astrox 99 Pro Racket", category="badminton_racket", price=4699, cost=3300, stock=8, rating=4.8, attributes="experienced,pro,head_heavy,steep_smash"),
    Product(merchant_id=athletehub.id, name="Li-Ning Ranger Badminton Shoes", category="badminton_shoes", price=1899, cost=1250, stock=20, rating=4.2, attributes="beginner,budget,gum_sole"),

    # Football
    Product(merchant_id=athletehub.id, name="Adidas DriFit Training Jersey", category="football_jersey", price=899, cost=580, stock=20, rating=4.6, attributes="breathable,pro_cut"),
    Product(merchant_id=athletehub.id, name="Puma Team Football Socks", category="football_socks", price=249, cost=150, stock=40, rating=4.3, attributes="value,ribbed_cuff"),

    # Cricket
    Product(merchant_id=athletehub.id, name="SS Ton English Willow Bat", category="cricket_bat", price=4799, cost=3400, stock=8, rating=4.8, attributes="experienced,pro,english_willow,huge_sweetspot"),
    Product(merchant_id=athletehub.id, name="SS Super Test Batting Gloves", category="cricket_gloves", price=1199, cost=780, stock=15, rating=4.7, attributes="experienced,pitta_leather,pro_protection"),
    Product(merchant_id=athletehub.id, name="SS Test Batting Pads", category="cricket_pads", price=2499, cost=1650, stock=10, rating=4.7, attributes="experienced,lightweight_cane,pro_impact"),
    Product(merchant_id=athletehub.id, name="SG Tournament Leather Ball", category="cricket_ball", price=399, cost=250, stock=30, rating=4.6, attributes="four_piece_leather,hand_stitched"),

    # Tennis
    Product(merchant_id=athletehub.id, name="Wilson Pro Staff Tennis Racket", category="tennis_racket", price=4899, cost=3450, stock=6, rating=4.8, attributes="experienced,pro,precision_control"),

    # Swimming
    Product(merchant_id=athletehub.id, name="Decathlon Nabaiji Swim Trunks", category="swimwear", price=699, cost=420, stock=30, rating=4.3, attributes="beginner,budget,comfortable_fit")
]
db.add_all(athletehub_products)

# Save database
db.commit()

print(" Multi-sport catalog seeded successfully across 3 merchants!")
db.close()