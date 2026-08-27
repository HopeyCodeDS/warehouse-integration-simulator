from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .database import engine, Base, get_db
from .models import Task

app = FastAPI(title="WIS WMS API", version="1.0.0")

class TaskCreate(BaseModel):
    order_number: str
    task_type: str
    payload: dict

@app.get("/health")
def health():
    return {"status": "healthy", "service": "wms-api"}

@app.post("/api/tasks", status_code=201)
def receive_task(task_data: TaskCreate, db: Session = Depends(get_db)):
    # The WMS receives a generic "task" and saves it to its own database
    new_task = Task(
        order_number=task_data.order_number,
        task_type=task_data.task_type,
        payload=task_data.payload
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    print(f"[WMS] Task received and saved: {new_task.order_number}")
    return {"message": "Task accepted by WMS", "task_id": str(new_task.id)}