#-----------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------
# # Description - (assets_motive)
# desc_dict['rb_desc'][rb.m_id]['name'] = rb.m_name

# desc_dict['ske_desc'][ske.m_id]['name'] = ske.m_name
# desc_dict['ske_desc'][ske.m_id]['rb_id'][rb.m_id]['name'] = rb.m_name
# desc_dict['ske_desc'][ske.m_id]['rb_id'][rb.m_id]['pos'] = rb.pos
# desc_dict['ske_desc'][ske.m_id]['rb_id'][rb.m_id]['parent_id'] = rb.parent_id
# desc_dict['ske_desc'][ske.m_id]['rb_name'][rb.m_name]['id'] = rb.m_id
# desc_dict['ske_desc'][ske.m_id]['rb_name'][rb.m_name]['pos'] = rb.pos
# desc_dict['ske_desc'][ske.m_id]['rb_name'][rb.m_name]['parent_id'] = rb.parent_id
# desc_dict['ske_desc'][ske.m_id]['rb_name'][rb.m_name]['global_pos'] = rb.global_tpose
# desc_dict['ske_desc'][ske.m_id]['rb_name'][rb.m_name]['children'] = rb.children
# desc_dict['ske_desc'][ske.m_id]['rb_name'][rb.m_name]['global_tpose_rot'] = rb.global_rot_tpose
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
# # MoCapData -
# data_dict['rb_data'][rb.m_id]['pos'] = pos
# data_dict['rb_data'][rb.m_id]['rot'] = rot

# data_dict['ske_data'][ske.m_id][rb.m_id]['pos'] = pos
# data_dict['ske_data'][ske.m_id][rb.m_id]['rot'] = rot
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
# # assets_blender -
# assets_blender['rigid_body'][rb.m_id]['b_ID'] = b_id

# assets_blender['skeleton'][ske.m_id]['b_ID'] = b_id
# assets_blender['skeleton'][ske.m_id]['ske_rb_map']['m_to_b'][rb.m_id] = b_obj
# assets_blender['skeleton'][ske.m_id]['ske_rb_map']['b_to_m'][b_obj] = rb.m_id
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
# # rev_assets_blender -
# rev_assets_blender[b_id]['m_id'] = m_id
# rev_assets_blender[b_id]['obj'] = b_obj
# rev_assets_blender[b_id]['asset_type'] = 'rigid_body' / 'skeleton'
#------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------------------------

import bpy
from bpy.types import Operator
from .plugin_operators import ConnectOperator
import math

class MotiveArmatureOperator(Operator):
    bl_idname = "wm.add_armature"
    bl_description = "Add Human Meta-Rig with Motive's Skeleton Data"
    bl_label = "Add Motive Armature"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        existing_conn = ConnectOperator.connection_setup
        if existing_conn.assets_motive and existing_conn.assets_motive['ske_desc']:
            pass
        else:
            existing_conn.get_desc_dict(context)
        
        dt = existing_conn.assets_motive['ske_desc']

        create_armature = CreateArmature(dt)
        create_armature.update_dict()
        
        for key, val in dt.items():
            bone_conv = create_armature.find_bone_convention(key)
            # Create a new armature
            armature = bpy.data.armatures.new("Root")
            armature_object = bpy.data.objects.new(val['name'], armature)
            # Link the armature object to the scene
            bpy.context.collection.objects.link(armature_object) # this is where obj is introduced in \
            # the scene collection list
            # Set the armature as the active object
            bpy.context.view_layer.objects.active = armature_object
            
            bpy.ops.object.mode_set(mode='EDIT')  # Switch to edit mode

            arm_dict = create_armature.adding_armature_entry(key, bone_conv)

            for k, v in arm_dict.items():
                bone = armature_object.data.edit_bones.new(k)
                if v[0] != None:
                    bone.parent = armature_object.data.edit_bones.get(v[0])
                bone.head = v[1]
                # bone.head = existing_conn.quat_loc_yup_zup(v[1])
                bone.tail = v[2]
                # bone.tail = existing_conn.quat_loc_yup_zup(v[2])
                val['rb_name'][k]['global_tpose_rot'] = math.radians(v[3])
                bone.roll = math.radians(v[3])
                # bone.use_connect = True
                if v[4] == True:
                    bone.use_connect = True
                # else:
                #     bone.use_offset = True
                #     bpy.ops.object.mode_set(mode='POSE')
                #     # Select the child bone to apply constraints
                #     child_bone_pose = armature_object.pose.bones[k]
                #     # Create a Child Of constraint
                #     constraint = child_bone_pose.constraints.new(type='CHILD_OF')
                #     constraint.target = armature_object  # Replace with your target object
                #     constraint.subtarget = bone.parent.name

                #     # Enable Keep Offset
                #     constraint.use_offset = True
                #     bpy.ops.object.mode_set(mode='EDIT')
            
                # print("bone: " + bone.name + " parent: " + str(v[0]) + " head: " + str(bone.head) + \
                #     " tail: " + str(bone.tail) + " roll: " + str(math.degrees(bone.roll)))
                bone_pos = bone.matrix.decompose()[0]
                # print("bone: " + bone.name + " bone pos: " + str(bone_pos))

            bpy.ops.object.mode_set(mode='OBJECT') # Switch back to object mode
        
        # bpy.ops.object.mode_set(mode='POSE')
        # pose_data = {}
        # for bone in armature.pose.bones:
        #     pose_data[bone.name] = {"location": bone.location.copy(), 
        #                             "rotation": bone.rotation_quaternion.copy(),
        #                             "scale": bone.scale.copy()}
        # bpy.ops.object.mode_set(mode='OBJECT')
        
        return {'FINISHED'}

