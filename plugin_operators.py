import ipaddress
import math
import os
import sys
from queue import Queue
from threading import Lock

import bpy
import mathutils
from bpy.types import Operator

from .Modified_NatNetClient import NatNetClient
from .repository.action import ActionRepository
from .repository.skeleton import BoneData, SkeletonData, SkeletonRepository

# Define a custom property to track states
bpy.types.WindowManager.connection_status = bpy.props.BoolProperty(
    name="Connection Status", default=False
)
bpy.types.WindowManager.start_status = bpy.props.BoolProperty(
    name="Start Status", default=False
)
# 1 - selective keyframes, 2 - no definitive keyframes
bpy.types.WindowManager.record1_status = bpy.props.BoolProperty(
    name="Record Status", default=False
)
bpy.types.WindowManager.record2_status = bpy.props.BoolProperty(
    name="Record Status", default=False
)


class ConnectionSetup:
    def __init__(self):
        self.streaming_client = None
        self.indicate_model_changed = None
        self.indicate_motive_edit = None
        self.assets_motive = {}  # ( {assetType: {motive_ID: motive_name}} )
        self.assets_blender = {}  # ( {assetType: {motive_ID: blender_ID}} )
        self.rev_assets_blender = {}  # ( {blender_ID: {object, motive_ID, assetType}} )
        self.q = Queue()
        self.l = Lock()
        self.is_running = None
        self.frame_start = 0
        self.live_record = False
        self.bone_convention = "FBX"

    def reset_to_initial(self):
        self.streaming_client = None
        self.indicate_model_changed = None
        self.indicate_motive_edit = None
        self.assets_motive = {}
        self.assets_blender = {}
        self.rev_assets_blender = {}
        self.q = Queue()
        self.l = Lock()
        self.is_running = None
        self.frame_start = 0
        self.live_record = False
        self.bone_convention = "FBX"

    # def signal_model_changed(self, tracked_model_changed): # flag to keep checking if Motive .tak changed
    #     self.indicate_model_changed = tracked_model_changed

    # def signal_motive_edit(self, edit_mode): # flag for live/edit mode in Motive
    #     self.indicate_motive_edit = edit_mode

    def connect_button_clicked(self, dict, context):
        if self.streaming_client is not None:
            self.streaming_client.set_client_address(dict["clientAddress"])
            self.streaming_client.set_server_address(dict["serverAddress"])
            self.streaming_client.set_use_multicast(dict["use_multicast"])

            self.is_running = self.streaming_client.run()

            # send commands to Motive to change its settings
            if self.is_running:
                sz_commands = [
                    "SetProperty,,Labeled Markers,false",
                    "SetProperty,,Unlabeled Markers,false",
                    "SetProperty,,Asset Markers,false",
                    "SetProperty,,Rigid Bodies,true",
                    "SetProperty,,Skeletons,true",
                    "SetProperty,,Trained Markerset Markers,false",
                    "SetProperty,,Trained Markerset Bones,false",
                    "SetProperty,,Devices,false",
                    # "SetProperty,,Skeleton Coordinates,Global",
                    "SetProperty,,Skeleton Coordinates,Local",
                    "SetProperty,,Bone Naming Convention," + str(self.bone_convention),
                    "SetProperty,,Up Axis,Y-Axis",
                ]
                for sz_command in sz_commands:
                    return_code = self.streaming_client.send_command(sz_command)

            # Update connection state
            context.window_manager.connection_status = True

        else:
            context.window_manager.connection_status = False
            try:
                sys.exit(1)
            except SystemExit:
                print("...")
            finally:
                print("exiting")

    def start_button_clicked(self, context):
        if context.window_manager.connection_status:
            self.streaming_client.data_listener = self.receive_data_frame

            # Update start state
            context.window_manager.start_status = True

    def get_desc_dict(self, context):  # array of all rigid bodies in the .tak
        if self.streaming_client.desc_dict != self.assets_motive:
            for k, v in self.rev_assets_blender.items():
                v["m_ID"] = "None"
            self.assets_blender = {}
            # print(self.assets_blender, self.rev_assets_blender)
        self.assets_motive = self.streaming_client.desc_dict

    def request_data_descriptions(self, s_client, context):
        # Request the model definitions
        return_code = s_client.send_modeldef_command()

    def add_ls(self, ls1, ls2):
        added = list()
        for item1, item2 in zip(ls1, ls2):
            item = item1 + item2
            added.append(item)
        return added

    def subtract_ls(self, ls1, ls2):
        subtracted = list()
        for item1, item2 in zip(ls1, ls2):
            item = item1 - item2
            subtracted.append(item)
        return subtracted

    def quat_loc_yup_zup(self, pos):
        # Motive's [X, Y, Z] -> Blender [X, -Z, Y]
        pos_copy = [0] * 3
        pos_copy[0] = pos[0]
        pos_copy[1] = -pos[2]
        pos_copy[2] = pos[1]
        return pos_copy

    def quat_rot_yup_zup(self, ori):
        # Motive's quat p -> Blender's quat p' = qpq^(-1)
        ori_quat = mathutils.Quaternion((ori[3], ori[0], ori[1], ori[2]))
        convert3 = mathutils.Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))
        return (convert3 @ ori_quat.to_matrix() @ convert3.inverted()).to_quaternion()

    def sca_first_last(self, ori):
        ori = list(ori)  # comment out later
        ori.append(ori.pop(0))
        return ori

    def sign(self, num):
        return int(num / abs(num)) if num != 0 else 0

    def quat_to_euler(self, ori):
        ori = mathutils.Quaternion(ori)
        ori = ori.to_matrix()
        eul = ori.to_euler("ZYX")
        return eul

    # def quat_modification(self, q): # only resolves lower body
    #     q_new = [0, 0, 0, 0]
    #     q_new[0] = -q[2]
    #     q_new[1] = q[3]
    #     q_new[2] = q[1]
    #     q_new[3] = q[0]
    #     return q_new

    def transform(self, rot_transform, rot):
        return rot_transform @ rot

    def transform_back(self, rot_transform, rot):
        return rot_transform.inverted() @ rot

    def armature_rb_transform(self, obj):
        mat_obj = obj.matrix_local.decompose()[1].to_matrix().to_4x4()
        mat_default = mathutils.Matrix(
            ((-1, 0, 0, 0), (0, 0, -1, 0), (0, -1, 0, 0), (0, 0, 0, 1))
        )  # Blender to Motive?
        rot_transform = (mat_default.inverted() @ mat_obj).to_quaternion()
        return rot_transform

    def receive_data_frame(self, data_dict):
        self.indicate_model_changed = data_dict["tracked_models_changed"]
        self.indicate_motive_edit = data_dict["edit_mode"]
        frame_num = data_dict["frame_number"]

        values = []

        for key1 in data_dict["rb_data"]:
            if ("rigid_body" in self.assets_blender) and (
                key1 in self.assets_blender["rigid_body"]
            ):
                m_val = data_dict["rb_data"][key1]  # rb.m_id = key1
                b_id = self.assets_blender["rigid_body"][key1]["b_ID"]

                # Z-Up with quats
                pos1 = self.quat_loc_yup_zup(m_val["pos"])
                rot1 = self.quat_rot_yup_zup(m_val["rot"])

                # sequence -> (assetID, pos, rot, frame_num, assetType, ske_rb)
                value = (b_id, pos1, rot1, frame_num, "rigid_body", None)
                values.append(value)

        for skeleton_id, frame_data in data_dict["ske_data"].items():
            skeleton_data = SkeletonRepository.get_by_id(skeleton_id=skeleton_id)
            frame_data = skeleton_data.create_frame_data(data=frame_data)
            values.append(
                (skeleton_id, skeleton_data, None, frame_num, "skeleton", frame_data)
            )

        self.l.acquire()
        try:
            self.q.put(values)
        finally:
            self.l.release()
            bpy.app.timers.register(
                self.update_object_loc, first_interval=1 / 120
            )  # freq = 120 Hz

    def update_object_loc(self):
        self.l.acquire()
        try:
            if not self.q.empty():
                q_vals = self.q.get()
                for q_val in q_vals:
                    try:
                        # live mode
                        if self.indicate_motive_edit == False:
                            # no definitive keyframes
                            if bpy.context.window_manager.record2_status == True:
                                bpy.context.window_manager.record1_status = False
                                if self.live_record == False:
                                    self.frame_start = q_val[3]
                                    print("frame start: ", self.frame_start)
                                self.live_record = True
                                current_frame = q_val[3] - self.frame_start
                                print("current_frame: ", current_frame)
                                bpy.context.scene.frame_set(current_frame)
                                # q_val[5] -> assetType, q_val[0] -> rbID

                                if q_val[4] == "rigid_body":
                                    my_obj = self.rev_assets_blender[q_val[0]]["obj"]
                                    my_obj.location = q_val[1]
                                    my_obj.rotation_mode = "QUATERNION"
                                    my_obj.rotation_quaternion = q_val[2]

                                    ActionRepository.assign_action(my_obj)
                                    my_obj.keyframe_insert(
                                        data_path="location", frame=current_frame
                                    )

                                    my_obj.keyframe_insert(
                                        data_path="rotation_quaternion",
                                        frame=current_frame,
                                    )

                                elif q_val[4] == "skeleton":
                                    (
                                        skeleton_id,
                                        skeleton_data,
                                        _,
                                        frame_num,
                                        _,
                                        frame_data,
                                    ) = q_val
                                    SkeletonRepository.render_skeletons_and_insert_keyframe(
                                        keyframe_num=frame_num,
                                        target_skeleton_data=skeleton_data,
                                        frame_data=frame_data,
                                    )

                            # selective keyframes
                            elif bpy.context.window_manager.record1_status == True:
                                bpy.context.window_manager.record2_status = False
                                if self.live_record == False:
                                    self.frame_start = q_val[3]
                                self.live_record = True
                                current_frame = q_val[3] - self.frame_start
                                if (
                                    bpy.context.scene.frame_start
                                    <= current_frame
                                    <= bpy.context.scene.frame_end
                                ):
                                    bpy.context.scene.frame_set(current_frame)
                                    # my_obj = self.rev_assets_blender[self.assets_blender[q_val[0]]]['obj']
                                    if q_val[4] == "rigid_body":
                                        my_obj = self.rev_assets_blender[q_val[0]][
                                            "obj"
                                        ]
                                        my_obj.location = q_val[1]
                                        my_obj.rotation_mode = "QUATERNION"
                                        my_obj.rotation_quaternion = q_val[2]

                                        ActionRepository.assign_action(my_obj)
                                        my_obj.keyframe_insert(
                                            data_path="location",
                                            frame=current_frame,
                                        )
                                        my_obj.keyframe_insert(
                                            data_path="rotation_quaternion",
                                            frame=current_frame,
                                        )
                                    elif q_val[4] == "skeleton":
                                        (
                                            skeleton_id,
                                            skeleton_data,
                                            _,
                                            frame_num,
                                            _,
                                            frame_data,
                                        ) = q_val
                                        SkeletonRepository.render_skeletons_and_insert_keyframe(
                                            keyframe_num=frame_num,
                                            target_skeleton_data=skeleton_data,
                                            frame_data=frame_data,
                                        )

                            # no recording
                            else:
                                # my_obj = self.rev_assets_blender[self.assets_blender[q_val[0]]]['obj']
                                if q_val[4] == "rigid_body":
                                    my_obj = self.rev_assets_blender[q_val[0]]["obj"]
                                    my_obj.location = q_val[1]
                                    my_obj.rotation_mode = "QUATERNION"
                                    my_obj.rotation_quaternion = q_val[2]
                                elif q_val[4] == "skeleton":
                                    skeleton_id, skeleton_data, _, _, _, frame_data = (
                                        q_val
                                    )
                                    SkeletonRepository.render_skeletons_and_insert_keyframe(
                                        target_skeleton_data=skeleton_data,
                                        frame_data=frame_data,
                                    )

                        # edit mode
                        else:
                            # no definitive keyframes
                            if bpy.context.window_manager.record2_status == True:
                                bpy.context.window_manager.record1_status = False
                                if bpy.context.scene.frame_end <= q_val[3]:
                                    bpy.context.scene.frame_end = q_val[3]
                                bpy.context.scene.frame_set(q_val[3])
                                # my_obj = self.rev_assets_blender[self.assets_blender[q_val[0]]]['obj']\
                                #  # new_id
                                if q_val[4] == "rigid_body":
                                    my_obj = self.rev_assets_blender[q_val[0]]["obj"]
                                    my_obj.location = q_val[1]
                                    my_obj.rotation_mode = "QUATERNION"
                                    my_obj.rotation_quaternion = q_val[2]

                                    ActionRepository.assign_action(my_obj)
                                    my_obj.keyframe_insert(
                                        data_path="location", frame=q_val[3]
                                    )
                                    my_obj.keyframe_insert(
                                        data_path="rotation_quaternion",
                                        frame=q_val[3],
                                    )
                                elif q_val[4] == "skeleton":
                                    (
                                        skeleton_id,
                                        skeleton_data,
                                        _,
                                        frame_num,
                                        _,
                                        frame_data,
                                    ) = q_val
                                    SkeletonRepository.render_skeletons_and_insert_keyframe(
                                        keyframe_num=frame_num,
                                        target_skeleton_data=skeleton_data,
                                        frame_data=frame_data,
                                    )

                            # selective keyframes
                            elif bpy.context.window_manager.record1_status == True:
                                bpy.context.window_manager.record2_status = False
                                if (
                                    bpy.context.scene.frame_start
                                    <= q_val[3]
                                    <= bpy.context.scene.frame_end
                                ):
                                    bpy.context.scene.frame_set(q_val[3])
                                    # my_obj = self.rev_assets_blender[self.assets_blender[q_val[0]]]['obj']
                                    if q_val[4] == "rigid_body":
                                        my_obj = self.rev_assets_blender[q_val[0]][
                                            "obj"
                                        ]
                                        my_obj.location = q_val[1]
                                        my_obj.rotation_mode = "QUATERNION"
                                        my_obj.rotation_quaternion = q_val[2]

                                        ActionRepository.assign_action(my_obj)
                                        my_obj.keyframe_insert(
                                            data_path="location", frame=q_val[3]
                                        )
                                        my_obj.keyframe_insert(
                                            data_path="rotation_quaternion",
                                            frame=q_val[3],
                                        )
                                    elif q_val[4] == "skeleton":
                                        (
                                            skeleton_id,
                                            skeleton_data,
                                            _,
                                            frame_num,
                                            _,
                                            frame_data,
                                        ) = q_val
                                        SkeletonRepository.render_skeletons_and_insert_keyframe(
                                            keyframe_num=frame_num,
                                            target_skeleton_data=skeleton_data,
                                            frame_data=frame_data,
                                        )

                            # no recording
                            else:
                                if q_val[4] == "rigid_body":
                                    my_obj = self.rev_assets_blender[q_val[0]]["obj"]
                                    my_obj.location = q_val[1]
                                    my_obj.rotation_mode = "QUATERNION"
                                    my_obj.rotation_quaternion = q_val[2]
                                elif q_val[4] == "skeleton":
                                    skeleton_id, skeleton_data, _, _, _, frame_data = (
                                        q_val
                                    )
                                    SkeletonRepository.render_skeletons_and_insert_keyframe(
                                        target_skeleton_data=skeleton_data,
                                        frame_data=frame_data,
                                    )
                    except KeyError:
                        # if object id updated in middle of the running .tak
                        pass
        finally:
            self.l.release()

    def stop_receive_rigid_body_frame(self, new_id, position, rotation, frame_number):
        pass

    def stop_receive_data_frame(self, data_dict):
        pass

    def pause_button_clicked(
        self, context
    ):  # Stop the data stream, but don't update the stored info
        if self.streaming_client:
            self.streaming_client.data_listener = self.stop_receive_data_frame
            context.window_manager.start_status = False

    def stop_button_clicked(self, context):  # Stop connection
        if self.streaming_client:
            self.streaming_client.shutdown()
            self.streaming_client = None
            context.window_manager.connection_status = False


