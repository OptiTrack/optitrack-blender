import bpy
from bpy.app.handlers import persistent
from .plugin_operators import ConnectOperator
from .property_definitions import CustomObjectProperties

@persistent
def object_handler(scene):
    if bpy.context.window_manager.connection_status == True:
        existing_conn = ConnectOperator.connection_setup
        # print("inside handler: ", existing_conn.assets_motive)
        # if bpy.context.window_manager.operators:
        #     last_operator = bpy.context.window_manager.operators[-1].bl_idname
        #     if last_operator == "OBJECT_OT_delete" or last_operator == "OUTLINER_OT_delete": # check if any object is deleted with the scene update
        deleted_ids = []
        for key in existing_conn.rev_assets_blender:
            if str(existing_conn.rev_assets_blender[key]['obj']) == "<bpy_struct, Object invalid>":
                deleted_ids.append((key, existing_conn.rev_assets_blender[key]['m_ID'], \
                                    existing_conn.rev_assets_blender[key]['asset_type']))
        
        if deleted_ids:
            for id in deleted_ids: # if object deleted, update the dictionaries accordingly
                if id[1] == None:
                    del existing_conn.rev_assets_blender[id[0]]
                else:
                    if id[2] in existing_conn.assets_blender:
                        if id[1] in existing_conn.assets_blender[id[2]]:
                            del existing_conn.assets_blender[id[2]][id[1]]
                    del existing_conn.rev_assets_blender[id[0]]
                print("Object deleted, ID: ", id)
        
        for obj in bpy.data.objects: # update the dictionary every time the scene updates
            uid = obj.id_data.session_uid # session-wide identifier for the data block
            if obj.type == 'MESH':
                 asset_type = 'rigid_body'
            elif obj.type == 'ARMATURE':
                 asset_type = 'skeleton'
            else:
                asset_type = obj.type
            # print("inside object_handler: ", existing_connection.assets_motive)
            # print("asset: ", obj.name, " ", obj.type, " ", asset)
            if uid not in existing_conn.rev_assets_blender:
                existing_conn.rev_assets_blender[uid] = {'obj': obj, 'm_ID': "None" , 'asset_type': asset_type}
            else:
                existing_conn.rev_assets_blender[uid]['obj'] = obj
            if not hasattr(obj, "obj_prop"):
                obj.obj_prop = bpy.props.PointerProperty(type=CustomObjectProperties)
            obj.obj_prop.obj_name = obj.name # assign object's name as one of the custom properties

@persistent
def model_change_handler(scene): # if Motive's .tak is changed with already established connection in Blender
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
def load_handler(dummy): # every time a new file is loaded or created in Blender
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