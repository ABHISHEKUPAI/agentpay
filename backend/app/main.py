from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine
from app.models.merchant import Merchant
from app.models.product import Product
from app.routes.merchant import router as merchant_router
from app.routes.buyer import router as buyer_router
from app.routes.recovery import router as recovery_router


Base.metadata.create_all(bind=engine)


app = FastAPI(title="AgentPay API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(merchant_router)
app.include_router(buyer_router)
app.include_router(recovery_router)

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "AgentPay Backend"
    }