import bpy
import ipaddress
from bpy.types import Operator
import sys
from threading import Lock
from queue import Queue
import mathutils
import math
from .Modified_NatNetClient import NatNetClient

# Define a custom property to track states
bpy.types.WindowManager.connection_status = bpy.props.BoolProperty(name="Connection Status", default=False)
bpy.types.WindowManager.start_status = bpy.props.BoolProperty(name="Start Status", default=False)
# 1 - selective keyframes, 2 - no definitive keyframes
bpy.types.WindowManager.record1_status = bpy.props.BoolProperty(name="Record Status", default=False)
bpy.types.WindowManager.record2_status = bpy.props.BoolProperty(name="Record Status", default=False)

class ConnectionSetup:
    def __init__(self):
        self.streaming_client = None
        self.indicate_model_changed = None
        self.indicate_motive_edit = None
        self.rigid_bodies_motive = {}
        self.rigid_bodies_blender = {} # ({motive_ID: blender_ID} pair)
        self.rev_rigid_bodies_blender = {} # ({blender_ID: {object, motive_ID}} pair)
        self.q = Queue()
        self.l = Lock()
        self.is_running = None
        self.frame_start = 0
        self.live_record = False

    def reset_to_initial(self):
        self.streaming_client = None
        self.indicate_model_changed = None
        self.indicate_motive_edit = None
        self.rigid_bodies_motive = {}
        self.rigid_bodies_blender = {}
        self.rev_rigid_bodies_blender = {} 
        self.q = Queue()
        self.l = Lock()
        self.is_running = None
        self.frame_start = 0
        self.live_record = False

    def signal_model_changed(self, tracked_model_changed): # flag to keep checking if Motive .tak changed
        self.indicate_model_changed = tracked_model_changed
    
    def signal_motive_edit(self, edit_mode): # flag for live/edit mode in Motive
        self.indicate_motive_edit = edit_mode

    def connect_button_clicked(self, dict, context):
        if self.streaming_client is not None:
            self.streaming_client.set_client_address(dict["clientAddress"])
            self.streaming_client.set_server_address(dict["serverAddress"])
            self.streaming_client.set_use_multicast(dict["use_multicast"])

            self.is_running = self.streaming_client.run()
            
            # send commands to Motive to change its settings
            if self.is_running:            
                sz_commands = [ "SetProperty,,Labeled Markers,false",
                                "SetProperty,,Unlabeled Markers,false",
                                "SetProperty,,Asset Markers,false",
                                "SetProperty,,Rigid Bodies,true"
                                "SetProperty,,Skeletons,false",
                                "SetProperty,,Trained Markerset Markers,false",
                                "SetProperty,,Trained Markerset Bones,false",
                                "SetProperty,,Devices,false",
                                "SetProperty,,Skeleton Coordinates,Global",
                                "SetProperty,,Bone Naming Convention,FBX",
                                "SetProperty,,Up Axis,Y-Axis"]
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
                self.streaming_client.model_changed = self.signal_model_changed
                self.streaming_client.rigid_body_listener = self.receive_rigid_body_frame
                self.streaming_client.motive_edit = self.signal_motive_edit
                # Update start state
                context.window_manager.start_status = True

    def get_rigid_body_dict(self, context): # array of all rigid bodies in the .tak
        self.rigid_bodies_motive = self.streaming_client.desc_dict
    
    def request_data_descriptions(self, s_client, context):
        # Request the model definitions
        return_code = s_client.send_modeldef_command()
    
    def quat_loc_yup_zup(self, pos):
        # Motive's [X, Y, Z] -> Blender [-X, Z, Y]
        pos_copy = [0]*3
        pos_copy[0] = -pos[0]
        pos_copy[1] = pos[2]
        pos_copy[2] = pos[1]
        return pos_copy
    
    def quat_product(self, r, s):
        t0 = (r[0]*s[0] - r[1]*s[1] - r[2]*s[2] - r[3]*s[3])
        t1 = (r[0]*s[1] + r[1]*s[0] - r[2]*s[3] + r[3]*s[2])
        t2 = (r[0]*s[2] + r[1]*s[3] + r[2]*s[0] - r[3]*s[1])
        t3 = (r[0]*s[3] - r[1]*s[2] + r[2]*s[1] + r[3]*s[0])
        return [t0, t1, t2, t3]

    def quat_rot_yup_zup(self, ori):
        # Motive's quat p -> Blender's quat p' = qpq^(-1)
        q = [0, (1/math.sqrt(2)), (1/math.sqrt(2)), 0]
        q_inv = [0, -(1/math.sqrt(2)), -(1/math.sqrt(2)), 0]
        p_1 = self.quat_product(q, ori)
        p_dash = self.quat_product(p_1, q_inv)
        return p_dash
    
    def sca_first_last(self, ori):
        ori.append(ori.pop(0))
        return ori
    
    def sign(self, num):
        return int(num/abs(num)) if num != 0 else 0
    
    def quat_to_euler(self, ori):
        ori = mathutils.Quaternion(ori)
        ori = ori.to_matrix()
        eul = ori.to_euler('ZYX')
        return eul
    
    def receive_rigid_body_frame(self, new_id, position, rotation, frame_number):
        if new_id in self.rigid_bodies_blender:
            # Y-Up
            pos = list(position)
            rot = list(rotation)

            # Z-Up with quats
            pos = self.quat_loc_yup_zup(position)
            rot = self.quat_rot_yup_zup(rotation)
            
            # (x, y, z, w) -> (w, x, y, z)
            rot = self.sca_first_last(rot)
            
            values = (new_id, pos, rot, frame_number)
            self.l.acquire()
            try:
                self.q.put(values)
            finally:
                self.l.release()
                bpy.app.timers.register(self.update_object_loc, first_interval=1/120) # freq = 120 Hz
        else:
            pass
                        
    def update_object_loc(self):
        if self.rigid_bodies_blender:
            self.l.acquire()
            try:
                if not self.q.empty(): 
                    q_val = self.q.get()
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
                                current_frame = (q_val[3] - self.frame_start)
                                print("current_frame: ", current_frame)
                                bpy.context.scene.frame_set(current_frame)
                                my_obj = self.rev_rigid_bodies_blender[self.rigid_bodies_blender[q_val[0]]]['obj'] # new_id
                                my_obj.location = q_val[1]
                                my_obj.keyframe_insert(data_path="location", frame=current_frame)
                                my_obj.rotation_mode = 'QUATERNION'
                                my_obj.rotation_quaternion = q_val[2]
                                my_obj.keyframe_insert(data_path="rotation_quaternion",frame=current_frame)
                            
                            # selective keyframes
                            elif bpy.context.window_manager.record1_status == True:
                                bpy.context.window_manager.record2_status = False
                                if self.live_record == False:
                                    self.frame_start = q_val[3]
                                self.live_record = True
                                current_frame = (q_val[3] - self.frame_start)
                                if bpy.context.scene.frame_start <= current_frame <= bpy.context.scene.frame_end:
                                    bpy.context.scene.frame_set(current_frame)
                                    my_obj = self.rev_rigid_bodies_blender[self.rigid_bodies_blender[q_val[0]]]['obj']
                                    my_obj.location = q_val[1]
                                    my_obj.keyframe_insert(data_path="location", frame=current_frame)
                                    my_obj.rotation_mode = 'QUATERNION'
                                    my_obj.rotation_quaternion = q_val[2]
                                    my_obj.keyframe_insert(data_path="rotation_quaternion",frame=current_frame)

                            # no recording
                            else:
                                my_obj = self.rev_rigid_bodies_blender[self.rigid_bodies_blender[q_val[0]]]['obj']
                                my_obj.location = q_val[1]
                                my_obj.rotation_mode = 'QUATERNION'
                                my_obj.rotation_quaternion = q_val[2]
                        
                        # edit mode
                        else:                    
                            # no definitive keyframes
                            if bpy.context.window_manager.record2_status == True:
                                bpy.context.window_manager.record1_status = False
                                if bpy.context.scene.frame_end <= q_val[3]:
                                    bpy.context.scene.frame_end = q_val[3]
                                bpy.context.scene.frame_set(q_val[3])
                                my_obj = self.rev_rigid_bodies_blender[self.rigid_bodies_blender[q_val[0]]]['obj'] # new_id
                                my_obj.location = q_val[1]
                                my_obj.keyframe_insert(data_path="location", frame=q_val[3])
                                my_obj.rotation_mode = 'QUATERNION'
                                my_obj.rotation_quaternion = q_val[2]
                                my_obj.keyframe_insert(data_path="rotation_quaternion",frame=q_val[3])

                            # selective keyframes
                            elif bpy.context.window_manager.record1_status == True:
                                bpy.context.window_manager.record2_status = False
                                if bpy.context.scene.frame_start <= q_val[3] <= bpy.context.scene.frame_end:
                                    bpy.context.scene.frame_set(q_val[3])
                                    my_obj = self.rev_rigid_bodies_blender[self.rigid_bodies_blender[q_val[0]]]['obj']
                                    my_obj.location = q_val[1]
                                    my_obj.keyframe_insert(data_path="location", frame=q_val[3])
                                    my_obj.rotation_mode = 'QUATERNION'
                                    my_obj.rotation_quaternion = q_val[2]
                                    my_obj.keyframe_insert(data_path="rotation_quaternion",frame=q_val[3])

                            # no recording
                            else:
                                my_obj = self.rev_rigid_bodies_blender[self.rigid_bodies_blender[q_val[0]]]['obj']
                                my_obj.location = q_val[1]
                                my_obj.rotation_mode = 'QUATERNION'
                                my_obj.rotation_quaternion = q_val[2]

                    except KeyError:
                        # if object id updated in middle of the running .tak
                        pass
            finally:
                self.l.release()
        else:
            pass
    
    def stop_receive_rigid_body_frame(self, new_id, position, rotation, frame_number):
        pass

    def pause_button_clicked(self, context): # Stop the data stream, but don't update the stored info        
        if self.streaming_client:
            self.streaming_client.rigid_body_listener = self.stop_receive_rigid_body_frame
            context.window_manager.start_status = False
    
    def stop_button_clicked(self, context): # Stop connection
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
        conn = self.connection_setup
        # Initialize streaming client       
        if conn.streaming_client is None:
            optionsDict = {'clientAddress': bpy.context.scene.init_prop.client_address, \
                           'serverAddress': bpy.context.scene.init_prop.server_address, \
                            'use_multicast': True}
            
            # check the ips
            try:
                ipaddress.ip_address(optionsDict["clientAddress"])
            except ValueError:
                self.report({'ERROR'}, "Client IP is not valid")
                conn.reset_to_initial()
                return {'CANCELLED'}
        
            try:
                ipaddress.ip_address(optionsDict["serverAddress"])
            except ValueError:
                self.report({'ERROR'}, "Server IP is not valid")
                conn.reset_to_initial()
                return {'CANCELLED'}
            
            conn.streaming_client = NatNetClient()
        try:
            conn.connect_button_clicked(optionsDict, context)
            conn.request_data_descriptions(conn.streaming_client, context)
            print("connected")
            from .app_handlers import object_handler
            object_handler(context.scene)
        except Exception as e:
            print("error: ", e)
            conn.streaming_client = None
            context.window_manager.connection_status = False
            self.report({'ERROR'}, f"Your Motive is not set to Multicast")
            return {'CANCELLED'}
    
        return {'FINISHED'}

