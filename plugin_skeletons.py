#-----------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------
# # Description - (assets_motive)
# desc_dict['rb_desc'][rb.m_id]['name'] = rb.m_name

# desc_dict['ske_desc'][ske.m_id]['name'] = ske.m_name
# desc_dict['ske_desc'][ske.m_id]['rb_desc'][rb.m_id]['name'] = rb.m_name
# desc_dict['ske_desc'][ske.m_id]['rb_name'][rb.m_name] = rb.m_id
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
            bone_conv = create_armature.find_bone_convention(val['rb_name'])
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
                bone = armature_object.data.edit_bones.new(key)
                bone.parent = val[0]
                bone.head = val[1]
                # bone.head = existing_conn.quat_loc_yup_zup(val[1])
                bone.tail = val[2]
                # bone.tail = existing_conn.quat_loc_yup_zup(val[2])
                bone.roll = math.radians(val[3])
                bone.use_connect = val[4]

            bpy.ops.object.mode_set(mode='OBJECT') # Switch back to object mode
        
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
        
    def find_bone_convention(self):
        if 'Hip' in self.dt:
            return 'Motive'
        elif 'Hips' in self.dt:
            return 'FBX'
        elif 'pelvis' in self.dt:
            return 'UnrealEngine'
        else:
            return None

    def get_global_pos(self, item, dt): # dt = desc_dict['ske_desc'][skeleton_id]['rb_name']
        total_pos = 0
        current_bone = item

        while current_bone is not None:
            # Add local position of the current item to the total
            total_pos += dt[current_bone]['pos']
            # Move to the parent
            current_bone = dt[current_bone]['parent_name']
        
        return total_pos
    
    def update_dict(self): # dt = desc_dict['ske_desc']
        for key, val in self.dt.items():
            self.dt[key.id_num]['parent_to_children'] = {}
            for k, v in val['rb_name'].items():
                parent_id = v['parent_id']
                if parent_id != 0:
                    parent_name = val['rb_id'][parent_id]['name']
                    val['rb_name'][k]['parent_name'] = parent_name
                    if parent_name not in self.dt['ske_desc'][key.id_num]['parent_to_children']:
                        self.dt['ske_desc'][key.id_num]['parent_to_children'][parent_name] = []
                    self.dt['ske_desc'][key.id_num]['parent_to_children'][parent_name].append(k)
                else:
                    val['rb_name'][k]['parent_name'] = None
        
        for key, val in self.dt.items():
            for k, v in val['rb_name'].items():
                if k in self.dt['ske_desc'][key.id_num]['parent_to_children']:
                    v['children'] = self.dt['ske_desc'][key.id_num]['parent_to_children'][k]
                if v['parent_name'] != None:
                    v['global_pos'] = self.get_global_pos(k, self.dt[key]['rb_name'])
        
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
        direction = parent_pos - bone_pos
        if direction.length > 0:
            direction.normalize()
        end_loc = bone_pos + (0.1 * direction)
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