import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
)
from bpy.types import PropertyGroup

from .plugin_operators import ConnectOperator
from .repository.skeleton import SkeletonRepository


def get_rb_id_names(self, context):
    enum_items = [("None", "None", "None")]

    existing_connection = ConnectOperator.connection_setup
    if existing_connection.assets_motive:
        rb_dict = existing_connection.assets_motive["rb_desc"]
        for id, name in rb_dict.items():
            id = str(id)
            word = id + ": " + name["name"]
            enum_items.append((id, word, word))  # (identifier, name, description)

    return enum_items


def update_rb_list(self, context):
    m_id = self.rigid_bodies
    current_obj = bpy.data.objects[self.obj_name]
    b_obj_id = current_obj.id_data.session_uid
    existing_conn = ConnectOperator.connection_setup

    if m_id != "None":
        m_id = int(m_id)
        if "rigid_body" in existing_conn.assets_blender:
            existing_conn.assets_blender["rigid_body"][m_id] = {"b_ID": b_obj_id}
        else:
            existing_conn.assets_blender["rigid_body"] = {}
            existing_conn.assets_blender["rigid_body"][m_id] = {"b_ID": b_obj_id}
        # existing_conn.rev_assets_blender[b_obj_id] = {'obj': current_obj, 'm_ID': m_id, \
        #                                                      'asset_type': 'rigid_body'}
        existing_conn.rev_assets_blender[b_obj_id]["m_ID"] = m_id
    else:
        rev_m_id = existing_conn.rev_assets_blender[b_obj_id]["m_ID"]
        if rev_m_id != "None":
            del existing_conn.assets_blender["rigid_body"][rev_m_id]
            existing_conn.rev_assets_blender[b_obj_id]["m_ID"] = "None"
    # print("assets_blender: ", existing_conn.assets_blender)
    # print("rev_assets_blender: ", existing_conn.rev_assets_blender)


def get_skeleton_id_names(self, context):
    enum_items = [("None", "None", "None")]

    existing_connection = ConnectOperator.connection_setup
    if existing_connection.assets_motive:
        ske_dict = existing_connection.assets_motive["ske_desc"]
        for id, name in ske_dict.items():
            id = str(id)
            word = id + ": " + name["name"]
            enum_items.append((id, word, word))  # (identifier, name, description)

    return enum_items


def update_skeleton_list(self, context):
    m_id = self.skeletons
    current_obj = bpy.data.objects[self.obj_name]
    b_obj_id = current_obj.id_data.session_uid
    existing_conn = ConnectOperator.connection_setup

    if m_id != "None":
        m_id = int(m_id)
        if "skeleton" in existing_conn.assets_blender:
            existing_conn.assets_blender["skeleton"][m_id] = {}
            existing_conn.assets_blender["skeleton"][m_id]["b_ID"] = b_obj_id
            existing_conn.assets_blender["skeleton"][m_id]["ske_rb_map"] = {}
        else:
            existing_conn.assets_blender["skeleton"] = {}
            existing_conn.assets_blender["skeleton"][m_id] = {}
            existing_conn.assets_blender["skeleton"][m_id]["b_ID"] = b_obj_id
            existing_conn.assets_blender["skeleton"][m_id]["ske_rb_map"] = {}

        existing_conn.rev_assets_blender[b_obj_id]["m_ID"] = m_id

        ske_rb_map = create_ble_ske_mapping(
            m_id, b_obj_id, existing_conn.assets_motive, current_obj
        )
        existing_conn.assets_blender["skeleton"][m_id]["ske_rb_map"] = ske_rb_map

    else:
        rev_m_id = existing_conn.rev_assets_blender[b_obj_id]["m_ID"]
        if rev_m_id != "None":
            # del existing_conn.assets_blender["skeleton"][rev_m_id]
            existing_conn.rev_assets_blender[b_obj_id]["m_ID"] = "None"

    SkeletonRepository.update_render_object(skeleton_id=m_id, object=current_obj)


def create_ble_ske_mapping(m_id, b_id, m_data_dict, b_obj):
    ske_rb_map = {}
    obj = b_obj

    if obj.type == "ARMATURE":
        armature = obj.data

        ske_rb_map["m_to_b"] = {}
        ske_rb_map["b_to_m"] = {}
        ske_rb_map["b_to_m_pos"] = {}  # added

        for bone in armature.bones:
            if bone.name in m_data_dict["ske_desc"][m_id]["rb_name"]:
                m_rb_id = m_data_dict["ske_desc"][m_id]["rb_name"][bone.name]["id"]
                m_rb_pos = m_data_dict["ske_desc"][m_id]["rb_name"][bone.name]["pos"]
                ske_rb_map["m_to_b"][m_rb_id] = bone.name
                ske_rb_map["b_to_m"][bone.name] = m_rb_id
                ske_rb_map["b_to_m_pos"][bone.name] = m_rb_pos  # added
            else:
                print(bone.name, " not in Motive Skeleton.")

        # print("m_to_b", ske_rb_map['m_to_b'])
        # print("b_to_m", ske_rb_map['b_to_m'])
    return ske_rb_map


class CustomObjectProperties(PropertyGroup):
    rigid_bodies: EnumProperty(
        name="Rigid Body",
        description="Assign objects in scene to rigid body IDs",
        items=get_rb_id_names,
        update=update_rb_list,
        options={"SKIP_SAVE"},
    )

    skeletons: EnumProperty(
        name="Skeleton",
        description="Assign objects in scene to skeleton IDs",
        items=get_skeleton_id_names,
        update=update_skeleton_list,
        options={"SKIP_SAVE"},
    )

    obj_name: StringProperty(default="", options={"SKIP_SAVE"})


class CustomSceneProperties(PropertyGroup):
    server_address: StringProperty(
        name="Server IP", description="IP of NatNet", default="127.0.0.1"
    )

    client_address: StringProperty(
        name="Client IP", description="IP of Blender", default="127.0.0.1"
    )

    custom_recording: BoolProperty(name="Record Frame Range", default=False)
