from fastapi import APIRouter, Depends
from app.core.dependencies import get_profile_service
from app.core.get_current_user import get_current_user
from app.models.user import User
from app.schemas.profile import ProfileSave, ProfileResponse
from app.services.profile_service import ProfileService

router = APIRouter(prefix='/profile', tags=['Profile'])


@router.get('', response_model=ProfileResponse)
def get_profile(current_user: User = Depends(get_current_user), service: ProfileService = Depends(get_profile_service)):
    return service.get(current_user.id)


@router.put('', response_model=ProfileResponse)
def save_profile(request: ProfileSave, current_user: User = Depends(get_current_user), service: ProfileService = Depends(get_profile_service)):
    return service.save(current_user.id, request)
