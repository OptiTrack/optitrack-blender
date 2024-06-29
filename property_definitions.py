import bpy
from bpy.props import StringProperty, IntProperty, FloatProperty, EnumProperty, BoolProperty
from bpy.types import PropertyGroup, Object

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
    bpy.context.scene.render.fps = bpy.context.scene.init_prop.frame_value

def get_ids(self, context):
    enum_items = [('None', 'Null', 'None')]

    # for name in 

class Initializer(PropertyGroup):
    server_address : StringProperty(name="Server IP",
                                    description="IP of NatNet",
                                    default="127.0.0.1")
    
    client_address : StringProperty(name="Client IP",
                                    description="IP of Blender",
                                    default="127.0.0.1")

    unit_setting : EnumProperty(name="Unit system",
                                    description="change unit settings",
                                    default='Metric',
                                    update=update_unit_settings,
                                    items= [('None', "None", "Adaptive"),
                                            ('Metric', "Metric", "meters, kilogram"),
                                            ('Imperial', "Imperial", "feet, pound")
                                            ])
    
    scale : FloatProperty(name="Unit Scale", default=1, update=update_unit_scale, precision=3)
    
    fps_value : IntProperty(name="Frame Rate", default=120, 
                                      min=1, max=1000)
    
    desired_object : EnumProperty(name="Object",
                                        description="shape of rigid body of your choice",
                                        default='UV Sphere',
                                        items=[('UV Sphere', "UV Sphere", ""),
                                                ('Cube', "Cube", ""),
                                               ('Ico Sphere', "Ico Sphere", ""),
                                               ('Cylinder', "Cylinder", ""),
                                               ('Cone', "Cone", "")
                                               ])
    
    default_settings: BoolProperty(name="Keep configuration", 
                                   description="Configure scene to above settings",
                                   default=True)

    rigid_bodies : EnumProperty(name="Rigid Body", 
                                description="Assign objects in scene rigid body IDs",
                                items=get_ids,
                                update=)