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

class ConnectionSetup:
    def __init__(self):
        self.streaming_client = None
        self.indicate_model_changed = None
        self.rigid_bodies_motive = {}
        self.rigid_bodies_blender = {} # all objects getting stored ({ID: rigid_body} pair)
        self.rev_rigid_bodies_blender = {} # ({rigid_body: ID} pair)
        self.q = Queue()
        self.l = Lock()
        self.is_running = None

    def reset_to_initial(self):
        self.streaming_client = None
        self.indicate_model_changed = None
        self.rigid_bodies_motive = {}
        self.rigid_bodies_blender = {}
        self.rev_rigid_bodies_blender = {} 
        self.q = Queue()
        self.l = Lock()
        self.is_running = None

    def signal_model_changed(self, tracked_model_changed): # flag to keep checking if Motive .tak changed
        self.indicate_model_changed = tracked_model_changed

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
                return_code = self.streaming_client.send_command("SetProperty,,Skeletons,false")

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
                # Update start state
                context.window_manager.start_status = True

    def get_rigid_body_dict(self, context): # array of all rigid bodies in the .tak
        self.rigid_bodies_motive = self.streaming_client.desc_dict
    
    def request_data_descriptions(self, s_client, context):
        # Request the model definitions
        return_code = s_client.send_modeldef_command()
    
    def quat_loc_yup_zup(self, pos):
        # temp = pos[1]
        # pos[1] = -1*pos[2]
        # pos[2] = temp
        # Motive's [X, Y, Z] -> Blender [-X, Z, Y]
        pos_copy = [0]*3
        pos_copy[0] = -pos[0]
        pos_copy[1] = pos[2]
        pos_copy[2] = pos[1]
        return pos_copy
        # return pos
    
    def quat_product(self, r, s):
        t0 = (r[0]*s[0] - r[1]*s[1] - r[2]*s[2] - r[3]*s[3])
        t1 = (r[0]*s[1] + r[1]*s[0] - r[2]*s[3] + r[3]*s[2])
        t2 = (r[0]*s[2] + r[1]*s[3] + r[2]*s[0] - r[3]*s[1])
        t3 = (r[0]*s[3] - r[1]*s[2] + r[2]*s[1] + r[3]*s[0])
        return [t0, t1, t2, t3]

    def quat_rot_yup_zup(self, ori):
        # temp = ori[1]
        # ori[1] = -1*ori[2]
        # ori[2] = temp
        # Motive's quat p -> Blender's p' = qpq^(-1)
        q = [0, (1/math.sqrt(2)), (1/math.sqrt(2)), 0]
        # q^(-1) = [q0, -q1, -q2, -q3]
        q_inv = [0, -(1/math.sqrt(2)), -(1/math.sqrt(2)), 0]
        p_1 = self.quat_product(q, ori)
        p_dash = self.quat_product(p_1, q_inv)
        return p_dash
        # return ori
    
    def eul_loc_yup_zup(self, pos):
        # Rot_matrix = [[-1, 0, 0], [0, 0, 1], [0, 1, 0]]
        pos_copy = [-pos[0], pos[2], pos[1]]
        return pos_copy
    
    def eul_rot_yup_zup(self, ori):
        ori_copy = [-ori[0], ori[2], ori[1]]
        return ori_copy
    
    def sca_first_last(self, ori):
        ori.append(ori.pop(0))
        return ori
    
    def sign(self, num):
        return int(num/abs(num)) if num != 0 else 0
    
    def quat_to_euler(self, ori):
        ori = mathutils.Quaternion(ori)
        # ori = ori.to_matrix()
        # ori = ori.to_euler('ZYX') # somehow matches XYZ
        # print("rad rot: ", [i for i in ori])
        # print("deg rot: ", [i*57.296 for i in ori])

        # custom function - ZYX answer
        # # x-axis rotation (roll)
        # x = math.atan2(2 * ((ori.w * ori.x) + (ori.y * ori.z)), 1 - (2 * ((ori.x * ori.x) + (ori.y * ori.y)))) 
        # # y-axis rotation (pitch)
        # y = (2 * math.atan2(math.sqrt(1 + (2 * ((ori.w * ori.y) - (ori.x * ori.z)))), /
        # math.sqrt(1 - (2 * ((ori.w * ori.y) - (ori.x * ori.z)))))) - (math.pi/2)
        # # z-axis rotation (yaw)
        # z = math.atan2(2 * ((ori.w * ori.z) + (ori.x * ori.y)), 1 - (2 * ((ori.y * ori.y) + (ori.z * ori.z))))
        
        # custom function - XYZ answer
        x = math.atan2(-2*(ori.y*ori.z - ori.w*ori.x), ori.w*ori.w - ori.x*ori.x - ori.y*ori.y + ori.z*ori.z)
        y = math.asin ( 2*(ori.x*ori.z + ori.w*ori.y) )
        z = math.atan2(-2*(ori.x*ori.y - ori.w*ori.z), ori.w*ori.w + ori.x*ori.x - ori.y*ori.y - ori.z*ori.z)
        
        x = -self.sign(x) * (math.pi - abs(x))
        z = -self.sign(z) * (math.pi - abs(z))
        eul = [x, y, z]
        # euler = [i*57.29578 for i in eul]
        # print("euler: ", euler)
        return eul
    
    # This is a callback function that gets connected to the NatNet client. It is called once per rigid body per frame
    def receive_rigid_body_frame(self, new_id, position, rotation):
        if new_id in self.rigid_bodies_blender:
            # Y-Up
            pos = list(position)
            rot = list(rotation)

            # Z-Up with quats
            # pos = self.quat_loc_yup_zup(position)
            # rot = self.quat_rot_yup_zup(rotation)
            
            rot = self.sca_first_last(rot)
            rot = self.quat_to_euler(rot)
            
            # z-up with eulers
            # pos = self.eul_loc_yup_zup(position)
            # rot = self.eul_rot_yup_zup(rot)
            
            values = (new_id, pos, rot)
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
                        my_obj = self.rigid_bodies_blender[q_val[0]] # new_id
                        my_obj.location = q_val[1]
                        # my_obj.rotation_mode = 'QUATERNION'
                        # my_obj.rotation_quaternion = q_val[2]
                        my_obj.rotation_mode = 'XYZ'
                        my_obj.rotation_euler = q_val[2] 
                    except KeyError:
                        # if object id updated in middle of the running .tak
                        pass
            finally:
                self.l.release()
        else:
            pass
    
    def stop_receive_rigid_body_frame(self, new_id, position, rotation):
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

