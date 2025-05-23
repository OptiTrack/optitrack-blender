import bpy
from . import plugin_operators
from .plugin_operators import ConnectOperator
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
        
        row = layout.row(align=True)
        row.label(text = "Motive Plugin", icon_value = IconsLoader.get_icon("Motive"))

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
        box2 = box.box()
        row = box2.row(align=True)
        row.label(text="Set Transmission Type to")
        row = box2.row(align=True)
        row.label(text="Multicast in Streaming Settings.")
        box.prop(initprop, 'unit_setting')
        box.prop(initprop, 'scale')
        box.prop(initprop, 'fps_value')

        row = layout.row(align=True)
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
            row.operator(plugin_operators.ResetOperator.bl_idname, \
                         text=plugin_operators.ResetOperator.bl_label, \
                            icon_value = IconsLoader.get_icon("Stop"))

            row = layout.row(align=True)
            row.label(text="Motive Assets (ID: Name)")
            row = layout.row(align=True)
            obj_ls = ConnectOperator.connection_setup.streaming_client.desc_dict
            if obj_ls:
                box = layout.box()
                for key, val in obj_ls.items():
                    row = box.row(align=True)
                    row.label(text=str(key) + ": " + str(val), icon_value = IconsLoader.get_icon("RigidBody"))
            else:
                box = layout.box()
                row = box.row(align=True)

            row = layout.row(align=True)
            row.operator(plugin_operators.RefreshAssetsOperator.bl_idname, \
                         text=plugin_operators.RefreshAssetsOperator.bl_label, \
                            icon_value = IconsLoader.get_icon("Refresh"))
            
            row = layout.row(align=True)
            if context.window_manager.start_status:
                row.label(text="Receiving", icon_value = IconsLoader.get_icon("Checkmark"))
                row.operator(plugin_operators.PauseOperator.bl_idname, \
                             text=plugin_operators.PauseOperator.bl_label, \
                                icon_value = IconsLoader.get_icon("Pause"))
            else:
                row.operator(plugin_operators.StartOperator.bl_idname, \
                             text=plugin_operators.StartOperator.bl_label, \
                                icon_value = IconsLoader.get_icon("Awaiting"))

        else:
            layout.operator(plugin_operators.ConnectOperator.bl_idname, \
                            text=plugin_operators.ConnectOperator.bl_label, \
                                icon_value = IconsLoader.get_icon("Connect"))

class Recorder(Panel):
    bl_idname = "VIEW3D_PT_recorder"
    bl_label = "Recorder"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Motive'
    bl_parent_id = 'VIEW3D_PT_connection'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        Scene = context.scene
        initprop = Scene.init_prop
        
        row = layout.row(align=True)
        if context.window_manager.connection_status:
            # no definite keyframes
            row.enabled = not initprop.custom_recording
            if context.window_manager.record2_status:
                row.operator(plugin_operators.StopRecordOperator.bl_idname, \
                             text=plugin_operators.StopRecordOperator.bl_label, \
                                icon_value = IconsLoader.get_icon("RecordStop"))
            else:
                row.operator(plugin_operators.StartRecordOperator.bl_idname, \
                             text=plugin_operators.StartRecordOperator.bl_label, \
                                icon_value = IconsLoader.get_icon("Record"))
            
            row = layout.row(align=True)
            row.prop(initprop, 'custom_recording')

            # selective keyframes
            row = layout.row(align=True)
            row.enabled = initprop.custom_recording
            row.operator(plugin_operators.StartEndFrameOperator.bl_idname, \
                         text="Select Frame Range")
            row = layout.row(align=True)
            row.enabled = initprop.custom_recording
            if context.window_manager.record1_status:
                row.operator(plugin_operators.StopFrameRecordOperator.bl_idname, \
                             text=plugin_operators.StopRecordOperator.bl_label, \
                                icon_value = IconsLoader.get_icon("RecordStop"))
            else:
                row.operator(plugin_operators.StartFrameRecordOperator.bl_idname, \
                             text=plugin_operators.StartRecordOperator.bl_label, \
                                icon_value = IconsLoader.get_icon("Record"))
            
            row = layout.row(align=True)
            row.operator(plugin_operators.newActionOperator.bl_idname, \
                         text=plugin_operators.newActionOperator.bl_label)
        else:
            row.label(text="Start the connection first")

# Object Properties Pane
class AssignObjects(Panel):
    bl_idname = "OBJECT_PT_assign_objects"
    bl_label = "Motive: Assign Assets"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_options = {'HEADER_LAYOUT_EXPAND'}

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.label(text="Assign Rigid Body to Object:", icon='ARROW_LEFTRIGHT')

        layout.use_property_split = True

        existing_conn = plugin_operators.ConnectOperator.connection_setup
        bad_obj_types = ['CAMERA', 'LIGHT']
        if existing_conn.streaming_client:
            existing_conn.get_rigid_body_dict(context)
            if existing_conn.rigid_bodies_motive:
                for obj in bpy.data.objects:
                    if obj.type not in bad_obj_types:
                        objprop = obj.obj_prop
                        row = layout.row(align=True)
                        obj_name = obj.name
                        row.prop(objprop, 'rigid_bodies', text=obj_name)
        else:
            row = layout.row(align=True)
            row.label(text="None")

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
        
        row = layout.row(align=True)
        row.label(text = "OptiTrack Documentation", icon_value = IconsLoader.get_icon("Info"))
        row = layout.row(align=True)
        row.operator("wm.url_open", text = "Website").url = "https://optitrack.com"
        row.operator("wm.url_open", text = "Documentation").url = "https://docs.optitrack.com/"
