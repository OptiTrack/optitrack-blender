import bpy
import ipaddress
from bpy.types import Operator
import sys
import os
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
        self.assets_motive = {} # ( {assetType: {motive_ID: motive_name}} )
        self.assets_blender = {} # ( {assetType: {motive_ID: blender_ID}} )
        self.rev_assets_blender = {} # ( {blender_ID: {object, motive_ID, assetType}} )
        self.q = Queue()
        self.l = Lock()
        self.is_running = None
        self.frame_start = 0
        self.live_record = False

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
                sz_commands = [ "SetProperty,,Labeled Markers,false",
                                "SetProperty,,Unlabeled Markers,false",
                                "SetProperty,,Asset Markers,false",
                                "SetProperty,,Rigid Bodies,true",
                                "SetProperty,,Skeletons,true",
                                "SetProperty,,Trained Markerset Markers,false",
                                "SetProperty,,Trained Markerset Bones,false",
                                "SetProperty,,Devices,false",
                                "SetProperty,,Skeleton Coordinates,Global",
                                # "SetProperty,,Skeleton Coordinates,Local",
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
                self.streaming_client.data_listener = self.receive_data_frame
                
                # Update start state
                context.window_manager.start_status = True

    def get_desc_dict(self, context): # array of all rigid bodies in the .tak
        if self.streaming_client.desc_dict != self.assets_motive:
            for k, v in self.rev_assets_blender.items():
                v['m_ID'] = "None"
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
        ori = list(ori) # comment out later
        ori.append(ori.pop(0))
        return ori
    
    def sign(self, num):
        return int(num/abs(num)) if num != 0 else 0
    
    def quat_to_euler(self, ori):
        ori = mathutils.Quaternion(ori)
        ori = ori.to_matrix()
        eul = ori.to_euler('ZYX')
        return eul
    
    # def quat_modification(self, q): # only resolves lower body
    #     q_new = [0, 0, 0, 0]
    #     q_new[0] = -q[2]
    #     q_new[1] = q[3]
    #     q_new[2] = q[1]
    #     q_new[3] = q[0]
    #     return q_new

    def receive_data_frame(self, data_dict):
        self.indicate_model_changed = data_dict[ 'tracked_models_changed' ]
        self.indicate_motive_edit = data_dict[ 'edit_mode' ]
        frame_num = data_dict[ 'frame_number' ]

        values = []

        for key1 in data_dict[ 'rb_data' ]:
            if ('rigid_body' in self.assets_blender) and (key1 in self.assets_blender['rigid_body']):
                m_val = data_dict['rb_data'][key1] # rb.m_id = key1
                b_id = self.assets_blender['rigid_body'][key1]['b_ID']
                
                # Z-Up with quats
                pos1 = self.quat_loc_yup_zup(m_val['pos'])
                rot1 = self.quat_rot_yup_zup(m_val['rot'])
            
                # (x, y, z, w) -> (w, x, y, z)
                rot1 = self.sca_first_last(rot1)

                # sequence -> (assetID, pos, rot, frame_num, assetType, ske_rb)
                value = (b_id, pos1, rot1, frame_num, 'rigid_body', None)
                values.append(value)

        for key2 in data_dict[ 'ske_data' ]:
            if ('skeleton' in self.assets_blender) and (key2 in self.assets_blender['skeleton']):
                # m_ske_id = key2
                asset_type = 'skeleton'
                b_id = self.assets_blender['skeleton'][key2]['b_ID']
                m_ske_val = data_dict['ske_data'][key2] # ske.m_id = key2
                for k2, v2 in m_ske_val.items():
                    bone = self.assets_blender['skeleton'][key2]['ske_rb_map']['m_to_b'][k2]

                    # Z-Up with quats
                    pos2 = v2['pos']
                    rot2 = v2['rot']
                    # pos2 = self.quat_loc_yup_zup(v2['pos']) # pos_modification)
                    # rot2 = self.quat_rot_yup_zup(v2['rot'])
                
                    # (x, y, z, w) -> (w, x, y, z)
                    rot2 = self.sca_first_last(rot2)
                    # rot2 = self.quat_modification(rot2) # added

                    # sequence -> (assetID, pos, rot, frame_num, assetType, ske_rb)
                    value = (b_id, pos2, rot2, frame_num, 'skeleton', bone)
                    values.append(value)

            self.l.acquire()
            try:
                self.q.put(values)
            finally:
                self.l.release()
                bpy.app.timers.register(self.update_object_loc, first_interval=1/120) # freq = 120 Hz
        
        else:
            pass
                        
    def update_object_loc(self):
        if self.assets_blender:
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
                                    current_frame = (q_val[3] - self.frame_start)
                                    print("current_frame: ", current_frame)
                                    bpy.context.scene.frame_set(current_frame)
                                    # q_val[5] -> assetType, q_val[0] -> rbID
                                    if q_val[4] == 'rigid_body':
                                        my_obj = self.rev_assets_blender[q_val[0]]['obj']
                                    elif q_val[4] == 'skeleton':
                                        armature = self.rev_assets_blender[q_val[0]]['obj']
                                        my_obj = armature.pose.bones[q_val[5]]
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
                                        # my_obj = self.rev_assets_blender[self.assets_blender[q_val[0]]]['obj']
                                        if q_val[4] == 'rigid_body':
                                            my_obj = self.rev_assets_blender[q_val[0]]['obj']
                                        elif q_val[4] == 'skeleton':
                                            armature = self.rev_assets_blender[q_val[0]]['obj']
                                            my_obj = armature.pose.bones[q_val[5]]
                                        my_obj.location = q_val[1]
                                        my_obj.keyframe_insert(data_path="location", frame=current_frame)
                                        my_obj.rotation_mode = 'QUATERNION'
                                        my_obj.rotation_quaternion = q_val[2]
                                        my_obj.keyframe_insert(data_path="rotation_quaternion",frame=current_frame)

                                # no recording
                                else:
                                    # my_obj = self.rev_assets_blender[self.assets_blender[q_val[0]]]['obj']
                                    if q_val[4] == 'rigid_body':
                                        my_obj = self.rev_assets_blender[q_val[0]]['obj']
                                    elif q_val[4] == 'skeleton':
                                        armature = self.rev_assets_blender[q_val[0]]['obj']
                                        my_obj = armature.pose.bones[q_val[5]]
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
                                    # my_obj = self.rev_assets_blender[self.assets_blender[q_val[0]]]['obj'] # new_id
                                    if q_val[4] == 'rigid_body':
                                        my_obj = self.rev_assets_blender[q_val[0]]['obj']
                                        my_obj.location = q_val[1]
                                        my_obj.keyframe_insert(data_path="location", frame=q_val[3])
                                        my_obj.rotation_mode = 'QUATERNION'
                                        my_obj.rotation_quaternion = q_val[2]
                                        my_obj.keyframe_insert(data_path="rotation_quaternion",frame=q_val[3])
                                    elif q_val[4] == 'skeleton':
                                        armature = self.rev_assets_blender[q_val[0]]['obj']
                                        for bone in armature.pose.bones[:]:
                                            print(bone.name)
                                            bone.location = q_val[1]
                                            bone.keyframe_insert(data_path="location", frame=q_val[3])
                                            bone.rotation_mode = 'QUATERNION'
                                            bone.rotation_quaternion = q_val[2]
                                            bone.keyframe_insert(data_path="rotation_quaternion",frame=q_val[3])
                                        # my_obj = armature.pose.bones[q_val[5]]
                                        # print(armature.worldPosition)
                                        # bpy.ops.object.mode_set(mode='POSE')
                                        # my_obj.pose_head = q_val[1] - armature.worldPosition
                                        # my_obj.location = armature.matrix_world.inverted() @ mathutils.Vector(q_val[1])
                                        
                                    
                                    # if q_val[4] == 'rigid_body':
                                    #     my_obj = self.rev_assets_blender[q_val[0]]['obj']
                                    # elif q_val[4] == 'skeleton':
                                    #     armature = self.rev_assets_blender[q_val[0]]['obj']
                                    #     my_obj = armature.pose.bones[q_val[5]]
                                    # my_obj.location = q_val[1]
                                    # my_obj.keyframe_insert(data_path="location", frame=q_val[3])
                                    # my_obj.rotation_mode = 'QUATERNION'
                                    # my_obj.rotation_quaternion = q_val[2]
                                    # my_obj.keyframe_insert(data_path="rotation_quaternion",frame=q_val[3])

                                # selective keyframes
                                elif bpy.context.window_manager.record1_status == True:
                                    bpy.context.window_manager.record2_status = False
                                    if bpy.context.scene.frame_start <= q_val[3] <= bpy.context.scene.frame_end:
                                        bpy.context.scene.frame_set(q_val[3])
                                        # my_obj = self.rev_assets_blender[self.assets_blender[q_val[0]]]['obj']
                                        if q_val[4] == 'rigid_body':
                                            my_obj = self.rev_assets_blender[q_val[0]]['obj']
                                        elif q_val[4] == 'skeleton':
                                            armature = self.rev_assets_blender[q_val[0]]['obj']
                                            my_obj = armature.pose.bones[q_val[5]]
                                        my_obj.location = q_val[1]
                                        my_obj.keyframe_insert(data_path="location", frame=q_val[3])
                                        my_obj.rotation_mode = 'QUATERNION'
                                        my_obj.rotation_quaternion = q_val[2]
                                        my_obj.keyframe_insert(data_path="rotation_quaternion",frame=q_val[3])

                                # no recording
                                else:
                                    if q_val[4] == 'rigid_body':
                                        my_obj = self.rev_assets_blender[q_val[0]]['obj']
                                        my_obj.location = q_val[1]
                                        my_obj.rotation_mode = 'QUATERNION'
                                        my_obj.rotation_quaternion = q_val[2]
                                    elif q_val[4] == 'skeleton':
                                        armature = self.rev_assets_blender[q_val[0]]['obj']
                                        my_obj = armature.pose.bones[q_val[5]]
                                        # print(armature.worldPosition)
                                        # bpy.ops.object.mode_set(mode='POSE')
                                        my_obj.location = q_val[1]
                                        # my_obj.pose_head = q_val[1] - armature.worldPosition
                                        # my_obj.location = armature.matrix_world.inverted() @ mathutils.Vector(q_val[1])
                                        my_obj.rotation_mode = 'QUATERNION'
                                        my_obj.rotation_quaternion = q_val[2]
                                        # my_obj.rotation_quaternion = [1, 0, 0, 0]
                                        # my_obj.rotation_quaternion = armature.rotation_euler.to_quaternion() * mathutils.Quaternion(q_val[2]) 
                                        # creates more problem
                                    print("loc, rot: ", my_obj.name, " ", my_obj.location, " ", my_obj.rotation_quaternion)
                                    # print("matrix1: ", armature.matrix_world @ my_obj.tail)
                                    # print("getpose: ", my_obj.getPose())
                                    # print("matrix2: ", my_obj.getMatrix(space='worldspace'))

                        except KeyError:
                            # if object id updated in middle of the running .tak
                            pass
            finally:
                self.l.release()
        else:
            pass
    
    def stop_receive_rigid_body_frame(self, new_id, position, rotation, frame_number):
        pass

    def stop_receive_data_frame(self, data_dict):
        pass

    def pause_button_clicked(self, context): # Stop the data stream, but don't update the stored info        
        if self.streaming_client:
            self.streaming_client.data_listener = self.stop_receive_data_frame
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
                # conn.reset_to_initial()
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
            conn.streaming_client = None
            context.window_manager.connection_status = False
            if "'NoneType' object has no attribute 'sendto'" in str(e):
                self.report({'ERROR'}, f"Your Motive is not set to Multicast")
            else:
                self.report({'ERROR'}, f"Check Toggle System Console")
                print("error: ", e)
            return {'CANCELLED'}
    
        return {'FINISHED'}

class RefreshAssetsOperator(Operator):
    bl_idname = "wm.refresh_button"
    bl_description = "Refresh the asset list"
    bl_label = "Refresh Assets"

    def execute(self, context):
        existing_conn = ConnectOperator.connection_setup
        existing_conn.request_data_descriptions(existing_conn.streaming_client, context)
        if context.window_manager.start_status:
            existing_conn.pause_button_clicked(context)
        return {'FINISHED'}

class MotiveArmatureOperator(Operator):
    bl_idname = "wm.add_armature"
    bl_description = "Add Human Meta-Rig with Motive's Armature"
    bl_label = "Add Motive Armature"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        existing_conn = ConnectOperator.connection_setup
        # print("inside MotiveArmature: ", existing_conn.assets_motive)
        if existing_conn.assets_motive and existing_conn.assets_motive['ske_desc']:
            pass
        else:
            existing_conn.get_desc_dict(context)
        #     existing_conn.request_data_descriptions(existing_conn.streaming_client, context)
        

        for key, val in existing_conn.assets_motive['ske_desc'].items(): # assetType: m_ID: b_ID
            ## Method 1
            # add an armature
            bpy.ops.object.armature_add(location=(0, 0, 0), enter_editmode=False, \
                                        align='WORLD', scale=(1, 1, 1))
            armature_object = bpy.context.object
            # armature.bones[0].name = key
            armature_object.name = val['name']

            ## Method 2
            # # Create a new armature
            # armature = bpy.data.armatures.new("Root")
            # armature_object = bpy.data.objects.new(val['name'], armature)
            # # Link the armature object to the scene
            # bpy.context.collection.objects.link(armature_object) # this is where obj is introduced in \
            # # the scene collection list
            # # Set the armature as the active object
            # bpy.context.view_layer.objects.active = armature_object
            
            bpy.ops.object.mode_set(mode='EDIT')  # Switch to edit mode

            # for k, v in val['rb_desc'].items():
            #     parent_id = v['parent_id']
            #     parent_name = val['rb_desc'][parent_id]['name']
            #     child_id = val['parent_to_children'][parent_id][0]

            #     if parent_id != 0:

            ####### Method 2 (with children linked)
            for k, v in val['rb_name'].items():
                parent_id = v['parent_id']
                local_pos = v['pos']
                if parent_id != 0:
                    parent_name = val['rb_desc'][parent_id]['name']
                    parent_bone = armature_object.data.edit_bones.get(parent_name)
                else:
                    parent_bone = armature_object.data.edit_bones.get('Bone')
                    parent_bone.tail = local_pos
                bone = armature_object.data.edit_bones.new(k)
                bone.parent = parent_bone
                bone.head = parent_bone.tail # existing_conn.add_ls(list(parent_bone.head), local_pos)
                # print(bone.name + " " + str(list(parent_bone.head)) + " " + str(local_pos) + " " +\
                #       str(list(bone.head)))
                if val['parent_to_children'][parent_id]:
                    child_id = val['parent_to_children'][parent_id][0]
                    child_pos = val['rb_desc'][child_id]['pos']
                    bone.tail = existing_conn.add_ls(list(bone.head), child_pos)
                    # print(bone.name + " " + str(list(bone.head)) + " " + str(child_pos) + " " +\
                    #   str(list(bone.tail)))
                else:
                    direction = parent_bone.tail - parent_bone.head
                    if direction.length > 0:
                        direction.normalize()
                    bone.tail = bone.head + (0.2 * direction)
                # bone.use_connect = True
                print("bone head and tail: " + bone.name + " " + str(parent_bone.head) + \
                      " and " + str(parent_bone.tail))
            ###################################


            ##### Method 1
            # for k, v in val['rb_name'].items():
            #     parent_id = v['parent_id']
            #     # child_id = val['parent_to_children'][parent_id][0]
            #     # print(val['parent_to_children'][parent_id])
            #     if parent_id != 0:
            #         # parent_name = val['rb_desc'][parent_id]['name']
            #         # parent_bone = armature_object.data.edit_bones.get(parent_name)
            #         # bone = armature_object.data.edit_bones.new(k)
            #         # bone.parent = parent_bone
            #         # local_pos = v['pos']
            #         # bone.head = existing_conn.add_ls(list(parent_bone.head), local_pos)


            #         if k in ['LeftUpLeg', 'RightUpLeg']:
            #             parent_name = val['rb_desc'][parent_id]['name']
            #             parent_bone = armature_object.data.edit_bones.get(parent_name)
            #             bone = armature_object.data.edit_bones.new(k)
            #             bone.parent = parent_bone
            #             local_pos = v['pos']
            #             # local_pos = existing_conn.quat_loc_yup_zup(v['pos'])
            #             bone.head = existing_conn.add_ls(list(parent_bone.head), local_pos)
            #             bone.use_connect = False # cannot connect this, we need that gap

            #             # # Switch to Pose mode to add a constraint
            #             # bpy.ops.object.mode_set(mode='POSE')
                        
            #             # # Access the pose bone
            #             # pose_child_bone = armature_object.pose.bones[k]
                        
            #             # # Create a Copy Location constraint on the child bone to follow the parent bone
            #             # # constraint = pose_child_bone.constraints.new(type='COPY_LOCATION')
            #             # constraint = pose_child_bone.constraints.new(type='CHILD_OF')
            #             # constraint.target = armature_object
            #             # constraint.subtarget = parent_name
            #             # # constraint.use_offset = True  # Keep the offset so they aren't connected visually
            #             # bpy.ops.object.mode_set(mode='EDIT')
            #         else:
            #             parent_name = val['rb_desc'][parent_id]['name']
            #             # print(str(parent_id) + " " + parent_name)
            #             # parent_bone = armature_object.data.edit_bones[parent_name]
            #             parent_bone = armature_object.data.edit_bones.get(parent_name)
            #             local_pos = v['pos']
            #             # local_pos = existing_conn.quat_loc_yup_zup(v['pos'])
            #             parent_bone.tail = existing_conn.add_ls(list(parent_bone.head), local_pos)
                        
            #             bone = armature_object.data.edit_bones.new(k)
            #             bone.parent = parent_bone
            #             bone.head = parent_bone.tail
            #             bone.use_connect = True

            #             if k in ['Head', 'LeftHand', 'RightHand', 'LeftToeBase', 'RightToeBase']:
            #                 direction = parent_bone.tail - parent_bone.head
            #                 if direction.length > 0:
            #                     direction.normalize()
                            
            #                 bone.tail = bone.head + (0.1 * direction)

            #             # bone.use_local_location = True # don't know if it is doing anything
            #             # # local_pos = existing_conn.subtract_ls(v['pos'], val['rb_desc'][parent_id]['pos'])
            #             # # bone.parent.tail_local = local_pos
            #             # # bone.head_local = bone.parent.tail_local
            #             # print(k + " pos: " + str(bone.head) + " parent_id: " + str(parent_id) + \
            #             #         " parent_pos: " + str(bone.parent.head) + "bone length: " + str(bone.length))
            #             # --------------------------------
            #             # parent_head = parent_bone.head
            #             # direction = mathutils.Vector(local_pos - parent_head)
            #             # # Calculate roll based on parent position
            #             # parent_head = bone.parent.head
            #             # direction = mathutils.Vector(local_pos) - mathutils.Vector(parent_head)
            #             # direction.normalize()
                        
            #             # # Define a reference vector (usually along the Z axis)
            #             # ref_vector = mathutils.Vector((0, 1, 0))  # Adjust as needed for your setup
                        
            #             # # Calculate roll using the direction and reference
            #             # roll = direction.angle(ref_vector)
            #             # if direction.x < 0:
            #             #     roll = -roll
                        
            #             # # Set the roll value
            #             # bone.roll = roll
            #     else:
            #         bone = armature_object.data.edit_bones.new(k)
            #         parent_bone = armature_object.data.edit_bones.get('Bone')
            #         bone.use_local_location = True
            #         # bone.name = k
            #         local_pos = v['pos']
            #         parent_bone.tail = local_pos
            #         bone.parent = parent_bone
            #         # local_pos = existing_conn.quat_loc_yup_zup(v['pos'])
            #         bone.head = local_pos
            #         bone.use_connect = False
            #         # bone.head_local = local_pos  # + armature.worldPosition
            #         # print(k + " bone pos: " + str(bone.head) +" bone length: " + str(bone.length))
                
            #     print("bone head and tail: " + bone.name + " " + str(parent_bone.head) + " and " \
            #               + str(parent_bone.tail))
            
            # # # Bones don't show until you get out of EDIT mode
            # # bpy.ops.object.mode_set(mode='POSE')
            # # bones = ['LeftUpLeg', 'RightUpLeg']
            # # for bone_name in bones:
            # #     bone = armature_object.pose.bones.get(bone_name)
            # #     constraint = bone.constraints.new(type='COPY_LOCATION')
            # #     parent_bone = armature_object.pose.bones.get("Hips")
            # #     # Set the target object to the armature itself
            # #     constraint.target = armature_object
                
            # #     # Specify the bone to follow (the parent bone)
            # #     constraint.subtarget = "Hips"
                
            # #     # Disable the connection to the parent
            # #     constraint.use_offset = True

            # # # Ensure display settings for relationship lines
            # # armature_object.data.show_relationship_lines = True
            ##########################
            
            bpy.ops.object.mode_set(mode='OBJECT')
            # bpy.context.space_data.overlay.show_relationship_lines = True


            # for arm in bpy.data.armatures:
            #     print(str(arm) + " " + arm.name)
            # for bone in bpy.data.armatures["Root"].bones:
            #     if bone.parent is not None:
            #         bone.parent.tail_local = bone.head_local

    # curr_dir = os.path.dirname(os.path.abspath(__file__))
    # file_path = os.path.join(curr_dir, "MotiveSkeleton.fbx")
    # bpy.ops.import_scene.fbx(filepath=file_path)
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