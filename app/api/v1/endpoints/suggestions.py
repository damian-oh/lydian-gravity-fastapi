from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas.suggestion import NextStepRequest, NextStepResponse
from app.services.music_theory import generate_next_step_suggestions

router = APIRouter()


@router.post("/next-steps", response_model=NextStepResponse)
async def suggest_next_steps(
    current_user: CurrentUser,
    suggestion_in: NextStepRequest,
) -> NextStepResponse:
    del current_user
    result = generate_next_step_suggestions(
        tonal_center=suggestion_in.master_tonal_center,
        mode=suggestion_in.master_mode,
        chords=[
            {
                "id": chord.id,
                "root": chord.root,
                "quality": chord.quality,
                "chord_name": chord.chord_name,
                "notes": chord.notes,
                "start_beat": chord.start_beat,
                "duration_beats": chord.duration_beats,
                "parent_mode": chord.parent_mode,
            }
            for chord in suggestion_in.active_section.chords
        ],
    )

    return NextStepResponse.model_validate(result)
