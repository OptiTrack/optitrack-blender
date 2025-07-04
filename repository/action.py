import bpy
from bpy.types import Action, Object


class ActionRepository:
    take_idx: int = 1

    @classmethod
    def get_action_name(cls) -> str:
        return f"Take{cls.take_idx}"

    @classmethod
    def create_new_action(cls):
        cls.take_idx += 1

    @classmethod
    def set_action(cls, object: Object):
        action_name = f"{object.name}.{ActionRepository.get_action_name()}"
        if not object.animation_data:
            object.animation_data_create()
        if (
            not object.animation_data.action
            or object.animation_data.action.name != action_name
        ):
            action = bpy.data.actions.get(action_name)
            if action is None:
                action = bpy.data.actions.new(action_name)
                action.use_fake_user = True
            object.animation_data.action = action
