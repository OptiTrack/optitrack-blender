from enum import IntEnum
from typing import Protocol

import bpy
from bpy.types import Action, ActionFCurves, ActionSlot, FCurve, Object, PoseBone
from mathutils import Quaternion, Vector


class FCurveIndexEnum(IntEnum):
    QUATERNION_ROTATION_W = 0
    QUATERNION_ROTATION_X = 1
    QUATERNION_ROTATION_Y = 2
    QUATERNION_ROTATION_Z = 3

    LOCATION_X = 4
    LOCATION_Y = 5
    LOCATION_Z = 6

    def get_keyframe_value(self, pose_bone: PoseBone) -> float:
        if self >= 4:
            value = pose_bone.location[self - 4]
        else:
            value = pose_bone.rotation_quaternion[self]
        return value


class ActionRepositoryProtocol(Protocol):
    take_idx: int

    fcurves: dict[Object, dict[PoseBone, dict[FCurveIndexEnum, FCurve]]] = {}

    @classmethod
    def get_action_name(cls) -> str:
        raise NotImplementedError()

    @classmethod
    def create_new_action(cls):
        raise NotImplementedError()

    @classmethod
    def cache_fcurves(cls, objects: list[Object]):
        raise NotImplementedError()

    @classmethod
    def assign_action(cls, object: Object):
        raise NotImplementedError()

    @classmethod
    def get_fcurves(cls, object: Object) -> ActionFCurves:
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


class ActionRepositoryBase(ActionRepositoryProtocol):
    @classmethod
    def get_action_name(cls) -> str:
        return f"Take{cls.take_idx}"

    @classmethod
    def create_new_action(cls):
        cls.take_idx += 1

    @classmethod
    def cache_fcurves(cls, objects: list[Object]):

        cls.fcurves = {}
        for object in objects:
            cls.assign_action(object)

            fcurves = cls.get_fcurves(object=object)

            pose_bone_to_fcurves: dict[PoseBone, dict[FCurveIndexEnum, FCurve]] = {}
            for pose_bone in object.pose.bones:
                pose_bone_fcurves: dict[FCurveIndexEnum, FCurve] = {}
                if pose_bone.parent is not None and pose_bone.parent.parent is None:
                    data_path = f'pose.bones["{pose_bone.name}"].location'
                    for fcurve_index_enum in [
                        FCurveIndexEnum.LOCATION_X,
                        FCurveIndexEnum.LOCATION_Y,
                        FCurveIndexEnum.LOCATION_Z,
                    ]:
                        index = fcurve_index_enum - FCurveIndexEnum.LOCATION_X
                        fcurve = fcurves.find(
                            data_path=data_path,
                            index=index,
                        )
                        if fcurve is None:
                            fcurve = fcurves.new(
                                data_path=data_path,
                                index=index,
                            )
                        pose_bone_fcurves[fcurve_index_enum] = fcurve
                data_path = f'pose.bones["{pose_bone.name}"].rotation_quaternion'
                for fcurve_index_enum in [
                    FCurveIndexEnum.QUATERNION_ROTATION_W,
                    FCurveIndexEnum.QUATERNION_ROTATION_X,
                    FCurveIndexEnum.QUATERNION_ROTATION_Y,
                    FCurveIndexEnum.QUATERNION_ROTATION_Z,
                ]:
                    index = fcurve_index_enum
                    fcurve = fcurves.find(
                        data_path=data_path,
                        index=index,
                    )
                    if fcurve is None:
                        fcurve = fcurves.new(
                            data_path=data_path,
                            index=index,
                        )
                    pose_bone_fcurves[fcurve_index_enum] = fcurve
                pose_bone_to_fcurves[pose_bone] = pose_bone_fcurves
            cls.fcurves[object] = pose_bone_to_fcurves


class ActionRepositoryWithSlot(ActionRepositoryBase):
    take_idx: int = 1

    fcurves: dict[Object, dict[PoseBone, dict[FCurveIndexEnum, FCurve]]] = {}

    @classmethod
    def get_fcurves(cls, object: Object) -> ActionFCurves:
        action = object.animation_data.action
        action_slot = object.animation_data.action_slot

        if not action.layers:
            action.layers.new("Layer")
        layer = action.layers[0]

        if not layer.strips:
            layer.strips.new(type="KEYFRAME")
        strip = layer.strips[0]

        channelbag = strip.channelbag(action_slot, ensure=True)

        return channelbag.fcurves

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


class ActionRepositoryWithoutSlot(ActionRepositoryBase):
    take_idx: int = 1

    fcurves: dict[Object, dict[PoseBone, dict[FCurveIndexEnum, FCurve]]] = {}

    @classmethod
    def get_fcurves(cls, object: Object) -> ActionFCurves:
        return object.animation_data.action.fcurves

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
