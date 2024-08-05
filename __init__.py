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
    from . import plugin_operators
    from . import Modified_NatNetClient
    from . import property_definitions
    from . import app_handlers
    from . import icon_viewer
    
    if "bpy" not in locals():
        pass
    else:
        import importlib
        importlib.reload(plugin_panels)
        importlib.reload(plugin_operators)
        importlib.reload(Modified_NatNetClient)
        importlib.reload(property_definitions)
        importlib.reload(app_handlers)
        importlib.reload(icon_viewer)

    global classes
    classes = [plugin_panels.PluginMotive, property_definitions.CustomSceneProperties,
               property_definitions.CustomObjectProperties, 
               plugin_panels.InitialSettings, plugin_panels.AssignObjects,
               plugin_panels.Connection, plugin_operators.ResetOperator,
               plugin_operators.ConnectButtonOperator, 
               plugin_operators.RefreshAssetsOperator,
               plugin_operators.StartButtonOperator,
               plugin_operators.PauseButtonOperator,
               plugin_panels.Info]
    # plugin_operators.StartRecordButtonOperator, plugin_operators.StopRecordButtonOperator,
    for cls in classes:
        bpy.utils.register_class(cls)
    
    icon_viewer.IconsLoader.registering_icons()
    bpy.types.Scene.init_prop = bpy.props.PointerProperty(
        type=property_definitions.CustomSceneProperties)
    bpy.types.Object.obj_prop = bpy.props.PointerProperty(
        type=property_definitions.CustomObjectProperties)
    bpy.app.handlers.depsgraph_update_post.append(app_handlers.object_deleted_handler)
    bpy.app.handlers.depsgraph_update_post.append(app_handlers.object_prop_handler)
    bpy.app.handlers.depsgraph_update_pre.append(app_handlers.model_change_handler)
    bpy.app.handlers.load_post.append(app_handlers.load_handler)

def unregister():
    # from . import plugin_panels
    # from . import plugin_operators
    # from . import Modified_NatNetClient
    # from . import property_definitions
    from . import app_handlers
    from . import icon_viewer
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.init_prop
    del bpy.types.Object.obj_prop
    icon_viewer.IconsLoader.unregistering_icons()
    if app_handlers.object_deleted_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(app_handlers.object_deleted_handler)
    if app_handlers.object_prop_handler in bpy.app.handlers.depsgraph_update_post:    
        bpy.app.handlers.depsgraph_update_post.remove(app_handlers.object_prop_handler)
    if app_handlers.model_change_handler in bpy.app.handlers.depsgraph_update_pre:
        bpy.app.handlers.depsgraph_update_pre.remove(app_handlers.model_change_handler)
    bpy.app.handlers.load_post.remove(app_handlers.load_handler)
    
if __name__ == "__main__":
    register()