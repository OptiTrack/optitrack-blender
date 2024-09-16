import bpy
from bpy.app.handlers import persistent
from .plugin_operators import ConnectOperator
from .property_definitions import CustomObjectProperties

@persistent
def object_prop_handler(scene):
    for scene in bpy.data.scenes:    
        for obj in scene.objects:
            if not hasattr(obj, "obj_prop"):
                obj.obj_prop = bpy.props.PointerProperty(type=CustomObjectProperties)
            obj.obj_prop.obj_name = obj.name

@persistent
def object_deleted_handler(scene):
    if bpy.context.window_manager.operators:
        last_operator = bpy.context.window_manager.operators[-1].bl_idname
        if last_operator == "OBJECT_OT_delete" or last_operator == "OUTLINER_OT_delete":
            if bpy.context.window_manager.connection_status == True:
                existing_connection = ConnectOperator.connection_setup
                deleted_ids = []
                for obj in existing_connection.rev_rigid_bodies_blender:
                    if str(obj) == "<bpy_struct, Object invalid>":
                        deleted_ids.append(existing_connection.rev_rigid_bodies_blender[obj])
                
                if deleted_ids:
                    for id in deleted_ids:
                        del existing_connection.rev_rigid_bodies_blender[existing_connection.rigid_bodies_blender[id]]
                        del existing_connection.rigid_bodies_blender[id]
                        print("Object deleted, ID: ", id)

@persistent
def model_change_handler(scene):
    if ConnectOperator.connection_setup is not None:  
        existing_connection = ConnectOperator.connection_setup
        if existing_connection.streaming_client is not None:
            if existing_connection.indicate_model_changed == True:
                print("True")
                bpy.context.window_manager.connection_status = False
                existing_connection.streaming_client.shutdown()
                existing_connection.reset_to_initial()
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

@persistent
def load_handler(dummy):
    print("handler loaded")
    if ConnectOperator.connection_setup is not None:    
        existing_connection = ConnectOperator.connection_setup
        if existing_connection.streaming_client is not None:
            existing_connection.streaming_client.shutdown()
            existing_connection.reset_to_initial()
        
            for attr in dir(bpy.data):
                if "bpy_prop_collection" in str(type(getattr(bpy.data, attr))):
                    for obj in getattr(bpy.data, attr):
                        for custom_prop_name in list(obj.keys()):
                            del obj[custom_prop_name]

            bpy.ops.object.select_all(action='DESELECT')