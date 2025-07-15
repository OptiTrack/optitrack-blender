from bpy.types import Operator

from .repository.skeleton import SkeletonRepository


class MotiveArmatureOperator(Operator):
    bl_idname = "wm.add_armature"
    bl_description = "Add Human Meta-Rig with Motive's Skeleton Data"
    bl_label = "Add Motive Armature"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        SkeletonRepository.create_armatures()
        return {"FINISHED"}
