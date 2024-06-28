import bpy
from bpy.app.handlers import persistent
from .connection_operator import ConnectButtonOperator
from queue import Queue
from threading import Lock

def reset_to_default(scene):
    for scene in bpy.data.scenes:
        initprop = scene.init_prop
        if initprop.default_settings and initprop.unit_setting == initprop.bl_rna.properties['unit_setting'].default:
            initprop.unit_setting = initprop.bl_rna.properties['unit_setting'].default
        
        if initprop.default_settings and initprop.scale == initprop.bl_rna.properties['scale'].default:
            initprop.scale = initprop.bl_rna.properties['scale'].default
        
        if initprop.default_settings and initprop.fps_value == initprop.bl_rna.properties['fps_value'].default:
            initprop.fps_value = initprop.bl_rna.properties['fps_value'].default
        
        if initprop.default_settings and initprop.desired_object == initprop.bl_rna.properties['default_settings'].default:
            initprop.desired_object = initprop.bl_rna.properties['default_settings'].default

@persistent
def object_deleted_handler(scene):
    if bpy.context.window_manager.operators:
        last_operator = bpy.context.window_manager.operators[-1].bl_idname
        if last_operator == "OBJECT_OT_delete" or last_operator == "OUTLINER_OT_delete":
            if bpy.context.window_manager.connection_status == True:
                existing_connection = ConnectButtonOperator.connection_setup
                deleted_ids = []
                for id in existing_connection.rigid_bodies:
                    if str(existing_connection.rigid_bodies[id]) == "<bpy_struct, Object invalid>":
                        deleted_ids.append(id)    
                
                if deleted_ids:
                    for id in deleted_ids:
                        del existing_connection.rev_rigid_bodies[existing_connection.rigid_bodies[id]]
                        del existing_connection.rigid_bodies[id]
                        print("Object deleted, ID: ", id)

@persistent
def model_change_handler(scene):
    if ConnectButtonOperator.connection_setup is not None:  
        existing_connection = ConnectButtonOperator.connection_setup
        if existing_connection.streaming_client is not None:
            print("existing indicate: ", existing_connection.indicate_model_changed)        
            if existing_connection.indicate_model_changed == True:
                print("False to True!")
                bpy.context.window_manager.connection_status = False
                existing_connection.streaming_client.shutdown()
                existing_connection.reset_to_initial()    

                # print("Initial values: ")
                # print("rigid_body_ids", len(existing_connection.rigid_body_ids))
                # print("rigid_bodies", len(existing_connection.rigid_bodies))
                existing_connection = None
    
                for attr in dir(bpy.data):
                    if "bpy_prop_collection" in str(type(getattr(bpy.data, attr))):
                        for obj in getattr(bpy.data, attr):
                            for custom_prop_name in list(obj.keys()):
                                del obj[custom_prop_name]

                # Deselect all objects
                bpy.ops.object.select_all(action='DESELECT')

                # Delete all custom properties
                scene = bpy.context.scene
                # Iterate over all custom properties in the scene
                for prop_name in list(scene.keys()):
                    if scene[prop_name].is_property:
                        del scene[prop_name]
                        print(f"Deleted custom scene property '{prop_name}'")

@persistent
def load_handler(dummy):
    print("handler loaded")
    if ConnectButtonOperator.connection_setup is not None:    
        existing_connection = ConnectButtonOperator.connection_setup
        if existing_connection.streaming_client is not None:
            existing_connection.streaming_client.shutdown()
            existing_connection.reset_to_initial()
        
            for attr in dir(bpy.data):
                if "bpy_prop_collection" in str(type(getattr(bpy.data, attr))):
                    for obj in getattr(bpy.data, attr):
                        for custom_prop_name in list(obj.keys()):
                            del obj[custom_prop_name]

            # Deselect all objects
            bpy.ops.object.select_all(action='DESELECT')