class ConnectOperator(Operator):
    bl_idname = "wm.connect_button"
    bl_description = "Establish the connection"
    bl_label = "Start Connection"

    connection_setup = None
    if connection_setup is None:
        connection_setup = ConnectionSetup()

    def execute(self, context):
        SkeletonRepository.clear()

        conn = self.connection_setup
        # Initialize streaming client
        if conn.streaming_client is None:
            optionsDict = {
                "clientAddress": bpy.context.scene.init_prop.client_address,
                "serverAddress": bpy.context.scene.init_prop.server_address,
                "use_multicast": True,
            }

            # check the ips
            try:
                ipaddress.ip_address(optionsDict["clientAddress"])
            except ValueError:
                self.report({"ERROR"}, "Client IP is not valid")
                # conn.reset_to_initial()
                return {"CANCELLED"}

            try:
                ipaddress.ip_address(optionsDict["serverAddress"])
            except ValueError:
                self.report({"ERROR"}, "Server IP is not valid")
                conn.reset_to_initial()
                return {"CANCELLED"}

            conn.streaming_client = NatNetClient()
        try:
            conn.connect_button_clicked(optionsDict, context)
            conn.request_data_descriptions(conn.streaming_client, context)
            print("connected")
            from .app_handlers import object_handler

            object_handler(context.scene)
        except Exception as e:
            conn.streaming_client = None
            context.window_manager.connection_status = False
            if "'NoneType' object has no attribute 'sendto'" in str(e):
                self.report({"ERROR"}, f"Your Motive is not set to Multicast")
            else:
                self.report({"ERROR"}, f"Check Toggle System Console")
                print("error: ", e)
            return {"CANCELLED"}

        return {"FINISHED"}


