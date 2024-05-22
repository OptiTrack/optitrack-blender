import bpy
import sys
import threading
from queue import Queue
from Modified_NatNetClient import NatNetClient

# Define a custom property to track connection state
bpy.types.WindowManager.connection_status = bpy.props.BoolProperty(name="Connection Status", default=False)

# class Status(bpy.types.Operator):
#     bl_idname = "status.operator"
#     bl_label = "status"

#     def execute(self, context):
#         # Retrieve the status property from the scene
#         status = context.scene.get("status", False)
#         return {'FINISHED'}

    # def execute(self, context):
    #     # Toggle the status property
    #     status = context.scene.get("status", False)
    #     context.scene["status"] = not status
            
    #     # Access connection_status
    #     if context.scene["status"]:
    #         self.report({'INFO'}, "Connection is active")
    #     else:
    #         self.report({'INFO'}, "Connection is inactive")
    #     return {'FINISHED'}

class ConnectionSetup:
    def __init__(self):
        self.streaming_client = None
        self.rigid_bodies = {} # all IDs getting stored
        self.q = Queue() # create queue object
        self.l = threading.Lock()
        self.is_running = None

    def connect_button_clicked(self, context): 
        # Initialize streaming client       
        if self.streaming_client is None:
            optionsDict = {'clientAddress': '127.0.0.1', 'serverAddress': '127.0.0.1', 'use_multicast': True}
            self.streaming_client = NatNetClient()
            self.streaming_client.set_client_address(optionsDict["clientAddress"])
            self.streaming_client.set_server_address(optionsDict["serverAddress"])
            self.streaming_client.set_use_multicast(optionsDict["use_multicast"])

            self.streaming_client.rigid_body_listener = self.receive_rigid_body_frame

            self.is_running = self.streaming_client.run()
            
            if self.is_running:
                # Update connection status
                context.window_manager.connection_status = True

                # # Timer to periodically update the object's location
                # def update_location_timer():
                #     self.update_object_loc()
                #     return 0.1  # Interval in seconds
                # bpy.app.timers.register(update_location_timer)
                # bpy.app.timers.register(self.update_object_loc, first_interval=0.1)
                # Status.status = True
            else:
                context.window_manager.connection_status = False
                # Status.status = False 
                try:
                    sys.exit(1)
                except SystemExit:
                    print("...")
                finally:
                    print("exiting")

    # This is a callback function that gets connected to the NatNet client. It is called once per rigid body per frame
    def receive_rigid_body_frame(self, new_id, position, rotation):
        if new_id not in self.rigid_bodies:
            # deselect all the objects
            bpy.ops.object.select_all(action='DESELECT')
            # create a cube
            bpy.ops.mesh.primitive_cube_add(size=1, enter_editmode=False, align='WORLD', location=position)
            my_obj = bpy.data.objects["Cube"] 
            bpy.context.view_layer.objects.active = my_obj
            my_obj.select_set(True)
            my_obj.name = "my_obj_%1.1d"%new_id
            my_obj.rotation_mode = 'QUATERNION'
            my_obj.rotation_quaternion = rotation
            self.rigid_bodies[new_id] = my_obj
            # print("Created object for rigid body", new_id)
        else:
            values = (new_id, position, rotation)
            self.l.acquire()
            try:
                self.q.put(values)
            # print("q size after value inserted: ",self.q.qsize())
            finally:
                self.l.release()
                # self.update_object_loc()
                bpy.app.timers.register(self.update_object_loc, first_interval=0.1)

    def update_object_loc(self):
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

    def disconnect_button_clicked(self, context):        
        if self.streaming_client:
            # Status.status = False
            self.streaming_client.shutdown()
            self.streaming_client = None
            context.window_manager.connection_status = False

class ConnectButtonOperator(bpy.types.Operator):
    bl_idname = "wm.connect_button"
    bl_label = "Start"

    connection_setup = None
    if connection_setup is None:
        connection_setup = ConnectionSetup()
    def execute(self, context):
        self.connection_setup.connect_button_clicked(context)
        return {'FINISHED'}
    
    # def invoke(self, context, event):
    #     context.window_manager.modal_handler_add(self)
    #     return {'RUNNING_MODAL'}

    # def modal(self, context, event):
    #     ConnectionSetup().connect_button_clicked(context)
    #     return {'PASS_THROUGH'}

class DisconnectButtonOperator(bpy.types.Operator):
    bl_idname = "wm.disconnect_button"
    bl_label = "Stop"
    
    def execute(self, context):
        # print("disconnected ", ConnectButtonOperator.connection_setup)
        if hasattr(ConnectButtonOperator, 'connection_setup') and ConnectButtonOperator.connection_setup is not None:
            ConnectButtonOperator.connection_setup.disconnect_button_clicked(context)
        return {'FINISHED'}

# def execute_queued_function():
#     while not exec_q.empty():
#         func = exec_q.get()
#         func()
#     return 0.083

# bpy.app.timers.register(execute_queued_function)