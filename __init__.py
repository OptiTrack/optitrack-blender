# Edit -> Preferences -> Add-ons
bl_info = {
    "name": "OptiTrack Blender Plugin",
    "author": "OptiTrack",
    "version": (1, 0, 0),
    "blender": (4, 1, 0),
    "location": "View3D > Toolbar > Motive",
    "description": "live stream Motive data into blender",
    "warning": "",
    "wiki_url": "github??",
    "category": "Motive",
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
    
    if "bpy" not in locals():
        pass
    else:
        import importlib
        importlib.reload(plugin_panels)
        importlib.reload(connection_operator)
        importlib.reload(Modified_NatNetClient)
        importlib.reload(property_definitions)
        importlib.reload(app_handlers)

    global classes
    classes = [plugin_panels.PluginMotive, property_definitions.Initializer, plugin_panels.InitialSettings,
               plugin_panels.Connection, plugin_panels.Receiver, connection_operator.ResetOperator,
               connection_operator.ConnectButtonOperator, connection_operator.StartButtonOperator,
               connection_operator.GetRigidBodiesIDsOperator, connection_operator.PauseButtonOperator, 
               connection_operator.AssignAgainOperator, plugin_panels.Info]
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.init_prop = bpy.props.PointerProperty(type=property_definitions.Initializer)
    bpy.app.handlers.depsgraph_update_post.append(app_handlers.object_deleted_handler)
    bpy.app.handlers.depsgraph_update_pre.append(app_handlers.model_change_handler)
    bpy.app.handlers.load_post.append(app_handlers.load_handler)

def unregister():
    from . import plugin_panels
    from . import connection_operator
    from . import Modified_NatNetClient
    from . import property_definitions
    from . import app_handlers
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.init_prop
    if app_handlers.object_deleted_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(app_handlers.object_deleted_handler)
    if app_handlers.model_change_handler in bpy.app.handlers.depsgraph_update_pre:
        bpy.app.handlers.depsgraph_update_pre.remove(app_handlers.model_change_handler)
    bpy.app.handlers.load_post.remove(app_handlers.load_handler)
    
if __name__ == "__main__":
    register()