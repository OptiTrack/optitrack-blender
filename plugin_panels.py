import bpy
from . import connection_operator
from .connection_operator import ConnectButtonOperator
from bpy.types import Panel
from .icon_viewer import IconsLoader

class PluginMotive(Panel):
    bl_idname = "VIEW3D_PT_plugin_motive"
    bl_label = "Optitrack"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Motive'
    
    def draw(self, context):
        layout = self.layout
        
        row = layout.row()
        row.label(text = "Motive Plugin", icon= 'POINTCLOUD_POINT')

class InitialSettings(Panel):
    bl_idname = "VIEW3D_PT_initial_settings"
    bl_label = "Settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Motive'
    bl_parent_id = 'VIEW3D_PT_plugin_motive'


    def draw(self, context):
        layout = self.layout
        Scene = context.scene
        initprop = Scene.init_prop

        box = layout.box()
        box.prop(initprop, 'server_address')
        box.prop(initprop, 'client_address')
        box.prop(initprop, 'unit_setting')
        box.prop(initprop, 'scale')
        box.prop(initprop, 'fps_value')

        row = layout.row()
        row.prop(initprop, 'default_settings')

class Connection(Panel):
    bl_idname = "VIEW3D_PT_connection"
    bl_label = "Connection"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Motive'
    bl_parent_id = 'VIEW3D_PT_plugin_motive'
    
    def draw(self, context):
        layout = self.layout
        Scene = context.scene
        initprop = Scene.init_prop
        
        row = layout.row(align=True)
        if context.window_manager.connection_status:
            row.operator(connection_operator.ResetOperator.bl_idname, text=connection_operator.ResetOperator.bl_label, icon='SNAP_FACE')
            row = layout.row()
            row.operator(connection_operator.RefreshAssetsOperator.bl_idname, text=connection_operator.RefreshAssetsOperator.bl_label, icon='FILE_REFRESH')
            row = layout.row()
            row.label(text="Motive Assets (ID: Name)")
            row = layout.row()
            # row.template_list("UI_LIST", "Object List", context.scene, "obj_ls", rows=1)
            # obj_ls = context.scene.get('obj_ls', {})
            obj_ls = ConnectButtonOperator.connection_setup.streaming_client.desc_dict
            if obj_ls:
                box = layout.box()
                for key, val in obj_ls.items():
                    row = box.row()
                    row.label(text=str(key) + ": " + str(val), icon_value = IconsLoader.get_icon("active"))
            else:
                box = layout.box()
                row = box.row()
            
            row = layout.row()
            if context.window_manager.start_status:
                row.label(text="Receiving", icon='CHECKMARK')
                row.operator(connection_operator.PauseButtonOperator.bl_idname, text=connection_operator.PauseButtonOperator.bl_label, icon='PAUSE')
            else:
                row.operator(connection_operator.StartButtonOperator.bl_idname, text=connection_operator.StartButtonOperator.bl_label, icon= 'TEMP')
        else:
            layout.operator(connection_operator.ConnectButtonOperator.bl_idname, text=connection_operator.ConnectButtonOperator.bl_label, icon= 'TRIA_RIGHT_BAR')

# Object Properties Pane
class AssignObjects(Panel):
    bl_idname = "OBJECT_PT_assign_objects"
    bl_label = "OptiTrack Blender Plugin"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    # bl_context = ''
    bl_options = {'HEADER_LAYOUT_EXPAND'}

    def draw(self, context):
        layout = self.layout
        obj = context.object

        row = layout.row(align=True)
        row.label(text="Assign Object", icon='ARROW_LEFTRIGHT')

        # row = layout.row(align=True)
        # if not ConnectButtonOperator.connection_setup.streaming_client.desc_dict:
        #     row.label(text="None")
        # else:
        #     row.prop(context.object, )    

class Info(Panel):
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
