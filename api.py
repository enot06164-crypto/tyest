"""Main API router for Iskra"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List, Optional

from app.models import get_db
from app.models.user import User, Post, Comment, Like, friendships, FriendRequest, Group, GroupMember
from app.schemas import (
    UserResponse, PostResponse, PostCreate, CommentCreate, CommentResponse,
    GroupCreate, GroupResponse, SearchResult, FriendRequestCreate, FriendRequestResponse
)
from app.routers.auth import get_current_user, get_current_user_optional

router = APIRouter()

# Users API
@router.get("/users/search", response_model=List[UserResponse])
async def search_users(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    users = db.query(User).filter(
        or_(
            User.username.ilike(f"%{q}%"),
            User.iskra_id == q,
            User.display_name.ilike(f"%{q}%")
        )
    ).limit(20).all()
    return [UserResponse.model_validate(u) for u in users]

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        or_(User.id == user_id, User.iskra_id == user_id, User.username == user_id)
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)

@router.get("/users/{user_id}/posts", response_model=List[PostResponse])
async def get_user_posts(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    user = db.query(User).filter(
        or_(User.id == user_id, User.iskra_id == user_id, User.username == user_id)
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    posts = db.query(Post).filter(Post.author_id == user.id).order_by(Post.created_at.desc()).all()
    return [PostResponse.model_validate(p) for p in posts]

# Friends API
@router.post("/friends/request", response_model=FriendRequestResponse)
async def send_friend_request(
    request: FriendRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if request.receiver_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot send request to yourself")

    receiver = db.query(User).filter(User.id == request.receiver_id).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if already friends
    if receiver in current_user.friends:
        raise HTTPException(status_code=400, detail="Already friends")

    # Check if request already exists
    existing = db.query(FriendRequest).filter(
        FriendRequest.sender_id == current_user.id,
        FriendRequest.receiver_id == request.receiver_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Request already sent")

    friend_request = FriendRequest(sender_id=current_user.id, receiver_id=request.receiver_id)
    db.add(friend_request)
    db.commit()
    db.refresh(friend_request)
    return FriendRequestResponse.model_validate(friend_request)

@router.post("/friends/accept/{request_id}")
async def accept_friend_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    req = db.query(FriendRequest).filter(
        FriendRequest.id == request_id,
        FriendRequest.receiver_id == current_user.id
    ).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    sender = db.query(User).filter(User.id == req.sender_id).first()
    current_user.friends.append(sender)
    sender.friends.append(current_user)
    req.status = "accepted"
    db.commit()
    return {"message": "Friend request accepted"}

@router.post("/friends/reject/{request_id}")
async def reject_friend_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    req = db.query(FriendRequest).filter(
        FriendRequest.id == request_id,
        FriendRequest.receiver_id == current_user.id
    ).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    req.status = "rejected"
    db.commit()
    return {"message": "Friend request rejected"}

@router.get("/friends/requests", response_model=List[FriendRequestResponse])
async def get_friend_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    requests = db.query(FriendRequest).filter(
        FriendRequest.receiver_id == current_user.id,
        FriendRequest.status == "pending"
    ).all()
    return [FriendRequestResponse.model_validate(r) for r in requests]

@router.get("/friends", response_model=List[UserResponse])
async def get_friends(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return [UserResponse.model_validate(f) for f in current_user.friends]

@router.delete("/friends/{friend_id}")
async def remove_friend(
    friend_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    friend = db.query(User).filter(User.id == friend_id).first()
    if not friend or friend not in current_user.friends:
        raise HTTPException(status_code=404, detail="Friend not found")

    current_user.friends.remove(friend)
    friend.friends.remove(current_user)
    db.commit()
    return {"message": "Friend removed"}

# Posts API
@router.post("/posts", response_model=PostResponse)
async def create_post(
    post: PostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_post = Post(**post.model_dump(), author_id=current_user.id)
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return PostResponse.model_validate(db_post)

@router.get("/posts", response_model=List[PostResponse])
async def get_feed(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    friend_ids = [f.id for f in current_user.friends] + [current_user.id]
    posts = db.query(Post).filter(
        or_(
            Post.author_id.in_(friend_ids),
            Post.is_public == True
        )
    ).order_by(Post.created_at.desc()).limit(50).all()
    return [PostResponse.model_validate(p) for p in posts]

@router.get("/posts/{post_id}", response_model=PostResponse)
async def get_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return PostResponse.model_validate(post)

@router.post("/posts/{post_id}/like")
async def like_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    existing = db.query(Like).filter(
        Like.post_id == post_id,
        Like.user_id == current_user.id
    ).first()

    if existing:
        db.delete(existing)
        post.likes_count -= 1
    else:
        like = Like(post_id=post_id, user_id=current_user.id)
        db.add(like)
        post.likes_count += 1

    db.commit()
    return {"liked": existing is None, "likes_count": post.likes_count}

@router.post("/posts/{post_id}/comments", response_model=CommentResponse)
async def add_comment(
    post_id: int,
    comment: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    db_comment = Comment(**comment.model_dump(), post_id=post_id, author_id=current_user.id)
    db.add(db_comment)
    post.comments_count += 1
    db.commit()
    db.refresh(db_comment)
    return CommentResponse.model_validate(db_comment)

@router.get("/posts/{post_id}/comments", response_model=List[CommentResponse])
async def get_comments(post_id: int, db: Session = Depends(get_db)):
    comments = db.query(Comment).filter(Comment.post_id == post_id).order_by(Comment.created_at.desc()).all()
    return [CommentResponse.model_validate(c) for c in comments]

# Groups API
@router.post("/groups", response_model=GroupResponse)
async def create_group(
    group: GroupCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_group = Group(**group.model_dump(), owner_id=current_user.id)
    db.add(db_group)
    db.commit()
    db.refresh(db_group)

    # Add owner as member
    member = GroupMember(group_id=db_group.id, user_id=current_user.id, is_admin=True)
    db.add(member)
    db.commit()

    return GroupResponse.model_validate(db_group)

@router.get("/groups", response_model=List[GroupResponse])
async def list_groups(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    groups = db.query(Group).filter(Group.is_public == True).all()
    result = []
    for g in groups:
        gr = GroupResponse.model_validate(g)
        if current_user:
            member = db.query(GroupMember).filter(
                GroupMember.group_id == g.id,
                GroupMember.user_id == current_user.id
            ).first()
            if member:
                gr.is_member = True
                gr.is_admin = member.is_admin
        result.append(gr)
    return result

@router.get("/groups/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    gr = GroupResponse.model_validate(group)
    if current_user:
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.id
        ).first()
        if member:
            gr.is_member = True
            gr.is_admin = member.is_admin
    return gr

@router.post("/groups/{group_id}/join")
async def join_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    existing = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already a member")

    member = GroupMember(group_id=group_id, user_id=current_user.id)
    db.add(member)
    group.members_count += 1
    db.commit()
    return {"message": "Joined group"}

@router.post("/groups/{group_id}/leave")
async def leave_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == current_user.id
    ).first()
    if not member:
        raise HTTPException(status_code=400, detail="Not a member")

    group = db.query(Group).filter(Group.id == group_id).first()
    db.delete(member)
    group.members_count -= 1
    db.commit()
    return {"message": "Left group"}

# Search API
@router.get("/search", response_model=SearchResult)
async def search(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    users = db.query(User).filter(
        or_(
            User.username.ilike(f"%{q}%"),
            User.iskra_id == q,
            User.display_name.ilike(f"%{q}%")
        )
    ).limit(10).all()

    groups = db.query(Group).filter(
        or_(
            Group.name.ilike(f"%{q}%"),
            Group.description.ilike(f"%{q}%")
        ),
        Group.is_public == True
    ).limit(10).all()

    return SearchResult(
        users=[UserResponse.model_validate(u) for u in users],
        groups=[GroupResponse.model_validate(g) for g in groups]
    )
