# Edit -> Preferences -> Add-ons
bl_info = {
    "name": "Motive Blender Plugin",
    "author": "OptiTrack",
    "version": (1, 0, 0),
    "blender": (4, 1, 0),
    "location": "View3D > Toolbar > Motive",
    "description": "live stream Motive data into blender",
    "warning": "",
    "wiki_url": "github??",
    "category": "OptiTrack",
}

# Import libraries
if "bpy" not in locals():
    import bpy # Blender Python Module

# Register and unregister classes
def register():
    from . import plugin_panels
    from . import connection_operator
    from . import Modified_NatNetClient
    from . import property_definitions
    from . import app_handlers
    from . import icon_viewer
    
    if "bpy" not in locals():
        pass
    else:
        import importlib
        importlib.reload(plugin_panels)
        importlib.reload(connection_operator)
        importlib.reload(Modified_NatNetClient)
        importlib.reload(property_definitions)
        importlib.reload(app_handlers)
        importlib.reload(icon_viewer)

    global classes
    classes = [plugin_panels.PluginMotive, property_definitions.CustomProperties, 
               plugin_panels.InitialSettings, plugin_panels.AssignObjects,
               plugin_panels.Connection, connection_operator.ResetOperator,
               connection_operator.ConnectButtonOperator, 
               connection_operator.RefreshAssetsOperator,
               connection_operator.StartButtonOperator,
               connection_operator.PauseButtonOperator, plugin_panels.Info]
    for cls in classes:
        bpy.utils.register_class(cls)
    
    icon_viewer.IconsLoader.registering_icons()
    bpy.types.Scene.init_prop = bpy.props.PointerProperty(
        type=property_definitions.CustomProperties)
    # bpy.types.Scene.obj_ls = bpy.props.CollectionProperty(
    #     type=property_definitions.ObjectListItem)
    bpy.app.handlers.depsgraph_update_post.append(app_handlers.object_deleted_handler)
    bpy.app.handlers.depsgraph_update_pre.append(app_handlers.model_change_handler)
    bpy.app.handlers.load_post.append(app_handlers.load_handler)

def unregister():
    from . import plugin_panels
    from . import connection_operator
    from . import Modified_NatNetClient
    from . import property_definitions
    from . import app_handlers
    from . import icon_viewer
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    icon_viewer.IconsLoader.unregistering_icons()
    del bpy.types.Scene.init_prop
    if app_handlers.object_deleted_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(app_handlers.object_deleted_handler)
    if app_handlers.model_change_handler in bpy.app.handlers.depsgraph_update_pre:
        bpy.app.handlers.depsgraph_update_pre.remove(app_handlers.model_change_handler)
    bpy.app.handlers.load_post.remove(app_handlers.load_handler)
    
if __name__ == "__main__":
    register()