class RefreshAssetsOperator(Operator):
    bl_idname = "wm.refresh_button"
    bl_description = "Refresh the asset list"
    bl_label = "Refresh Assets"

    def execute(self, context):
        existing_connection = ConnectOperator.connection_setup
        existing_connection.request_data_descriptions(existing_connection.streaming_client, context)
        if context.window_manager.start_status:
            existing_connection.pause_button_clicked(context)
        return {'FINISHED'}

class StartOperator(Operator):
    bl_idname = "wm.start_button"
    bl_description = "Start receiving the data for every frame"
    bl_label = "Start Receiver"

    def execute(self, context):
        ConnectOperator.connection_setup.start_button_clicked(context)
        return {'FINISHED'}

class PauseOperator(Operator):
    bl_idname = "wm.pause_button"
    bl_description = "Stop the data coming in but don't reset the connection"
    bl_label = "Pause"
    
    def execute(self, context):
        if ConnectOperator.connection_setup is not None:
            ConnectOperator.connection_setup.pause_button_clicked(context)
        return {'FINISHED'}

class StartRecordOperator(Operator):
    bl_idname = "wm.start_record2"
    bl_description = "Start recording"
    bl_label = "Start Record"

    def execute(self, context):
        if ConnectOperator.connection_setup is not None:
            context.window_manager.record2_status = True
            context.window_manager.record1_status = False
        return {'FINISHED'}

