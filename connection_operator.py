import bpy
from bpy.types import Operator
import sys
from threading import Lock
from queue import Queue
from .Modified_NatNetClient import NatNetClient
from .MoCapData import MoCapData

# Define a custom property to track connection state
bpy.types.WindowManager.connection_status = bpy.props.BoolProperty(name="Connection Status", default=False)
bpy.types.WindowManager.start_status = bpy.props.BoolProperty(name="Start Status", default=False)

class ConnectionSetup:
    def __init__(self):
        self.streaming_client = None
        self.indicate_model_changed = None
        self.rigid_body_ids = []
        self.rigid_bodies = {} # all objects getting stored ({ID: rigid_body} pair)
        self.rev_rigid_bodies = {} # ({rigid_body: ID} pair)
        self.q = Queue()
        self.l = Lock()
        self.is_running = None

    def reset_to_initial(self):
        self.streaming_client = None
        self.indicate_model_changed = None
        self.rigid_body_ids = []
        self.rigid_bodies = {}
        self.rev_rigid_bodies = {} 
        self.q = Queue()
        self.l = Lock()
        self.is_running = None

    def request_data_descriptions(s_client):
        # Request the model definitions
        s_client.send_request(s_client.command_socket, s_client.NAT_REQUEST_MODELDEF,    "",  (s_client.server_ip_address, s_client.command_port) )

    def connect_button_clicked(self, context): 
        # Initialize streaming client       
        if self.streaming_client is None:
            optionsDict = {'clientAddress': bpy.context.scene.init_prop.client_address, 'serverAddress': bpy.context.scene.init_prop.server_address, 'use_multicast': True}
            self.streaming_client = NatNetClient()
            self.streaming_client.set_client_address(optionsDict["clientAddress"])
            self.streaming_client.set_server_address(optionsDict["serverAddress"])
            self.streaming_client.set_use_multicast(optionsDict["use_multicast"])
            self.request_data_descriptions(self.streaming_client)
            
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
            self.is_running = self.streaming_client.run()
        
            if self.is_running:
                self.streaming_client.model_changed = self.signal_model_changed
                # self.rigid_body_ids = self.streaming_client.rigid_body_id_listener
                # print("rigid_body_id_listener: ", len(self.rigid_body_ids))
                self.streaming_client.rigid_body_listener = self.receive_rigid_body_frame

                # Update start state
                context.window_manager.start_status = True


    def get_rigid_body_ids(self, context): # array of all rigid bodies in the .tak
        return self.rigid_body_ids

    def assign_objs(self, context): # Assign objects in scene to rigid body IDs
        self.l.acquire()
        try:
            for obj in bpy.data.objects:
                obj_name = obj.name
                last_underscore = obj_name.rfind('_')
                if last_underscore != -1:
                    obj_id = obj_name[last_underscore + 1:]
                    obj_id = int(obj_id)
                    self.rigid_bodies[obj_id] = obj
                    self.rev_rigid_bodies[obj] = obj_id  
                else:
                    obj_id = None

        finally:
            self.l.release()        

    def signal_model_changed(self, tracked_model_changed):
        self.indicate_model_changed = tracked_model_changed
    
    # This is a callback function that gets connected to the NatNet client. It is called once per rigid body per frame
    def receive_rigid_body_frame(self, new_id, position, rotation):
        print("recive_rigid_bodies: ", len(self.rigid_bodies))
        print("recive_rigid_body_ids: ", len(self.rigid_body_ids))

        # if len(self.rigid_bodies) > len(self.rigid_body_ids):
        #         try:
        #             self.l.acquire()
        #             for key, val in self.rigid_bodies.items():
        #                 if key not in self.rigid_body_ids:
        #                     del self.rev_rigid_bodies[self.rigid_bodies[key]]
        #                     del self.rigid_bodies[key]
        #         finally:
        #             self.l.release()

        if new_id not in self.rigid_body_ids:
            self.rigid_body_ids.append(new_id)

        # Two cases (Assign vs Create)
        if new_id not in self.rigid_bodies:
            bpy.ops.object.select_all(action='DESELECT')
            
            # creating objects
            if bpy.context.scene.init_prop.desired_object == 'Cube':
                # create a cube
                bpy.ops.mesh.primitive_cube_add(size=0.75, enter_editmode=False, align='WORLD', location=position)
            
            if bpy.context.scene.init_prop.desired_object == 'UV Sphere':
                # create a UV sphere
                bpy.ops.mesh.primitive_uv_sphere_add(radius=0.75/2, enter_editmode=False, align='WORLD', location=position)
            
            if bpy.context.scene.init_prop.desired_object == 'Ico Sphere':
                # create an Icosphere
                bpy.ops.mesh.primitive_ico_sphere_add(radius=0.75/2, enter_editmode=False, align='WORLD', location=position)
            
            if bpy.context.scene.init_prop.desired_object == 'Cylinder':
                # create a cylinder
                bpy.ops.mesh.primitive_cylinder_add(radius=0.75/2, depth=0.75, enter_editmode=False, align='WORLD', location=position)
            
            if bpy.context.scene.init_prop.desired_object == 'Cone':
                # create a cone
                bpy.ops.mesh.primitive_cone_add(radius1=0.75/2, radius2=0.0, depth=0.75, enter_editmode=False, align='WORLD', location=position)
            
            my_obj = bpy.context.view_layer.objects.active
            my_obj.select_set(True)
            my_obj.name = "my_obj_%1.1d"%new_id
            my_obj.rotation_mode = 'QUATERNION'
            my_obj.rotation_quaternion = rotation
            self.rigid_bodies[new_id] = my_obj
            self.rev_rigid_bodies[my_obj] = new_id

        else:
            values = (new_id, position, rotation)
            self.l.acquire()
            try:
                self.q.put(values)
            finally:
                self.l.release()
                bpy.app.timers.register(self.update_object_loc, first_interval=1/120) # freq = 120 Hz

    def update_object_loc(self):
        if self.rigid_bodies:
            self.l.acquire()
            try:
                if not self.q.empty(): 
                    q_val = self.q.get()
                    my_obj = self.rigid_bodies[q_val[0]] # new_id
                    my_obj.location = q_val[1]
                    my_obj.rotation_mode = 'QUATERNION'
                    my_obj.rotation_quaternion = q_val[2]
            finally:
                self.l.release()
        else:
            pass

    def pause_button_clicked(self, context): # Stop the data stream, but don't update the stored info        
        if self.streaming_client:
            self.streaming_client.shutdown()
            self.streaming_client = None
            context.window_manager.start_status = False

