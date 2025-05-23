import bpy
from .plugin_operators import ConnectOperator
from bpy.props import StringProperty, IntProperty, FloatProperty, EnumProperty, BoolProperty
from bpy.types import PropertyGroup

def update_unit_settings(self, context):
    initprop = bpy.context.scene.init_prop
    if initprop.unit_setting == 'None':
        bpy.context.scene.unit_settings.system = 'NONE'
    elif initprop.unit_setting == 'Metric':
        bpy.context.scene.unit_settings.system = 'METRIC'
    elif initprop.unit_setting == 'Imperial':
        bpy.context.scene.unit_settings.system = 'IMPERIAL'

def update_unit_scale(self, context):
    bpy.context.scene.unit_settings.scale_length = bpy.context.scene.init_prop.scale

def update_frame_rate(self, context):
    bpy.context.scene.render.fps = bpy.context.scene.init_prop.fps_value

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
    id = self.rigid_bodies
    current_obj = bpy.data.objects[self.obj_name]
    existing_conn = ConnectOperator.connection_setup
    if current_obj in existing_conn.rev_rigid_bodies_blender:
        del existing_conn.rigid_bodies_blender[existing_conn.rev_rigid_bodies_blender[current_obj]]
        del existing_conn.rev_rigid_bodies_blender[current_obj]

    if id != "None":
        id = int(id)
        if id in existing_conn.rigid_bodies_blender:
            del existing_conn.rev_rigid_bodies_blender[existing_conn.rigid_bodies_blender[id]]
            del existing_conn.rigid_bodies_blender[id]
        
        existing_conn.rigid_bodies_blender[id] = current_obj
        existing_conn.rev_rigid_bodies_blender[current_obj] = id

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

    unit_setting : EnumProperty(name="Unit System",
                                    description="change unit settings",
                                    default='Metric',
                                    update=update_unit_settings,
                                    items= [('None', "None", "Adaptive"),
                                            ('Metric', "Metric", "meters, kilogram"),
                                            ('Imperial', "Imperial", "feet, pound")
                                            ])
    
    scale : FloatProperty(name="Unit Scale", default=1, update=update_unit_scale, precision=3)
    
    fps_value : IntProperty(name="Frame Rate", default=120, min=1, max=1000, update=update_frame_rate)
    
    default_settings: BoolProperty(name="Apply Configuration", 
                                   description="Unit System, Unit Scale and Frame Rate settings in this panel will override Blender's settings. Enable Apply Configuration to confirm and overwrite Blenders settings",
                                   default=True)
    
    custom_recording: BoolProperty(name="Record Frame Range", default=False)