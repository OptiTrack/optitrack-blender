import bpy
from . import connection_operator
from .connection_operator import ConnectButtonOperator
from bpy.types import Panel

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
        layout.operator(connection_operator.ResetOperator.bl_idname)

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
        box.prop(initprop, 'desired_object')

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
            box = row.box()
            box.label(text="Connected", icon='SEQUENCE_COLOR_04')
            row = layout.row()
            if context.window_manager.start_status:
                row.label(text="Started")
                row.operator(connection_operator.PauseButtonOperator.bl_idname, text="Pause", icon='PAUSE')
                row = layout.row()
                row.operator(connection_operator.GetRigidBodiesIDsOperator.bl_idname, text="Show Current IDs")
                id_ls = context.scene.get('id_ls', [])
                if id_ls:
                    box = layout.box()
                    # box.label(text="IDs: ")
                    row = box.row()
                    for item in id_ls:
                        row.label(text=str(item))
                row = layout.row()
                row.label(text="Assigned IDs: ")
                box = layout.box()
                for key, val in connection_operator.ConnectButtonOperator.connection_setup.rigid_bodies.items():
                    row = box.row()
                    row.label(text=str(key) + ": " + str(val.name))
                row = layout.row()
                row.operator(connection_operator.AssignAgainOperator.bl_idname, text="Assign IDs")
            else:
                row.operator(connection_operator.StartButtonOperator.bl_idname, text="Start", icon= 'TRIA_RIGHT_BAR')
        else:
            layout.operator(connection_operator.ConnectButtonOperator.bl_idname, text="Connect", icon= 'SEQUENCE_COLOR_01') # 'LINK_BLEND'

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