class CreateArmature:
    def __init__(self, dt):
        self.dt = dt # desc_dict['ske_desc']
        # self.armature_description = {}
        self.conventions = {
            'Motive'        : ['Hip', 'Ab', 'Chest', 'Neck', 'Head', 'LShoulder', 'LUArm', 'LFArm', \
                               'LHand', 'RShoulder', 'RUArm', 'RFArm', 'RHand', 'LThigh', 'LShin', \
                                'LFoot', 'LToe', 'RThigh', 'RShin', 'RFoot', 'RToe'],
            'FBX'           : ['Hips', 'Spine', 'Spine1', 'Neck', 'Head', 'LeftShoulder', 'LeftArm', \
                                'LeftForeArm', 'LeftHand', 'RightShoulder', 'RightArm', 'RightForeArm', \
                                'RightHand', 'LeftUpLeg', 'LeftLeg', 'LeftFoot', 'LeftToeBase', \
                                'RightUpLeg', 'RightLeg', 'RightFoot', 'RightToeBase'],
            'UnrealEngine'  : ['pelvis', 'spine_01', 'spine_02', 'neck_01', 'head', 'clavicle_l', \
                                'upperarm_l', 'lowerarm_l', 'hand_l', 'clavicle_r', 'upperarm_r', \
                                'lowerarm_r', 'hand_r', 'thigh_l', 'calf_l', 'foot_l', 'ball_l', \
                                'thigh_r', 'calf_r', 'foot_l', 'ball_r']
                            }
        
    def find_bone_convention(self, key):
        if 'Hip' in self.dt[key]['rb_name']:
            return 'Motive'
        elif 'Hips' in self.dt[key]['rb_name']:
            return 'FBX'
        elif 'pelvis' in self.dt[key]['rb_name']:
            return 'UnrealEngine'
        else:
            return None

    def get_global_pos(self, item, dt): # dt = desc_dict['ske_desc'][skeleton_id]['rb_name']
        total_pos = [0, 0, 0]
        current_bone = item

        while current_bone is not None:
            # Add local position of the current item to the total
            current_bone_pos = dt[current_bone]['pos']
            total_pos[0] += current_bone_pos[0]
            total_pos[1] += current_bone_pos[1]
            total_pos[2] += current_bone_pos[2]
            # Move to the parent
            current_bone = dt[current_bone]['parent_name']
        
        return total_pos
    
    def update_dict(self): # dt = desc_dict['ske_desc']
        for key, val in self.dt.items():
            self.dt[key]['parent_to_children'] = {}
            for k, v in val['rb_name'].items():
                parent_id = v['parent_id']
                if parent_id != 0:
                    parent_name = val['rb_id'][parent_id]['name']
                    val['rb_name'][k]['parent_name'] = parent_name
                    if parent_name not in self.dt[key]['parent_to_children']:
                        self.dt[key]['parent_to_children'][parent_name] = []
                    self.dt[key]['parent_to_children'][parent_name].append(k)
                else:
                    val['rb_name'][k]['parent_name'] = None
        
        for key, val in self.dt.items():
            for k, v in val['rb_name'].items():
                if v['parent_name'] != None:
                    v['global_pos'] = self.get_global_pos(k, self.dt[key]['rb_name'])
                else:
                    v['global_pos'] = v['pos']
                
                v['children'] = []
                if k in self.dt[key]['parent_to_children']:
                    v['children'] = self.dt[key]['parent_to_children'][k]
                # print("desc dict: ", k, " global pos: ", str(round(v['global_pos'][0], 4)), ", ",\
                #       str(round(v['global_pos'][1], 4)), ", ", str(round(v['global_pos'][2], 4)))
        return self.dt

    def get_parent(self, id, bone_name):
        return self.dt[id]['rb_name'][bone_name]['parent_name']
    
    def get_head(self, id, bone_name):
        return self.dt[id]['rb_name'][bone_name]['global_pos']
    
    def get_tail(self, id, bone_name):
        child_name = self.dt[id]['rb_name'][bone_name]['children'][0]
        return self.dt[id]['rb_name'][child_name]['global_pos']
    
    def create_tail(self, id, bone_name):
        parent_name = self.dt[id]['rb_name'][bone_name]['parent_name']
        parent_pos = self.dt[id]['rb_name'][parent_name]['global_pos']
        bone_pos = self.dt[id]['rb_name'][bone_name]['global_pos']
        direction = list(map(lambda x, y: x - y, bone_pos, parent_pos))
        dir_len = math.sqrt(direction[0]**2 + direction[1]**2 + direction[2]**2)
        if dir_len > 0:
            dir_normalized = list(map(lambda x : x/dir_len, direction))
            end_loc = list(map(lambda x, y : x + 0.1 * y, bone_pos, dir_normalized)) 
            # bone_pos + (0.1 * dir_normalized)
        else:
            end_loc = bone_pos
        return end_loc
    
    def adding_armature_entry(self, id, bone_conv): # dt = desc_dict['ske_desc'][skeleton_id]['rb_name']
        ls = self.conventions[bone_conv]
        new_entry = {
            ## bone : [parent, head, tail, roll, connect]
            ls[0] : [self.get_parent(id, ls[0]), self.get_head(id, ls[0]), self.get_tail(id, ls[0]), 0, True],
            ls[1] : [self.get_parent(id, ls[1]), self.get_head(id, ls[1]), self.get_tail(id, ls[1]), 0, True],
            ls[2] : [self.get_parent(id, ls[2]), self.get_head(id, ls[2]), self.get_tail(id, ls[2]), 0, True],
            ls[3] : [self.get_parent(id, ls[3]), self.get_head(id, ls[3]), self.get_tail(id, ls[3]), 0, True],
            ls[4] : [self.get_parent(id, ls[4]), self.get_head(id, ls[4]), self.create_tail(id, ls[4]), 0, True],
            ls[5] : [self.get_parent(id, ls[5]), self.get_head(id, ls[5]), self.get_tail(id, ls[5]), 180, False],
            ls[6] : [self.get_parent(id, ls[6]), self.get_head(id, ls[6]), self.get_tail(id, ls[6]), 180, True],
            ls[7] : [self.get_parent(id, ls[7]), self.get_head(id, ls[7]), self.get_tail(id, ls[7]), 180, True],
            ls[8] : [self.get_parent(id, ls[8]), self.get_head(id, ls[8]), self.create_tail(id, ls[8]), 180, True],
            ls[9] : [self.get_parent(id, ls[9]), self.get_head(id, ls[9]), self.get_tail(id, ls[9]), 0, False],
            ls[10] : [self.get_parent(id, ls[10]), self.get_head(id, ls[10]), self.get_tail(id, ls[10]), 0, True],
            ls[11] : [self.get_parent(id, ls[11]), self.get_head(id, ls[11]), self.get_tail(id, ls[11]), 0, True],
            ls[12] : [self.get_parent(id, ls[12]), self.get_head(id, ls[12]), self.create_tail(id, ls[12]), 0, True],
            ls[13] : [self.get_parent(id, ls[13]), self.get_head(id, ls[13]), self.get_tail(id, ls[13]), 180, False],
            ls[14] : [self.get_parent(id, ls[14]), self.get_head(id, ls[14]), self.get_tail(id, ls[14]), 180, True],
            ls[15] : [self.get_parent(id, ls[15]), self.get_head(id, ls[15]), self.get_tail(id, ls[15]), 0, True],
            ls[16] : [self.get_parent(id, ls[16]), self.get_head(id, ls[16]), self.create_tail(id, ls[16]), 0, True],
            ls[17] : [self.get_parent(id, ls[17]), self.get_head(id, ls[17]), self.get_tail(id, ls[17]), 180, False],
            ls[18] : [self.get_parent(id, ls[18]), self.get_head(id, ls[18]), self.get_tail(id, ls[18]), 180, True],
            ls[19] : [self.get_parent(id, ls[19]), self.get_head(id, ls[19]), self.get_tail(id, ls[19]), 0, True],
            ls[20] : [self.get_parent(id, ls[20]), self.get_head(id, ls[20]), self.create_tail(id, ls[20]), 0, True],
        }
        return new_entry
    
    # def creating_blender_bones(self, dt, arm_obj, existing_conn): # dt = my_dict
        