class StopRecordOperator(Operator):
    bl_idname = "wm.stop_record2"
    bl_description = "Stop recording"
    bl_label = "Stop"

    def execute(self, context):
        if ConnectOperator.connection_setup is not None:
            context.window_manager.record2_status = False
            ConnectOperator.connection_setup.live_record = False
        return {'FINISHED'}

class StartEndFrameOperator(Operator):
    bl_idname = "wm.set_frame"
    bl_description = "Set Frames for Recording"
    bl_label = "Set Frames for Recording"

    start_frame : bpy.props.IntProperty(name= "Start Frame", default=0)
    end_frame : bpy.props.IntProperty(name= "End Frame", default=250)

    def execute(self, context):
        initprop = context.scene.init_prop
        bpy.context.scene.frame_start = self.start_frame
        bpy.context.scene.frame_end = self.end_frame
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class StartFrameRecordOperator(Operator):
    bl_idname = "wm.start_record1"
    bl_description = "Start recording"
    bl_label = "Start Record"

    def execute(self, context):
        if ConnectOperator.connection_setup is not None:
            context.window_manager.record1_status = True
            context.window_manager.record2_status = False
        return {'FINISHED'}

class StopFrameRecordOperator(Operator):
    bl_idname = "wm.stop_record1"
    bl_description = "Stop recording"
    bl_label = "Stop"

    def execute(self, context):
        if ConnectOperator.connection_setup is not None:
            context.window_manager.record1_status = False
        return {'FINISHED'}

class newActionOperator(Operator):
    bl_idname = "wm.new_action"
    bl_description = "Creates a new Action to record data onto"
    bl_label = "Create New Action"

    def execute(self, context):
        if context.view_layer.objects.active:
            obj = context.view_layer.objects.active
            obj.select_set(True)
            obj.animation_data_clear()
        return {'FINISHED'}

class deleteActionOperator(Operator):
    bl_idname = "wm.delete_action"
    bl_description = "Delete the most recent action from Action Editor"
    bl_label = "Delete Action"

    def execute(self, context):
        # bpy.context.area.type = 'DOPESHEET_EDITOR'
        # bpy.context.space_data.mode = 'ACTION'
        action = bpy.data.actions[-1] # Get the most recent action
        print(action)
        bpy.context.object.animation_data.action = action # Set the action as active
        bpy.data.actions.remove(action)
        # bpy.ops.action.delete() # Delete the action
        return {'FINISHED'}

class ResetOperator(Operator): 
    bl_idname = "object.reset_operator"
    bl_description = "Reset the connection"
    bl_label = "Stop Connection"

    def execute(self, context):
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
        bpy.ops.object.select_all(action='DESELECT')
        return {'FINISHED'}