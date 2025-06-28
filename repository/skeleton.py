from dataclasses import dataclass
from typing import Any, Optional

import bpy
from bpy.types import EditBone, Object
from mathutils import Matrix, Quaternion, Vector


@dataclass
class BoneData:
    bone_id: int
    bone_name: str
    t_pose_head: Vector
    parent: Optional["BoneData"] = None

    child: Optional["BoneData"] = None

    frame_pos: Optional[Vector] = None
    frame_rot: Optional[Quaternion] = None

    _blender_frame_rot: Optional[Quaternion] = None

    transform_matrix: Optional[Matrix] = None

    def __post_init__(self):
        if self.parent is None:
            self.t_pose_head = Vector()
        if self.parent and self.parent.child is None:
            self.parent.child = self

    def set_frame_pos(self, frame_pos: Vector):
        self.frame_pos = frame_pos
        self._blender_frame_pos = None

    def set_frame_rot(self, frame_rot: Quaternion):
        self.frame_rot = frame_rot
        self._blender_frame_rot = None

    def get_blender_frame_rot(self) -> Quaternion:
        if self._blender_frame_rot is None:
            self._blender_frame_rot = self.to_blender_rot(self.frame_rot)
        return self._blender_frame_rot

    def get_global_pos(self) -> Vector:
        global_pos = self.t_pose_head
        if self.parent is not None:
            global_pos = global_pos + self.parent.get_global_pos()
        return global_pos

    def get_blender_global_pos(self) -> Vector:
        return self.to_blender_pos(self.get_global_pos())

    def to_blender_pos(self, pos: Vector) -> Vector:
        return Vector((pos.x, -pos.z, pos.y))

    def to_blender_rot(self, rot: Quaternion) -> Quaternion:
        convert3 = self.transform_matrix
        return (convert3 @ rot.to_matrix() @ convert3.inverted()).to_quaternion()

    def to_motive_pos(self, pos: Vector) -> Vector:
        return Vector((pos.x, pos.z, -pos.y))

    def set_transform_matrix(self, edit_bone: EditBone):
        bone_matrix = edit_bone.matrix

        x_axis_local = Vector((1, 0, 0))
        y_axis_local = Vector((0, 1, 0))
        z_axis_local = Vector((0, 0, 1))

        x_axis_world = self.to_motive_pos(bone_matrix.to_3x3() @ x_axis_local)
        y_axis_world = self.to_motive_pos(bone_matrix.to_3x3() @ y_axis_local)
        z_axis_world = self.to_motive_pos(bone_matrix.to_3x3() @ z_axis_local)

        self.transform_matrix = Matrix((x_axis_world, y_axis_world, z_axis_world))


