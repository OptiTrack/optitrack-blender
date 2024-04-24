# plugin visible on the UI panel
bl_info = {
    "name": "Motive Plugin",
    "author": "RT",
    "version": (1, 0),
    "blender": (3, 6, 10, 0),
    "location": "View3D > Toolbar > Motive",
    "description": "live stream motive data into blender",
    "warning": "",
    "wiki_url": "github??",
    "category": "Motive Plugin",
}

# Import libraries
import bpy # Blender Python Module
import sys
import os
import time
# import asyncio
sys.path.append("C:/Users/radhika.tekade/Desktop/blender_plugin")
# dir = os.path.dirname(bpy.data.filepath)
# if not dir in sys.path:
#     sys.path.append(dir) # "C:/Users/radhika.tekade/Desktop/blender_plugin/NatNetClient"
#     print("system's path: " + str(sys.path))
from NatNetClient import NatNetClient

# this next part forces a reload in case you edit the source after you first start the blender session
# import imp
# imp.reload(cityFunctions)

# this is optional and allows you to call the functions without specifying the package name
# from cityFunctions import *

# SERVER = socket.gethostbyname(socket.gethostname()) # instead of hardcoding

class PopupMessageOperator(bpy.types.Operator):
    bl_idname = "wm.popup_message"
    bl_label = "Popup Message"

    message: bpy.props.StringProperty()

    def execute(self, context):
        # Display the popup message
        self.report({'INFO'}, self.message)
        return {'FINISHED'}

# Function to show the popup message
def display_message(message):
    # Invoke the custom operator
    bpy.ops.wm.popup_message('INVOKE_DEFAULT', message=message)

def request_data_descriptions(s_client):
    # Request the model definitions
    s_client.send_request(s_client.command_socket, s_client.NAT_REQUEST_MODELDEF,    "",  (s_client.server_ip_address, s_client.command_port) )

# Define a custom property to track connection state
bpy.types.WindowManager.connection_status = bpy.props.BoolProperty(name="Connection Status", default=False)

class PluginMotive(bpy.types.Panel):
    """Tooltip"""
    bl_idname = "VIEW3D_PT_plugin_motive"
    bl_label = "Optitrack"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Motive'
    
    def draw(self, context):
        layout = self.layout
        
        row = layout.row()
        row.label(text = "Motive Plugin", icon= 'OUTLINER_DATA_POINTCLOUD')
        row = layout.row()
        if context.window_manager.connection_status:
            row.label(text="Started")
            row.operator("wm.disconnect_button", text="Stop", icon='CANCEL') # CANCEL
        else:
            row.operator("wm.connect_button", text="Start", icon= 'TRIA_RIGHT_BAR') # icon - "CONSOLE"


class ConnectionSetup:
    def __init__(self):
        self.streaming_client = None

    def connect_button_clicked(self, context): 
        # Initialize streaming client       
        if self.streaming_client is None:
            optionsDict = {'clientAddress': '127.0.0.1', 'serverAddress': '127.0.0.1', 'use_multicast': True}
            self.streaming_client = NatNetClient()
            display_message(str(self.streaming_client))
            self.streaming_client.set_client_address(optionsDict["clientAddress"])
            self.streaming_client.set_server_address(optionsDict["serverAddress"])
            self.streaming_client.set_use_multicast(optionsDict["use_multicast"])

            is_running = self.streaming_client.run()
            if is_running:
                # Update connection status
                context.window_manager.connection_status = True
                display_message("Connection Successful")
            else:
                context.window_manager.connection_status = False
                display_message("Connection failed")   
                try:
                    sys.exit(1)
                except SystemExit:
                    print("...")
                finally:
                    print("exiting")

    def disconnect_button_clicked(self, context):        
        if self.streaming_client:
            context.window_manager.connection_status = False
            self.streaming_client.shutdown()
            self.streaming_client = None

connection_setup = ConnectionSetup()
class ConnectButtonOperator(bpy.types.Operator):
    bl_idname = "wm.connect_button"
    bl_label = "Start"
    
    def execute(self, context):
        connection_setup.connect_button_clicked(context)
        return {'FINISHED'}

class DisconnectButtonOperator(bpy.types.Operator):
    bl_idname = "wm.disconnect_button"
    bl_label = "Stop"
    
    def execute(self, context):
        connection_setup.disconnect_button_clicked(context)
        return {'FINISHED'}
        
class Addons(bpy.types.AddonPreferences):
    bl_idname = "object.addons"
    bl_label = "connection"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Motive'
    bl_parent_id = 'VIEW3D_PT_plugin_motive'
    bl_options = {'DEFAULT_CLOSED'}

    # socket_ip: bpy.props.StringProperty(name="Socket ip",
    #                             description="IP of publisher socket",
    #                             default="127.0.0.1")
    
    # socket_port: bpy.props.StringProperty(name="Socket port",
    #                             description="Port of publisher socket",
    #                             default="5550")  
    
    def draw(self, context):
        layout = self.layout
        layout.label(text="Socket connection settings:")

        row = layout.row(align=True)
        row.prop(self, "socket_ip", text="ip")
        row.prop(self, "socket_port", text="port")
    

class Info(bpy.types.Panel):
    """Tooltip"""
    bl_idname = "VIEW3D_PT_info"
    bl_label = "Info"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Motive'
    bl_parent_id = 'VIEW3D_PT_plugin_motive'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        
        row = layout.row()
        row.label(text = "INFO ABOUT THE PLUGIN", icon= 'INFO')
        row = layout.row()
        row.operator("wm.url_open", text = "Website").url = "https://optitrack.com"
        row.operator("wm.url_open", text = "Documentation").url = "https://docs.optitrack.com/"
        
# Register and unregister classes
classes = [PluginMotive, ConnectButtonOperator, DisconnectButtonOperator, PopupMessageOperator, Info, Addons]
def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
if __name__ == "__main__":
    register()

    # is_looping = True
    # time.sleep(1)
    # if streaming_client.connected() is False:
    #     print("ERROR: Could not connect properly. Check that Motive streaming is on.")
    #     try:
    #         sys.exit(2)
    #     except SystemExit:
    #         print("...")
    #     finally:
    #         print("exiting")
