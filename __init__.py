# Edit -> Preferences -> Add-ons
bl_info = {
    "name": "Motive Blender Plugin",
    "author": "OptiTrack",
    "version": (1, 1, 0),
    "blender": (4, 4, 0),
    "location": "View3D > Toolbar > Motive",
    "description": "Stream Motive asset data into Blender",
    "warning": "",
    "category": "OptiTrack",
}

# Import libraries
if "bpy" not in locals():
    import bpy  # Blender Python Module


# Register and unregister classes
def register():
    from . import (
        Modified_NatNetClient,
        app_handlers,
        icon_viewer,
        plugin_operators,
        plugin_panels,
        plugin_skeletons,
        property_definitions,
        repository,
    )

    if "bpy" not in locals():
        pass
    else:
        import importlib

        importlib.reload(plugin_panels)
        importlib.reload(plugin_operators)
        importlib.reload(plugin_skeletons)
        importlib.reload(Modified_NatNetClient)
        importlib.reload(property_definitions)
        importlib.reload(app_handlers)
        importlib.reload(icon_viewer)

    global classes
    classes = [
        plugin_panels.PluginMotive,
        property_definitions.CustomSceneProperties,
        property_definitions.CustomObjectProperties,
        plugin_panels.InitialSettings,
        plugin_panels.AssignObjects,
        plugin_panels.AllocatedObjects,
        plugin_panels.AllocatedArmatureBones,
        plugin_panels.Connection,
        plugin_panels.Recorder,
        plugin_operators.ResetOperator,
        plugin_operators.ConnectOperator,
        plugin_operators.RefreshAssetsOperator,
        plugin_operators.StartOperator,
        plugin_operators.PauseOperator,
        plugin_operators.StartRecordOperator,
        plugin_operators.StopRecordOperator,
        plugin_operators.StartEndFrameOperator,
        plugin_operators.StartFrameRecordOperator,
        plugin_operators.StopFrameRecordOperator,
        plugin_operators.newActionOperator,
        plugin_skeletons.MotiveArmatureOperator,
        plugin_panels.Info,
    ]

    for cls in classes:
        bpy.utils.register_class(cls)

    icon_viewer.IconsLoader.registering_icons()
    bpy.types.Scene.init_prop = bpy.props.PointerProperty(
        type=property_definitions.CustomSceneProperties
    )
    bpy.types.Object.obj_prop = bpy.props.PointerProperty(
        type=property_definitions.CustomObjectProperties
    )
    bpy.app.handlers.depsgraph_update_post.append(app_handlers.object_handler)
    bpy.app.handlers.depsgraph_update_pre.append(app_handlers.model_change_handler)
    bpy.app.handlers.load_post.append(app_handlers.load_handler)

    repository.register()


def unregister():
    from . import app_handlers, icon_viewer, repository

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.init_prop
    del bpy.types.Object.obj_prop
    icon_viewer.IconsLoader.unregistering_icons()

    if app_handlers.object_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(app_handlers.object_handler)
    if app_handlers.model_change_handler in bpy.app.handlers.depsgraph_update_pre:
        bpy.app.handlers.depsgraph_update_pre.remove(app_handlers.model_change_handler)

    bpy.app.handlers.load_post.remove(app_handlers.load_handler)

    repository.unregister()


if __name__ == "__main__":
    register()
