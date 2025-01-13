from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
# Configure allowed origins
app = FastAPI()
origins = [
    "http://localhost:5173",  # React development server
    "http://localhost:8000",  # FastAPI server (optional)
]

# Add CORS middleware to allow requests from specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)
# Database setup
DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class Chat(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=True, nullable=False)
    created_at = Column(String, default=datetime.utcnow)
    messages = relationship("Message", back_populates="chat", cascade="all, delete")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    content = Column(Text, nullable=False)
    ollama_said = Column(String, default="no response from model")
    created_at = Column(String, default=datetime.utcnow)
    chat = relationship("Chat", back_populates="messages")

Base.metadata.create_all(bind=engine)

# Pydantic schemas
class MessageBase(BaseModel):
    content: str

class MessageResponse(MessageBase):
    id: int
    created_at: str
    ollama_said: str

    class Config:
        orm_mode = True

class ChatBase(BaseModel):
    title: str

class ChatResponse(ChatBase):
    id: int
    created_at: str
    messages: list[MessageResponse] = []

    class Config:
        orm_mode = True

class CreateChatResponse(BaseModel):
    id: int
    title: str

# Dependency for database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# FastAPI app


# Utility to generate chat titles
def generate_chat_title():
    return f"Chat_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

# Endpoints
@app.get('/')
def home():
    return {"message": "Hello, World!"}
## Create or Fetch Chats
@app.get("/chats/", response_model=ChatResponse)
def get_or_create_chat(new: bool = Query(False), db: Session = Depends(get_db)):
    if new:
        # Create a new chat
        title = generate_chat_title()
        new_chat = Chat(title=title)
        db.add(new_chat)
        db.commit()
        db.refresh(new_chat)
        return ChatResponse(id=new_chat.id, title=new_chat.title, created_at=new_chat.created_at, messages=[])
    else:
        # Fetch the latest chat
        latest_chat = db.query(Chat).order_by(Chat.id.desc()).first()
        if not latest_chat:
            raise HTTPException(status_code=404, detail="No existing chats found.")
        return latest_chat

## Fetch All Chats
@app.get("/chats/all/", response_model=list[CreateChatResponse])
def get_all_chats(db: Session = Depends(get_db)):
    chats = db.query(Chat).all()
    return chats


## Add Message to a Chat
# @app.post("/chats/{chat_id}/messages/", response_model=MessageResponse)
# def add_message(chat_id: int, message: MessageBase, db: Session = Depends(get_db)):
#     chat = db.query(Chat).filter(Chat.id == chat_id).first()
#     if not chat:
#         raise HTTPException(status_code=404, detail="Chat not found.")
#     new_message = Message(chat_id=chat_id, content=message.content)
#     db.add(new_message)
#     db.commit()
#     db.refresh(new_message)
#     return new_message
import ollama
@app.post("/chats/{chat_id}/messages/", response_model=MessageResponse)
def add_message(chat_id: int, message: MessageBase, db: Session = Depends(get_db)):
    # Check if the chat exists
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found.")
    
    # Save the user's message to the database
    user_message = Message(chat_id=chat_id, content=message.content)
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    # Use Ollama library to get a response from the model
    try:
        ollama_response = ollama.chat(
            model="llama3.1",  # Specify the model name
            messages=[{"role": "user", "content": message.content}]
        )
        # Extract the model's reply content, with fallback for None
        model_reply_content = ollama_response.get("message", {}).get("content", "No response from model.")
    except Exception as e:
        model_reply_content = f"Error interacting with the model: {str(e)}"
    
    # Save the model's reply to the database
    model_reply = Message(chat_id=chat_id, content=message.content, ollama_said=model_reply_content)
    db.add(model_reply)
    db.commit()
    db.refresh(model_reply)

    # Return the message response, including `ollama_said`
    return MessageResponse(
        id=user_message.id,
        content=user_message.content,
        created_at=user_message.created_at,
        ollama_said=model_reply_content
    )

## Fetch Messages from a Chat
@app.get("/chats/{chat_id}/messages/", response_model=list[MessageResponse])
def get_messages(chat_id: int, db: Session = Depends(get_db)):
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found.")
    return chat.messages

## Delete a Chat
@app.delete("/chats/{chat_id}/", status_code=204)
def delete_chat(chat_id: int, db: Session = Depends(get_db)):
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found.")
    db.delete(chat)
    db.commit()
    return

## Delete a Message
@app.delete("/messages/{message_id}/", status_code=204)
def delete_message(message_id: int, db: Session = Depends(get_db)):
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found.")
    db.delete(message)
    db.commit()
    return
