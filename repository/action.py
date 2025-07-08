from enum import IntEnum
from typing import Protocol

import bpy
from bpy.types import Action, ActionSlot, Armature, FCurve, Object, PoseBone
from mathutils import Quaternion, Vector


class ActionRepositoryProtocol(Protocol):
    take_idx: int

    @classmethod
    def get_action_name(cls) -> str:
        raise NotImplementedError()

    @classmethod
    def create_new_action(cls):
        raise NotImplementedError()

    @classmethod
    def assign_action(cls, object: Object):
        raise NotImplementedError()

    @classmethod
    def keyframe_insert(
        cls,
        object: Object,
        location: Vector,
        rotation: Quaternion,
        frame_num: int,
    ):
        raise NotImplementedError()

    @classmethod
    def cache_fcurves(cls, objects: list[Object]):
        raise NotImplementedError()


class ActionRepositoryWithSlot(ActionRepositoryProtocol):
    take_idx: int = 1

    actions: dict[str, Action] = {}
    action_slots: dict[Action, dict[Object, ActionSlot]] = {}

    @classmethod
    def get_action_name(cls) -> str:
        return f"Take{cls.take_idx}"

    @classmethod
    def create_new_action(cls):
        cls.take_idx += 1

    @classmethod
    def get_action(cls, action_name: str) -> Action:
        action = bpy.data.actions.get(action_name)
        if not action:
            action = bpy.data.actions.new(name=action_name)
            action.use_fake_user = True
        return action

    @classmethod
    def get_action_slot(cls, action: Action, object: Object) -> ActionSlot:
        action_slot = action.slots.get(object.name)
        if action_slot is None:
            action_slot = action.slots.new(id_type="OBJECT", name=object.name)
        return action_slot

    @classmethod
    def assign_action(cls, object: Object):
        if not object.animation_data:
            object.animation_data_create()
        if object.animation_data.action is None:
            object.animation_data.action = cls.get_action(cls.get_action_name())
        if object.animation_data.action_slot is None:
            object.animation_data.action_slot = cls.get_action_slot(
                object.animation_data.action,
                object,
            )


class ActionRepositoryWithoutSlot(ActionRepositoryProtocol):
    take_idx: int = 1

    @classmethod
    def get_action_name(cls) -> str:
        return f"Take{cls.take_idx}"

    @classmethod
    def create_new_action(cls):
        cls.take_idx += 1

    @classmethod
    def assign_action(cls, object: Object):
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

    @classmethod
    def keyframe_insert(
        cls,
        object: Object,
        keyframe_num: int,
    ):
        object.keyframe_insert(
            data_path="location",
            frame=keyframe_num,
        )
        object.keyframe_insert(
            data_path="rotation_quaternion",
            frame=keyframe_num,
        )


if bpy.app.version >= (4, 4, 0):
    # ActionSlot is available after blender v4.4.0
    ActionRepository: ActionRepositoryProtocol = ActionRepositoryWithSlot
else:
    ActionRepository: ActionRepositoryProtocol = ActionRepositoryWithoutSlot