class RefreshAssetsOperator(Operator):
    bl_idname = "wm.refresh_button"
    bl_description = "Refresh the asset list"
    bl_label = "Refresh Assets"

    def execute(self, context):
        SkeletonRepository.clear()

        existing_conn = ConnectOperator.connection_setup
        existing_conn.request_data_descriptions(existing_conn.streaming_client, context)
        if context.window_manager.start_status:
            existing_conn.pause_button_clicked(context)

        return {"FINISHED"}


class StartOperator(Operator):
    bl_idname = "wm.start_button"
    bl_description = "Start receiving the data for every frame"
    bl_label = "Start Receiver"

    def execute(self, context):
        ConnectOperator.connection_setup.start_button_clicked(context)
        SkeletonRepository.set_transform_matrix()
        return {"FINISHED"}


class PauseOperator(Operator):
    bl_idname = "wm.pause_button"
    bl_description = "Stop the data coming in but don't reset the connection"
    bl_label = "Pause"

    def execute(self, context):
        if ConnectOperator.connection_setup is not None:
            ConnectOperator.connection_setup.pause_button_clicked(context)
        return {"FINISHED"}


class StartRecordOperator(Operator):
    bl_idname = "wm.start_record2"
    bl_description = "Start recording"
    bl_label = "Start Record"

    def execute(self, context):
        ActionRepository.cache_fcurves(
            SkeletonRepository.get_render_skeletons(),
        )
        if ConnectOperator.connection_setup is not None:
            context.window_manager.record2_status = True
            context.window_manager.record1_status = False
        return {"FINISHED"}