#-----------------------------------------------------------------------------------------------------------
# # create lookup in blender armature data for bone names
# motive_skeleton_hierarchy = ['Hips', 'Spine', 'Spine1', 'Neck', 'Head', 'LeftShoulder', 'LeftArm', \
#                    'LeftForeArm', 'LeftHand', 'RightShoulder', 'RightArm', 'RightForeArm', \
#                    'RightHand', 'LeftUpLeg', 'LeftLeg', 'LeftFoot', 'LeftToeBase', \
#                     'RightUpLeg', 'RightLeg', 'RightFoot', 'RightToeBase']
#-----------------------------------------------------------------------------------------------------------

# # request data descriptions

#-----------------------------------------------------------------------------------------------------------
#### script to print armature data
# import bpy
# from math import degrees

# bpy.ops.object.mode_set(mode='EDIT')

# armature1 = bpy.data.objects['Root']

# #armature2 = bpy.data.objects['Anthony']

# armature2 = bpy.data.objects['Anthony']

# #print("---------------------------------------------------")
# #print("Armature: " + armature1.name)
# #for bone in armature1.data.edit_bones:
# #    print(bone.name + " head: " + str(bone.head.x) + " " + str(bone.head.y) + " " + str(bone.head.z) + \
# " tail: " + str(bone.tail.x) + " " + str(bone.tail.y) + " " + str(bone.tail.z) + " roll (in degrees): " \
# + str(degrees(bone.roll)) )
# #    print("---------------------------------------------------")