@dataclass
class SkeletonData:
    skeleton_id: int
    skeleton_name: str
    bones: dict[int, BoneData]

    def append_bone(self, bone: BoneData):
        self.bones[bone.bone_id] = bone

    def get_bone_by_id(self, bone_id: int) -> BoneData:
        return self.bones[bone_id]

    def create_armature(self) -> bool:
        try:
            armature = bpy.data.armatures.new(self.skeleton_name)
            armature_object = bpy.data.objects.new(self.skeleton_name, armature)
            bpy.context.collection.objects.link(armature_object)

            bpy.context.view_layer.objects.active = armature_object

            for bone in self.bones.values():
                bpy.ops.object.mode_set(mode="EDIT")

                edit_bone = armature_object.data.edit_bones.new(bone.bone_name)

                if bone.parent is not None:
                    edit_bone_parent = armature_object.data.edit_bones.get(
                        bone.parent.bone_name
                    )
                    edit_bone.parent = edit_bone_parent

                    if bone.parent.child is bone:
                        edit_bone_parent.tail = bone.get_blender_global_pos()
                        bone.parent.set_transform_matrix(edit_bone=edit_bone_parent)

                edit_bone.roll = 0
                edit_bone.head = (
                    bone.get_blender_global_pos()
                    if bone.parent is not None
                    else Vector()
                )

                if bone.child is None:
                    edit_bone_parent = armature_object.data.edit_bones.get(
                        bone.parent.bone_name
                    )

                    direction = (
                        edit_bone_parent.tail - edit_bone_parent.head
                    ).normalized()

                    bone_length = 0.12

                    edit_bone.tail = direction * bone_length + edit_bone.head

                    bone.set_transform_matrix(edit_bone=edit_bone)

                edit_bone.use_local_location = True
                edit_bone.use_inherit_rotation = True

        except:
            raise
        else:
            return True
        finally:
            bpy.ops.object.mode_set(mode="OBJECT")

    def update_frame_data(self, data: dict[int, dict[str, Any]]):
        min_key = min(data.keys())  # TODO this is because of bone_id bug
        for bone_id in data:
            pos = Vector(data[bone_id]["pos"])
            x, y, z, w = data[bone_id]["rot"]
            rot = Quaternion((w, x, y, z))

            bone_id = bone_id - min_key + 1  # TODO this is because of bone_id bug

            bone_data = self.get_bone_by_id(bone_id=bone_id)
            bone_data.set_frame_pos(pos)
            bone_data.set_frame_rot(rot)

    def render_frame_data(
        self,
        object: Object,
        keyframe_num: Optional[int] = None,
    ):
        try:
            if keyframe_num is None:
                for bone in self.bones.values():
                    pose_bone = object.pose.bones[bone.bone_name]

                    if pose_bone.parent is None:
                        object.location = bone.to_blender_pos(bone.frame_pos)

                    pose_bone.rotation_mode = "QUATERNION"
                    pose_bone.rotation_quaternion = bone.get_blender_frame_rot()
            else:
                for bone in self.bones.values():
                    pose_bone = object.pose.bones[bone.bone_name]

                    if pose_bone.parent is None:
                        pose_bone.location = bone.frame_pos

                    pose_bone.rotation_mode = "QUATERNION"
                    pose_bone.rotation_quaternion = bone.get_blender_frame_rot()

                    pose_bone.keyframe_insert(
                        data_path="location",
                        frame=keyframe_num,
                    )
                    pose_bone.keyframe_insert(
                        data_path="rotation_quaternion",
                        frame=keyframe_num,
                    )

        except ReferenceError:
            SkeletonRepository.remove_render_object(object)


class SkeletonRepository:
    skeletons: dict[int, SkeletonData] = {}
    skeleton_name_to_id: dict[str, int] = {}  # skeleton_name, skeleton_id

    render_object_to_skeleton: dict[Object, Optional[SkeletonData]] = {}

    @classmethod
    def append_skeleton(cls, skeleton: SkeletonData) -> None:
        cls.skeletons[skeleton.skeleton_id] = skeleton
        cls.skeleton_name_to_id[skeleton.skeleton_name] = skeleton.skeleton_id

    @classmethod
    def create_armatures(cls) -> int:
        num_armatures = 0
        for skeleton in cls.skeletons.values():
            num_armatures += skeleton.create_armature()
        return num_armatures

    @classmethod
    def get_by_id(cls, skeleton_id) -> SkeletonData:
        return cls.skeletons[skeleton_id]

    @classmethod
    def update_render_object(cls, skeleton_id: str, object: Object):
        try:
            skeleton_id = int(skeleton_id)
        except:
            skeleton_id = -1

        cls.render_object_to_skeleton[object] = cls.skeletons.get(skeleton_id)

    @classmethod
    def remove_render_object(cls, object: Object):
        del SkeletonRepository.render_object_to_skeleton[object]

    @classmethod
    def clear(cls):
        cls.skeletons = {}
        cls.skeleton_name_to_id = {}

        for object in cls.render_object_to_skeleton:
            try:
                object.obj_prop.skeletons = "None"
            except:
                continue

        cls.render_object_to_skeleton = {}

    @classmethod
    def render_skeletons_and_insert_keyframe(cls, keyframe_num: Optional[int] = None):
        for object, skeleton_data in cls.render_object_to_skeleton.items():
            if skeleton_data:
                skeleton_data.render_frame_data(
                    object=object,
                    keyframe_num=keyframe_num,
                )
