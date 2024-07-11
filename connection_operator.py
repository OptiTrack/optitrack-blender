import bpy
import time
from bpy.types import Operator
import sys
from threading import Lock, Event
from queue import Queue
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

    def connect_button_clicked(self, context): 
        # Initialize streaming client       
        if self.streaming_client is None:
            optionsDict = {'clientAddress': bpy.context.scene.init_prop.client_address, 'serverAddress': bpy.context.scene.init_prop.server_address, 'use_multicast': True}
            self.streaming_client = NatNetClient()
            self.streaming_client.set_client_address(optionsDict["clientAddress"])
            self.streaming_client.set_server_address(optionsDict["serverAddress"])
            self.streaming_client.set_use_multicast(optionsDict["use_multicast"])

            self.is_running = self.streaming_client.run()
            
            # send commands to Motive to change its settings
            if self.is_running:            
                sz_commands = ["SetProperty,,Labeled Markers,false",
                                "SetProperty,,Unlabeled Markers,false",
                                "SetProperty,,Asset Markers,false",
                                "SetProperty,,Rigid Bodies,true"
                                "SetProperty,,Skeletons,false",
                                "SetProperty,,Trained Markerset Markers,false",
                                "SetProperty,,Trained Markerset Bones,false",
                                "SetProperty,,Devices,false",
                                "SetProperty,,Skeleton Coordinates,Global",
                                "SetProperty,,Bone Naming Convention,FBX",
                                "SetProperty,,Up Axis,Z-Axis"]
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
                # Update start state
                context.window_manager.start_status = True

    def get_rigid_body_dict(self, context): # array of all rigid bodies in the .tak
        self.rigid_bodies_motive = self.streaming_client.desc_dict
    
    def request_data_descriptions(self, s_client, context):
        # Request the model definitions
        return_code = s_client.send_modeldef_command()
    
    # This is a callback function that gets connected to the NatNet client. It is called once per rigid body per frame
    def receive_rigid_body_frame(self, new_id, position, rotation):
        if new_id in self.rigid_bodies_blender:
            values = (new_id, position, rotation)
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
                    my_obj = self.rigid_bodies_blender[q_val[0]] # new_id
                    my_obj.location = q_val[1]
                    my_obj.rotation_mode = 'QUATERNION'
                    my_obj.rotation_quaternion = q_val[2]
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

    connection_setup = None
    if connection_setup is None:
        connection_setup = ConnectionSetup()

    def execute(self, context):
        conn = self.connection_setup
        conn.connect_button_clicked(context)
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
    bl_label = "Awaiting"

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