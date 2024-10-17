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

# import bpy
# # from .plugin_operators import ConnectOperator
# from collections import OrderedDict

#-----------------------------------------------------------------------------------------------------
# # create lookup in blender armature data for bone names
# motive_skeleton_hierarchy = ['Hips', 'Spine', 'Spine1', 'Neck', 'Head', 'LeftShoulder', 'LeftArm', \
#                    'LeftForeArm', 'LeftHand', 'RightShoulder', 'RightArm', 'RightForeArm', \
#                    'RightHand', 'LeftUpLeg', 'LeftLeg', 'LeftFoot', 'LeftToeBase', \
#                     'RightUpLeg', 'RightLeg', 'RightFoot', 'RightToeBase']
#-----------------------------------------------------------------------------------------------------

# # request data descriptions

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