# print("---------------------------------------------------")
# print("Armature: " + armature2.name)
# print(armature2.data.edit_bones)
# for bone in armature2.data.edit_bones:
#     print(bone.name + " head: " + str(bone.head.x) + " " + str(bone.head.y) + " " + str(bone.head.z) + \
# " tail: " + str(bone.tail.x) + " " + str(bone.tail.y) + " " + str(bone.tail.z) + " roll (in degrees): " \
# + str(degrees(bone.roll)) )
#     print("---------------------------------------------------")

# bpy.ops.object.mode_set(mode='OBJECT')
#-----------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------
# import bpy
# from .plugin_operators import ConnectOperator

# class skeletonDict:
#     def __init__(self):
#         self.ske_rb_map = {}
    
#     def receive_ske_desc(self, m_id, data_dict):
#         # m_ske = ConnectOperator.connection_setup.assets_motive['ske_desc']
#         m_ske = data_dict['ske_desc']
#         if m_id in m_ske:
#             rb_list = m_ske[m_id]['rb_desc']
#             rb_name = m_ske[m_id]['rb_name']
#         # print(rb_list)
#         # print(rb_name)
    
#     def ble_ske_desc(self, b_id, data_dict):
#         # b_ske = ConnectOperator.connection_setup.rev_assets_blender
#         obj = data_dict[b_id]['obj']

