# plugin visible on the UI panel
bl_info = {
    "name": "Motive Plugin",
    "author": "RT",
    "version": (1, 0),
    "blender": (4, 1, 0, 0),
    "location": "View3D > Toolbar > Motive",
    "description": "live stream motive data into blender",
    "warning": "",
    "wiki_url": "github??",
    "category": "Motive Plugin",
}

# Import libraries
flag = "bpy" not in locals()
import bpy # Blender Python Module
import sys
import os

# Initial changes to UI
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 1.0
bpy.context.scene.render.fps = 120
bpy.data.objects['Cube'].select_set(True)
bpy.ops.object.delete()
        
# Register and unregister classes
def register():
    # Get the absolute path of the script file's directory
    for root, dirs, files in os.walk(os.path.dirname(os.path.abspath(__file__))):
        if "14blender_plugin050224.py" in files:
            package_dir = root 
    # package_dir = "C:/Users/radhika.tekade/Desktop/blender_plugin"
    sys.path.append(package_dir)
    print("package dir: ", package_dir)

    import plugin_panels
    import connection_operator
    import Modified_NatNetClient
    
    if flag:
        pass
    else:
        import importlib
        importlib.reload(plugin_panels)
        importlib.reload(connection_operator)
        importlib.reload(Modified_NatNetClient)
    
    global classes
    classes = [plugin_panels.PluginMotive, plugin_panels.Connection, 
               connection_operator.ConnectButtonOperator,
               connection_operator.DisconnectButtonOperator, plugin_panels.Info]
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
if __name__ == "__main__":
    register()