class StopRecordOperator(Operator):
    bl_idname = "wm.stop_record2"
    bl_description = "Stop recording"
    bl_label = "Stop"

    def execute(self, context):
        if ConnectOperator.connection_setup is not None:
            context.window_manager.record2_status = False
            ConnectOperator.connection_setup.live_record = False
        return {"FINISHED"}


class StartEndFrameOperator(Operator):
    bl_idname = "wm.set_frame"
    bl_description = "Set Frames for Recording"
    bl_label = "Set Frames for Recording"

    start_frame: bpy.props.IntProperty(name="Start Frame", default=0)
    end_frame: bpy.props.IntProperty(name="End Frame", default=250)

    def execute(self, context):
        initprop = context.scene.init_prop
        bpy.context.scene.frame_start = self.start_frame
        bpy.context.scene.frame_end = self.end_frame
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class StartFrameRecordOperator(Operator):
    bl_idname = "wm.start_record1"
    bl_description = "Start recording"
    bl_label = "Start Record"

    def execute(self, context):
        ActionRepository.cache_fcurves(
            SkeletonRepository.get_render_skeletons(),
        )
        if ConnectOperator.connection_setup is not None:
            context.window_manager.record1_status = True
            context.window_manager.record2_status = False
        return {"FINISHED"}