#         # b_ske_rb_id_list = []
#         b_ske_rb_name_list = []

#         if obj.type == 'ARMATURE':
#             armature = obj.data

#             for bone in armature.bones:
#                 # b_ske_rb_id_list.append(bone.id_data.session_uid) # cannot use this, cause same uids
#                 b_ske_rb_name_list.append(bone.name)
    
#     def create_ble_ske_mapping(self, m_id, b_id, m_data_dict, b_data_dict):
#         obj = b_data_dict[b_id]['obj']

#         if obj.type == 'ARMATURE':
#             armature = obj.data

#             self.ske_rb_map['m_to_b'] = {}
#             self.ske_rb_map['b_to_m'] = {}

#             for bone in armature.bones:
#                 if bone.name in m_data_dict['ske_desc'][m_id]['rb_name']:
#                     m_rb_id = m_data_dict['ske_desc'][m_id]['rb_name'][bone.name]
#                     self.ske_rb_map['m_to_b'][m_rb_id] = bone
#                     self.ske_rb_map['b_to_m'][bone] = m_rb_id
#                 else:
#                     print(bone.name, " not in Motive Skeleton.")
#-----------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------
# ### print keyframe data for a given frame
# import bpy

# print("--------------------------------------------------------------------------------------")
# # Set the frame you want to check
# target_frame = 161  # Change this to the desired frame number

# # Set the scene's frame to the target frame
# bpy.context.scene.frame_set(target_frame)

# # Iterate over all objects in the scene
# for obj in bpy.context.scene.objects:
#     if obj.animation_data and obj.animation_data.action:
#         action = obj.animation_data.action
#         print(f"Object: {obj.name}")

#         # Iterate through all FCurves in the action
#         for fcurve in action.fcurves:
#             # Print the data for the specified frame
#             for keyframe in fcurve.keyframe_points:
#                 if keyframe.co[0] == target_frame:
#                     rounded_val = round(keyframe.co[1], 3)
#                     print(f"  FCurve: {fcurve.data_path} | Array Index: {fcurve.array_index} | \
#                           Value: {rounded_val}")
#-----------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------
### Set the values from frame 161 from the animation data
# import bpy
# print("--------------------------------------------------------------------------------------")
# bone_data = {
#         'Hips': {'Loc': [0.08, 0.91, -1.16], 'Rot' : [0.19, -0.02, 0.02, 0.98]},
#         'Spine': {'Loc': [-0.00, 0.08, -0.00], 'Rot' : [0.03, 0.05, -0.00, 1.00]},
#         'Spine1': {'Loc': [0.00, 0.26, 0.00], 'Rot' : [0.12, 0.05, -0.01, 0.99]},
#         'Neck': {'Loc': [0.00, 0.28, 0.00], 'Rot' : [-0.20, -0.02, 0.05, 0.98]},
#         'Head': {'Loc': [-0.00, 0.16, 0.02], 'Rot' : [-0.07, -0.03, -0.01, 1.00]},
#         'LeftShoulder': {'Loc': [0.04, 0.24, -0.00], 'Rot' : [0.08, 0.00, -0.01, 1.00]},
#         'LeftArm': {'Loc': [0.12, 0.00, -0.00], 'Rot' : [0.29, -0.15, -0.45, 0.83]},
#         'LeftForeArm': {'Loc': [0.29, -0.00, 0.00], 'Rot' : [0.06, -0.59, 0.04, 0.81]},
#         'LeftHand': {'Loc': [0.25, -0.00, -0.00], 'Rot' : [0.08, -0.12, 0.22, 0.96]},
#         'RightShoulder': {'Loc': [-0.04, 0.24, -0.00], 'Rot' : [0.03, 0.08, 0.00, 1.00]},
#         'RightArm': {'Loc': [-0.12, 0.00, 0.00], 'Rot' : [0.05, 0.22, 0.38, 0.90]},
#         'RightForeArm': {'Loc': [-0.29, -0.00, -0.00], 'Rot' : [0.03, 0.82, -0.04, 0.56]},
#         'RightHand': {'Loc': [-0.25, -0.00, -0.00], 'Rot' : [0.10, 0.10, -0.29, 0.95]},
#         'LeftUpLeg': {'Loc': [0.10, -0.00, 0.00], 'Rot' : [-0.35, -0.02, -0.01, 0.94]},
#         'LeftLeg': {'Loc': [0.00, -0.45, -0.00], 'Rot' : [0.64, -0.00, -0.00, 0.77]},
#         'LeftFoot': {'Loc': [0.00, -0.40, 0.00], 'Rot' : [-0.02, 0.04, -0.01, 1.00]},
#         'LeftToeBase': {'Loc': [-0.00, -0.07, 0.15], 'Rot' : [-0.12, 0.00, 0.00, 0.99]},
#         'RightUpLeg': {'Loc': [-0.10, 0.00, -0.00], 'Rot' : [-0.21, -0.01, 0.01, 0.98]},
#         'RightLeg': {'Loc': [0.00, -0.45, -0.00], 'Rot' : [0.39, -0.00, 0.00, 0.92]},
#         'RightFoot': {'Loc': [-0.00, -0.40, 0.00], 'Rot' : [-0.20, -0.04, 0.03, 0.98]},
#         'RightToeBase': {'Loc': [0.00, -0.07, 0.15], 'Rot' : [-0.15, 0.00, -0.00, 0.99]},
#         }

