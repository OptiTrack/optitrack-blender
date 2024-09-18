import bpy
from bpy.app.handlers import persistent
from .plugin_operators import ConnectOperator
from .property_definitions import CustomObjectProperties

@persistent
def object_handler(scene):
    if bpy.context.window_manager.connection_status == True:
        existing_connection = ConnectOperator.connection_setup
        if bpy.context.window_manager.operators:
            last_operator = bpy.context.window_manager.operators[-1].bl_idname
            if last_operator == "OBJECT_OT_delete" or last_operator == "OUTLINER_OT_delete":    
                deleted_ids = []
                for key in existing_connection.rev_rigid_bodies_blender:
                    if str(existing_connection.rev_rigid_bodies_blender[key]['obj']) == "<bpy_struct, Object invalid>":
                        deleted_ids.append(key)
                
                if deleted_ids:
                    for id in deleted_ids:
                        if existing_connection.rev_rigid_bodies_blender[id]['m_ID'] == None:
                            del existing_connection.rev_rigid_bodies_blender[id]
                        else:
                            del existing_connection.rigid_bodies_blender[existing_connection.rev_rigid_bodies_blender[id]['m_ID']]
                            del existing_connection.rev_rigid_bodies_blender[id]
                        print("Object deleted, ID: ", id)
        
        for obj in bpy.data.objects:
            if obj.id_data.session_uid not in existing_connection.rev_rigid_bodies_blender:
                existing_connection.rev_rigid_bodies_blender[obj.id_data.session_uid] = {'obj': obj, 'm_ID': None}
            else:
                existing_connection.rev_rigid_bodies_blender[obj.id_data.session_uid]['obj'] = obj
            
            if not hasattr(obj, "obj_prop"):
                obj.obj_prop = bpy.props.PointerProperty(type=CustomObjectProperties)
            obj.obj_prop.obj_name = obj.name

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