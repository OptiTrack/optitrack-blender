import bpy

# from .plugin_skeletons import skeletonDict
from bpy.types import Panel

from . import plugin_operators
from .icon_viewer import IconsLoader
from .plugin_operators import ConnectOperator
from .plugin_skeletons import MotiveArmatureOperator
from .repository.action import ActionRepository


class PluginMotive(Panel):
    bl_idname = "VIEW3D_PT_plugin_motive"
    bl_label = "Optitrack"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Motive"

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.label(text="Motive Plugin", icon_value=IconsLoader.get_icon("Motive"))


class InitialSettings(Panel):
    bl_idname = "VIEW3D_PT_initial_settings"
    bl_label = "Settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Motive"
    bl_parent_id = "VIEW3D_PT_plugin_motive"

    def draw(self, context):
        layout = self.layout
        Scene = context.scene
        initprop = Scene.init_prop

        box = layout.box()
        box.prop(initprop, "server_address")
        box.prop(initprop, "client_address")
        box2 = box.box()
        row = box2.row(align=True)
        row.label(text="Set Transmission Type to")
        row = box2.row(align=True)
        row.label(text="Multicast in Streaming Settings.")


class Connection(Panel):
    bl_idname = "VIEW3D_PT_connection"
    bl_label = "Connection"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Motive"
    bl_parent_id = "VIEW3D_PT_plugin_motive"

    def draw(self, context):
        layout = self.layout
        Scene = context.scene
        initprop = Scene.init_prop

        row = layout.row(align=True)
        if context.window_manager.connection_status:
            row.operator(
                plugin_operators.ResetOperator.bl_idname,
                text=plugin_operators.ResetOperator.bl_label,
                icon_value=IconsLoader.get_icon("Stop"),
            )

            row = layout.row(align=True)
            row.label(text="Motive Assets (ID: Name)")
            row = layout.row(align=True)
            obj_ls = ConnectOperator.connection_setup.streaming_client.desc_dict
            if obj_ls:
                box = layout.box()
                for key, val in obj_ls.items():
                    if key == "rb_desc":
                        for k1, v1 in val.items():
                            row = box.row(align=True)
                            row.label(
                                text=str(k1) + " : " + str(v1["name"]),
                                icon_value=IconsLoader.get_icon("RigidBody"),
                            )

                    if key == "ske_desc":
                        for k2, v2 in val.items():
                            row = box.row(align=True)
                            row.label(
                                text=str(k2) + " : " + str(v2["name"]),
                                icon="OUTLINER_OB_ARMATURE",
                            )
            else:
                box = layout.box()
                row = box.row(align=True)

            row = layout.row(align=True)
            row.operator(
                plugin_operators.RefreshAssetsOperator.bl_idname,
                text=plugin_operators.RefreshAssetsOperator.bl_label,
                icon_value=IconsLoader.get_icon("Refresh"),
            )

            layout.row().separator()
            row = layout.row(align=True)
            row.operator(
                MotiveArmatureOperator.bl_idname,
                text=MotiveArmatureOperator.bl_label,
                icon="OUTLINER_OB_ARMATURE",
            )

            row = layout.row(align=True)
            if context.window_manager.start_status:
                row.label(
                    text="Receiving", icon_value=IconsLoader.get_icon("Checkmark")
                )
                row.operator(
                    plugin_operators.PauseOperator.bl_idname,
                    text=plugin_operators.PauseOperator.bl_label,
                    icon_value=IconsLoader.get_icon("Pause"),
                )
            else:
                row.operator(
                    plugin_operators.StartOperator.bl_idname,
                    text=plugin_operators.StartOperator.bl_label,
                    icon_value=IconsLoader.get_icon("Awaiting"),
                )

        else:
            layout.operator(
                plugin_operators.ConnectOperator.bl_idname,
                text=plugin_operators.ConnectOperator.bl_label,
                icon_value=IconsLoader.get_icon("Connect"),
            )


class Recorder(Panel):
    bl_idname = "VIEW3D_PT_recorder"
    bl_label = "Recorder"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Motive"
    bl_parent_id = "VIEW3D_PT_connection"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        Scene = context.scene
        initprop = Scene.init_prop

        row = layout.row(align=True)
        if context.window_manager.connection_status:
            # no definite keyframes
            row.enabled = not initprop.custom_recording
            if context.window_manager.record2_status:
                row.operator(
                    plugin_operators.StopRecordOperator.bl_idname,
                    text=plugin_operators.StopRecordOperator.bl_label,
                    icon_value=IconsLoader.get_icon("RecordStop"),
                )
            else:
                row.operator(
                    plugin_operators.StartRecordOperator.bl_idname,
                    text=plugin_operators.StartRecordOperator.bl_label,
                    icon_value=IconsLoader.get_icon("Record"),
                )

            row = layout.row(align=True)
            row.prop(initprop, "custom_recording")

            # selective keyframes
            row = layout.row(align=True)
            row.enabled = initprop.custom_recording
            row.operator(
                plugin_operators.StartEndFrameOperator.bl_idname,
                text="Select Frame Range",
            )
            row = layout.row(align=True)
            row.enabled = initprop.custom_recording
            if context.window_manager.record1_status:
                row.operator(
                    plugin_operators.StopFrameRecordOperator.bl_idname,
                    text=plugin_operators.StopRecordOperator.bl_label,
                    icon_value=IconsLoader.get_icon("RecordStop"),
                )
            else:
                row.operator(
                    plugin_operators.StartFrameRecordOperator.bl_idname,
                    text=plugin_operators.StartRecordOperator.bl_label,
                    icon_value=IconsLoader.get_icon("Record"),
                )

            layout.label(
                text=f"Current Action Name: {ActionRepository.get_action_name()}"
            )
            row = layout.row(align=True)
            row.operator(
                plugin_operators.newActionOperator.bl_idname,
                text=plugin_operators.newActionOperator.bl_label,
            )
        else:
            row.label(text="Start the connection first")