# imported_bone_data = {
#         'Hips': {'Loc': [8.563, -2.282, -118.068], 'Rot' : [0.982, 0.189, -0.023, 0.021]},
#         'Spine': {'Loc': [-0.0, -0.0, -0.0], 'Rot' : [0.999, 0.031, 0.044, -0.001]},
#         'Spine1': {'Loc': [0.0, -0.0, -0.0], 'Rot' : [0.992, 0.116, 0.044, -0.005]},
#         'Neck': {'Loc': [0.0, -0.026, -0.0], 'Rot' : [0.98, -0.194, -0.015, 0.051]},
#         'Head': {'Loc': [-0.0, -0.026, -0.0], 'Rot' : [0.997, -0.066, -0.027, -0.014]},
#         'LeftShoulder': {'Loc': [-0.0, 0.0, 0.0], 'Rot' : [0.996, -0.002, 0.084, 0.016]},
#         'LeftArm': {'Loc': [0.0, -0.0, 0.0], 'Rot' : [0.832, -0.157, 0.282, 0.451]},
#         'LeftForeArm': {'Loc': [-0.0, -0.0, -0.0], 'Rot' : [0.81, -0.582, 0.062, -0.045]},
#         'LeftHand': {'Loc': [-0.0, 0.0, 0.0], 'Rot' : [0.965, -0.122, 0.083, -0.218]},
#         'RightShoulder': {'Loc': [-0.0, 0.0, 0.0], 'Rot' : [0.996, 0.085, -0.029, 0.003]},
#         'RightArm': {'Loc': [0.0, -0.0, 0.0], 'Rot' : [0.897, 0.225, -0.05, 0.378]},
#         'RightForeArm': {'Loc': [0.0, -0.0, -0.0], 'Rot' : [0.575, 0.816, -0.03, -0.043]},
#         'RightHand': {'Loc': [-0.0, 0.0, 0.0], 'Rot' : [0.947, 0.106, -0.097, -0.286]},
#         'LeftUpLeg': {'Loc': [0.0, 0.0, 0.0], 'Rot' : [0.941, -0.339, 0.019, 0.011]},
#         'LeftLeg': {'Loc': [-0.0, -0.0, -0.0], 'Rot' : [0.764, 0.645, -0.0, -0.0]},
#         'LeftFoot': {'Loc': [-0.0, -0.0, -0.0], 'Rot' : [0.999, -0.012, -0.01, -0.043]},
#         'LeftToeBase': {'Loc': [-0.0, 0.0, -0.0], 'Rot' : [0.993, -0.122, 0.0, -0.0]},
#         'RightUpLeg': {'Loc': [-0.0, -0.0, -0.0], 'Rot' : [0.974, -0.224, 0.015, -0.015]},
#         'RightLeg': {'Loc': [-0.0, -0.0, 0.0], 'Rot' : [0.912, 0.41, -0.0, 0.0]},
#         'RightFoot': {'Loc': [0.0, -0.0, -0.0], 'Rot' : [0.976, -0.212, 0.023, 0.044]},
#         'RightToeBase': {'Loc': [0.0, 0.0, -0.0], 'Rot' : [0.99, -0.14, 0.0, 0.0]},
#         }