class StopFrameRecordOperator(Operator):
    bl_idname = "wm.stop_record1"
    bl_description = "Stop recording"
    bl_label = "Stop"

    def execute(self, context):
        if ConnectOperator.connection_setup is not None:
            context.window_manager.record1_status = False
        return {"FINISHED"}


class newActionOperator(Operator):
    bl_idname = "wm.new_action"
    bl_description = "Creates a new Action to record data onto"
    bl_label = "Create New Action"

    def execute(self, context):
        ActionRepository.create_new_action()
        return {"FINISHED"}


class ResetOperator(Operator):
    bl_idname = "object.reset_operator"
    bl_description = "Reset the connection"
    bl_label = "Stop Connection"

    def execute(self, context):
        SkeletonRepository.clear()

        if ConnectOperator.connection_setup is not None:
            existing_connection = ConnectOperator.connection_setup
            existing_connection.stop_button_clicked(context)
            existing_connection.reset_to_initial()

        existing_connection = None

        for attr in dir(bpy.data):
            if "bpy_prop_collection" in str(type(getattr(bpy.data, attr))):
                for obj in getattr(bpy.data, attr):
                    for custom_prop_name in list(obj.keys()):
                        del obj[custom_prop_name]

        # Deselect all objects
        bpy.ops.object.select_all(action="DESELECT")
        return {"FINISHED"}