# Object Properties Pane
class AssignObjects(Panel):
    bl_idname = "OBJECT_PT_assign_objects"
    bl_label = "Motive: Assign Assets"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_options = {"HEADER_LAYOUT_EXPAND"}

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.label(text="Assign Motive to Blender Asset:", icon="ARROW_LEFTRIGHT")

        layout.use_property_split = True

        existing_conn = plugin_operators.ConnectOperator.connection_setup
        # bad_obj_types = ['CAMERA', 'LIGHT']
        if existing_conn.streaming_client:
            # existing_conn.get_rigid_body_dict(context)
            existing_conn.get_desc_dict(context)
            # for obj in bpy.data.objects:
            # if obj.type not in bad_obj_types:
            if bpy.context.active_object.select_get():  # ==
                obj = bpy.context.active_object
                objprop = obj.obj_prop
                row = layout.row(align=True)
                obj_name = obj.name

                if obj.type == "MESH":
                    row.prop(objprop, "rigid_bodies", text=obj_name)

                if obj.type == "ARMATURE":
                    row.prop(objprop, "skeletons", text=obj_name)

            else:
                row = layout.row(align=True)
                row.label(text="Select an object.")

        else:
            row = layout.row(align=True)
            row.label(text="Start the connection.")


class AllocatedObjects(Panel):
    bl_idname = "OBJECT_PT_allocated_objects"
    bl_label = "Motive: Assets in Use"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_parent_id = "OBJECT_PT_assign_objects"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(
        cls, context
    ):  # sub panel created only if there are assigned motive objects to show
        d = plugin_operators.ConnectOperator.connection_setup.assets_blender
        if d:
            if ("rigid_body" in d and bool(d["rigid_body"])) or (
                "skeleton" in d and bool(d["skeleton"])
            ):
                return True

    def draw(self, context):
        existing_conn = plugin_operators.ConnectOperator.connection_setup
        layout = self.layout
        for key, val in existing_conn.assets_blender.items():  # assetType: m_ID: b_ID
            for k, v in val.items():  # m_ID: b_ID
                m_ID = k
                b_ID = v["b_ID"]
                b_obj_name = existing_conn.rev_assets_blender[v["b_ID"]]["obj"].name

                row = layout.row(align=True)
                row.alert = True

                if key == "rigid_body":
                    m_obj_name = existing_conn.assets_motive["rb_desc"][k]["name"]
                    row.label(
                        text=b_obj_name + " : " + str(m_ID) + " : " + str(m_obj_name),
                        icon="OUTLINER_DATA_MESH",
                    )

                elif key == "skeleton":
                    m_obj_name = existing_conn.assets_motive["ske_desc"][k]["name"]
                    row.label(
                        text=b_obj_name + " : " + str(m_ID) + " : " + str(m_obj_name),
                        icon="OUTLINER_OB_ARMATURE",
                    )


class AllocatedArmatureBones(Panel):
    bl_idname = "OBJECT_PT_allocated_arm_bones"
    bl_label = "Motive: Skeleton Bones"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_parent_id = "OBJECT_PT_allocated_objects"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(
        cls, context
    ):  # sub panel created only if there are assigned skeleton bones to show
        if (
            "skeleton"
            in plugin_operators.ConnectOperator.connection_setup.assets_blender
        ):
            if plugin_operators.ConnectOperator.connection_setup.assets_blender[
                "skeleton"
            ]:
                return True
        # return bool(plugin_operators.ConnectOperator.connection_setup.assets_blender['skeleton'])

    def draw(self, context):
        existing_conn = plugin_operators.ConnectOperator.connection_setup
        layout = self.layout
        for key, val in existing_conn.assets_blender[
            "skeleton"
        ].items():  # assetType: m_ID: b_ID
            row = layout.row(align=True)
            row.alert = True
            row.label(text=existing_conn.assets_motive["ske_desc"][key]["name"] + ": ")
            for k, v in val["ske_rb_map"]["b_to_m"].items():  # m_ID: b_ID
                row = layout.row(align=True)
                row.label(
                    text=k
                    + " : "
                    + str(v)
                    + " : "
                    + existing_conn.assets_motive["ske_desc"][key]["rb_id"][v]["name"]
                )


class Info(Panel):
    bl_idname = "VIEW3D_PT_info"
    bl_label = "Info"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Motive"
    bl_parent_id = "VIEW3D_PT_plugin_motive"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.label(
            text="OptiTrack Documentation", icon_value=IconsLoader.get_icon("Info")
        )
        row = layout.row(align=True)
        
        row.operator("wm.url_open", text = "Website").url = "https://optitrack.com"
        row.operator("wm.url_open", text = "Documentation").url = "https://docs.optitrack.com/plugins/optitrack-blender-plugin/optitrack-blender-plugin"