class ConnectButtonOperator(Operator):
    bl_idname = "wm.connect_button"
    bl_description = "Start the connection"
    bl_label = "Connect"

    connection_setup = None
    if connection_setup is None:
        connection_setup = ConnectionSetup()

    def execute(self, context):
        self.connection_setup.connect_button_clicked(context)
        from .app_handlers import reset_to_default
        reset_to_default(context.scene)
        if context.window_manager.connection_status:
            conn = self.connection_setup
            conn.assign_objs(context)
        return {'FINISHED'}

class StartButtonOperator(Operator):
    bl_idname = "wm.start_button"
    bl_description = "Start receiving the data for every frame"
    bl_label = "Start Data"

    def execute(self, context):
        ConnectButtonOperator.connection_setup.start_button_clicked(context)
        return {'FINISHED'}

class GetRigidBodiesIDsOperator(Operator):
    bl_idname = "wm.get_ids"
    bl_description = "Get the IDs of all the objects present in the frame"
    bl_label = "Get IDs"
    
    def execute(self, context):
        id_ls = []
        if context.window_manager.connection_status:
            if id_ls:
                id_ls = []
            id_ls = ConnectButtonOperator.connection_setup.get_rigid_body_ids(context)
            context.scene['id_ls'] = id_ls
        return {'FINISHED'}

class AssignAgainOperator(Operator):
    bl_idname = "wm.assign_again"
    bl_label = "Assign IDs again"

    def execute(self, context):
        ConnectButtonOperator.connection_setup.assign_objs(context)
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
    bl_label = "Reset"

    def execute(self, context):
        if ConnectButtonOperator.connection_setup is not None:
            existing_connection = ConnectButtonOperator.connection_setup
            existing_connection.pause_button_clicked(context)
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