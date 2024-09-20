import bpy
from .plugin_operators import ConnectOperator
from bpy.props import StringProperty, IntProperty, FloatProperty, EnumProperty, BoolProperty
from bpy.types import PropertyGroup

def get_id_names(self, context):
    enum_items = [('None', "None", "None")]

    existing_connection = ConnectOperator.connection_setup
    if existing_connection.rigid_bodies_motive:
        for id, name in existing_connection.rigid_bodies_motive.items():
            id = str(id)
            word = id + ": " + name
            enum_items.append((id, word, word)) # (identifier, name, description)
    
    return enum_items

def update_list(self, context):
    m_id = self.rigid_bodies
    current_obj = bpy.data.objects[self.obj_name]
    b_obj_id = current_obj.id_data.session_uid
    existing_conn = ConnectOperator.connection_setup

    if m_id != "None":
        m_id = int(m_id)
        existing_conn.rigid_bodies_blender[m_id] = b_obj_id
        existing_conn.rev_rigid_bodies_blender[b_obj_id] = {'obj': current_obj, 'm_ID': m_id}

class CustomObjectProperties(PropertyGroup):
    rigid_bodies : EnumProperty(name="Rigid Body", 
                                description="Assign objects in scene to rigid body IDs",
                                items=get_id_names,
                                update=update_list, options={'SKIP_SAVE'})
    
    obj_name : StringProperty(default="", options={'SKIP_SAVE'})

class CustomSceneProperties(PropertyGroup):
    server_address : StringProperty(name="Server IP",
                                    description="IP of NatNet",
                                    default="127.0.0.1")
    
    client_address : StringProperty(name="Client IP",
                                    description="IP of Blender",
                                    default="127.0.0.1")
    
    custom_recording: BoolProperty(name="Record Frame Range", default=False)