class ConnectButtonOperator(Operator):
    bl_idname = "wm.connect_button"
    bl_description = "Establish the connection"
    bl_label = "Start Connection"

    # def server_error(self, context):
        
    # def client_error(self, context):
        

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
                # context.window_manager.popup_menu(self.client_error(context))
                conn.reset_to_initial()
                return {'CANCELLED'}
        
            try:
                ipaddress.ip_address(optionsDict["serverAddress"])
            except ValueError:
                self.report({'ERROR'}, "Server IP is not valid")
                # context.window_manager.popup_menu(self.server_error(context))
                conn.reset_to_initial()
                return {'CANCELLED'}
            
            conn.streaming_client = NatNetClient()
        conn.connect_button_clicked(optionsDict, context)
        print("connected")
        conn.request_data_descriptions(conn.streaming_client, context)
        from .app_handlers import reset_to_default
        reset_to_default(context.scene)
        return {'FINISHED'}

class RefreshAssetsOperator(Operator):
    bl_idname = "wm.refresh_button"
    bl_description = "Refresh the asset list"
    bl_label = "Refresh Assets"

    def execute(self, context):
        existing_connection = ConnectButtonOperator.connection_setup
        existing_connection.request_data_descriptions(existing_connection.streaming_client, context)
        if context.window_manager.start_status:
            existing_connection.pause_button_clicked(context)
        return {'FINISHED'}


class StartButtonOperator(Operator):
    bl_idname = "wm.start_button"
    bl_description = "Start receiving the data for every frame"
    bl_label = "Start Receiver"

    def execute(self, context):
        ConnectButtonOperator.connection_setup.start_button_clicked(context)
        return {'FINISHED'}

class PauseButtonOperator(Operator):
    bl_idname = "wm.pause_button"
    bl_description = "Stop the data coming in but don't reset the connection"
    bl_label = "Pause"
    
    def execute(self, context):
        if ConnectButtonOperator.connection_setup is not None:
            ConnectButtonOperator.connection_setup.pause_button_clicked(context)
        return {'FINISHED'}

class ResetOperator(Operator): 
    bl_idname = "object.reset_operator"
    bl_description = "Reset the connection"
    bl_label = "Stop Connection"

    def execute(self, context):
        if ConnectButtonOperator.connection_setup is not None:
            existing_connection = ConnectButtonOperator.connection_setup
            existing_connection.stop_button_clicked(context)
            existing_connection.reset_to_initial()
        
        existing_connection = None
        
        # Delete all custom properties of each object from collection of properties
        for attr in dir(bpy.data):
            if "bpy_prop_collection" in str(type(getattr(bpy.data, attr))):
                for obj in getattr(bpy.data, attr):
                    for custom_prop_name in list(obj.keys()):
                        del obj[custom_prop_name]

        # Deselect all objects
        bpy.ops.object.select_all(action='DESELECT')
        return {'FINISHED'}