"""Messages router for Iskra"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List

from app.models import get_db
from app.models.user import User, Message
from app.schemas import MessageCreate, MessageResponse
from app.routers.auth import get_current_user
from app.services import encrypt_message, decrypt_message

router = APIRouter()

# Active WebSocket connections
active_connections = {}

@router.get("/conversations")
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get unique conversation partners
    sent = db.query(Message).filter(Message.sender_id == current_user.id).all()
    received = db.query(Message).filter(Message.receiver_id == current_user.id).all()

    partners = set()
    for m in sent:
        partners.add(m.receiver_id)
    for m in received:
        partners.add(m.sender_id)

    conversations = []
    for partner_id in partners:
        partner = db.query(User).filter(User.id == partner_id).first()
        if partner:
            last_message = db.query(Message).filter(
                ((Message.sender_id == current_user.id) & (Message.receiver_id == partner_id)) |
                ((Message.sender_id == partner_id) & (Message.receiver_id == current_user.id))
            ).order_by(Message.created_at.desc()).first()

            unread = db.query(Message).filter(
                Message.sender_id == partner_id,
                Message.receiver_id == current_user.id,
                Message.is_read == False
            ).count()

            conversations.append({
                "user": {
                    "id": partner.id,
                    "username": partner.username,
                    "display_name": partner.display_name,
                    "avatar_url": partner.avatar_url,
                    "iskra_id": partner.iskra_id,
                    "is_online": partner.is_online
                },
                "last_message": {
                    "content": last_message.content_encrypted if last_message else None,
                    "created_at": last_message.created_at.isoformat() if last_message else None,
                    "is_from_me": last_message.sender_id == current_user.id if last_message else None
                },
                "unread_count": unread
            })

    conversations.sort(key=lambda x: x["last_message"]["created_at"] if x["last_message"]["created_at"] else "", reverse=True)
    return conversations

@router.get("/history/{user_id}", response_model=List[MessageResponse])
async def get_message_history(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    messages = db.query(Message).filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.created_at.asc()).limit(100).all()

    # Mark as read
    for m in messages:
        if m.receiver_id == current_user.id and not m.is_read:
            m.is_read = True
    db.commit()

    return [MessageResponse.model_validate(m) for m in messages]

@router.post("/send", response_model=MessageResponse)
async def send_message(
    message: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    receiver = db.query(User).filter(User.id == message.receiver_id).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="User not found")

    # Encrypt message (simplified E2EE)
    encrypted = encrypt_message(message.content, receiver.public_key.encode())

    db_message = Message(
        sender_id=current_user.id,
        receiver_id=message.receiver_id,
        content_encrypted=encrypted
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)

    # Send via WebSocket if online
    if message.receiver_id in active_connections:
        await active_connections[message.receiver_id].send_json({
            "type": "new_message",
            "sender_id": current_user.id,
            "sender_name": current_user.display_name or current_user.username,
            "message_id": db_message.id
        })

    return MessageResponse.model_validate(db_message)

# WebSocket for real-time messaging
@router.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str, db: Session = Depends(get_db)):
    from app.services import verify_token

    payload = verify_token(token)
    if not payload:
        await websocket.close(code=4001)
        return

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    active_connections[user_id] = websocket
    user.is_online = True
    db.commit()

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif data.get("type") == "typing":
                receiver_id = data.get("receiver_id")
                if receiver_id in active_connections:
                    await active_connections[receiver_id].send_json({
                        "type": "typing",
                        "user_id": user_id
                    })
    except WebSocketDisconnect:
        if user_id in active_connections:
            del active_connections[user_id]
        user.is_online = False
        db.commit()
    except Exception:
        if user_id in active_connections:
            del active_connections[user_id]
        user.is_online = False
        db.commit()
