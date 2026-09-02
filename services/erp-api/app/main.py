from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .database import engine, get_db, Base
from . import models, schemas
import json
import uuid


app = FastAPI(
    title="WIS ERP API",
    description="Simulates an Enterprise Resource Planning system for the Warehouse Integration Simulator.",
    version="1.0.0"
)

# First Principle: We explicitly trust the React frontend to send commands.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "healthy", "service": "erp-api"}

@app.post("/api/orders", response_model=schemas.OrderResponse, status_code=201, tags=["Orders"])
def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    # 1. Check for duplicate order numbers
    db_order = db.query(models.Order).filter(models.Order.order_number == order.order_number).first()
    if db_order:
        raise HTTPException(status_code=400, detail="Order number already exists")

    # 2. Create the Order
    new_order = models.Order(
        order_number=order.order_number,
        customer=order.customer,
        destination_dock=order.destination_dock,
        status="PENDING"
    )
    db.add(new_order)
    db.flush() # Flush to get the new_order.id

    # 3. Create Order Items
    for item in order.items:
        new_item = models.OrderItem(
            order_id=new_order.id,
            product_sku=item.product_sku,
            requested_qty=item.requested_qty
        )
        db.add(new_item)

    # 4. Log the Integration Event
    correlation_id = str(uuid.uuid4())
    event_payload = json.dumps({
        "correlation_id": correlation_id,
        "order_number": order.order_number,
        "customer": order.customer,
        "items_count": len(order.items)
    })
    
    integration_event = models.IntegrationEvent(
        source="ERP",
        destination="Integration_Engine",
        event_type="ORDER_CREATED",
        payload=event_payload,
        status="PENDING"
    )
    db.add(integration_event)

    # 5. Commit everything in a single transaction
    db.commit()
    db.refresh(new_order)
    
    return new_order

@app.get("/api/orders/{order_number}", response_model=schemas.OrderResponse, tags=["Orders"])
def get_order(order_number: str, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.order_number == order_number).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order