# def quat_loc_yup_zup(self, pos):
#     # Motive's [X, Y, Z] -> Blender [-X, Z, Y]
#     pos_copy = [0]*3
#     pos_copy[0] = -pos[0]
#     pos_copy[1] = pos[2]
#     pos_copy[2] = pos[1]
#     return pos_copy

# def quat_product(self, r, s):
#     t0 = (r[0]*s[0] - r[1]*s[1] - r[2]*s[2] - r[3]*s[3])
#     t1 = (r[0]*s[1] + r[1]*s[0] - r[2]*s[3] + r[3]*s[2])
#     t2 = (r[0]*s[2] + r[1]*s[3] + r[2]*s[0] - r[3]*s[1])
#     t3 = (r[0]*s[3] - r[1]*s[2] + r[2]*s[1] + r[3]*s[0])
#     return [t0, t1, t2, t3]

# def quat_rot_yup_zup(self, ori):
#     # Motive's quat p -> Blender's quat p' = qpq^(-1)
#     q = [0, (1/math.sqrt(2)), (1/math.sqrt(2)), 0]
#     q_inv = [0, -(1/math.sqrt(2)), -(1/math.sqrt(2)), 0]
#     p_1 = self.quat_product(q, ori)
#     p_dash = self.quat_product(p_1, q_inv)
#     return p_dash

# def sca_first_last(self, ori):
#     ori = list(ori) # comment out later
#     ori.append(ori.pop(0))
#     return ori

# #armature = bpy.data.armatures.get("Anthony")
# armature = bpy.context.object
# # Go into pose mode to modify bones' pose
# bpy.ops.object.mode_set(mode='POSE')

# # Iterate through the dictionary and apply location and rotation to each bone
# for bone_name, data in bone_data.items():
#     if bone_name in armature.pose.bones:
#         bone = armature.pose.bones[bone_name]
        
#         # Apply location (in pose mode, we set the location relative to the rest position)
#         bone.location = data["Loc"]
        
#         # Apply rotation (set rotation using Euler angles in the bone's local space)
#         bone.rotation_quaternion = data["Rot"]
        
#         print(f"Applied location {data['Loc']} and rotation {data['Rot']} to bone {bone_name}")
#     else:
#         print(f"Bone '{bone_name}' not found in the armature.")

# # Return to object mode after applying transformations
# bpy.ops.object.mode_set(mode='OBJECT')

# for bone in armature.pose.bones:
#    loc_loc, loc_rot, loc_scale = bone.matrix.decompose()
# #   glo_loc, glo_rot, glo_scale = bone.matrix_world.decompose()
#    print("bone.matrix: " + bone.name + " Loc: " + str(loc_loc) + " Rot: " + str(loc_rot))
#    obj = bone.id_data
#    matrix_world = obj.matrix_world  # @ bone.matrix
#    glo_loc, glo_rot, _ = matrix_world.decompose()
#    print("bone.matrix_world: " + bone.name + " Loc: " + str(glo_loc) + " Rot: " + str(glo_rot))
#    matrix_final = obj.matrix_world @ bone.matrix
#    fin_loc, fin_rot, _ = matrix_final.decompose()
#    print("bone.matrix_final: " + bone.name + " Loc: " + str(fin_loc) + " Rot: " + str(fin_rot))
#-----------------------------------------------------------------------------------------------------------