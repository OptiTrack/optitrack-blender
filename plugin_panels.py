import bpy
import sys
import connection_operator

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
        row.label(text = "Motive Plugin", icon= 'POINTCLOUD_POINT')

class Connection(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_connection"
    bl_label = "Connection"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Motive'
    bl_parent_id = 'VIEW3D_PT_plugin_motive'

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        # if context.scene.get("status", False):
        if context.window_manager.connection_status:
            row.label(text="Started")
            row.operator(connection_operator.DisconnectButtonOperator.bl_idname, text="Stop", icon='CANCEL')
        else:
            row.operator(connection_operator.ConnectButtonOperator.bl_idname, text="Start", icon= 'TRIA_RIGHT_BAR')
   
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
