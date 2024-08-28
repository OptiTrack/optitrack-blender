#Copyright © 2021 Naturalpoint
#
#Licensed under the Apache License, Version 2.0 (the "License")
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#http://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.


# OptiTrack NatNet direct depacketization sample for Python 3.x
#


# Uses the Python NatNetClient.py library to establish a connection (by creating a NatNetClient),
# and receive data via a NatNet connection and decode it using the NatNetClient library.

#Utility functions

import copy
import hashlib
import random

K_SKIP = [0,0,1]
K_FAIL = [0,1,0]
K_PASS = [1,0,0]

# get_tab_str
# generate a string that takes the nesting level into account
def get_tab_str(tab_str, level):
    out_tab_str=""
    loop_range = range(0,level)
    for _ in loop_range:
        out_tab_str+=tab_str
    return out_tab_str

def add_lists(totals, totals_tmp):
    totals[0]+=totals_tmp[0]
    totals[1]+=totals_tmp[1]
    totals[2]+=totals_tmp[2]
    return totals

def test_hash(test_name, test_hash_str, test_object):
    out_str = test_object.get_as_string()
    out_hash_str=hashlib.sha1(out_str.encode()).hexdigest()
    ret_value=True
    if test_hash_str == out_hash_str:
        print("[PASS]:%s"%test_name)
    else:
        print("[FAIL]:%s test_hash_str != out_hash_str"%test_name)
        print("test_hash_str=%s"%test_hash_str)
        print("out_hash_str=%s"%out_hash_str)
        print("out_str =\n%s"%out_str)
        ret_value=False
    return ret_value


def test_hash2(test_name, test_hash_str, test_object, generator_string, run_test):
    ret_value = K_FAIL
    out_str = "FAIL"
    out_str2=""
    indent_string="       "
    if not run_test:
        ret_value = K_SKIP
        out_str = "SKIP"
    elif test_object == None:
        out_str = "FAIL"
        ret_value = K_FAIL
        out_str2 = "%sERROR: test_object was None"%indent_string
    else:

        if str(type(test_object)) != 'NoneType':
            obj_out_str = test_object.get_as_string()
            obj_out_hash_str=hashlib.sha1(obj_out_str.encode()).hexdigest()

        if test_hash_str == obj_out_hash_str:
            out_str = "PASS"
            ret_value = K_PASS
        else:
            out_str2+="%s%s test_hash_str != out_hash_str\n"%(indent_string,test_name)
            out_str2+="%stest_hash_str=%s\n"%(indent_string,test_hash_str)
            out_str2+="%sobj_out_hash_str=%s\n"%(indent_string,obj_out_hash_str)
            out_str2+="%sUpdated Test Entry:\n"%(indent_string)
            out_str2 += "%s[\"%s\", \"%s\", \"%s\", True],\n"%(indent_string,test_name,obj_out_hash_str,generator_string)
            out_str2+="%sobj_out_str =\n%s"%(indent_string,obj_out_str)


            ret_value = K_FAIL
    print("[%s]:%s"%(out_str,test_name))

    if len(out_str2):
        print("%s"%out_str2)
    return ret_value


def get_as_string(input_str):
    type_input_str=str(type(input_str))
    if type_input_str == "<class 'str'>":
        return input_str
    elif type_input_str ==  "<class 'NoneType'>":
        return ""
    elif type_input_str == "<class 'bytes'>":
        return input_str.decode('utf-8')
    elif type_input_str == "<class 'int'>":
        return str(input_str)
    else:
        print("type_input_str = %s NOT HANDLED"%type_input_str)
        return input_str


#MoCap Frame Classes
class FramePrefixData:
    def __init__(self, frame_number):
        self.frame_number=frame_number

    def get_as_string(self,tab_str="  ", level = 0):
        out_tab_str = get_tab_str(tab_str, level)
        out_str = "%sFrame #: %3.1d\n"%(out_tab_str,self.frame_number)
        return out_str

class MarkerData:
    def __init__(self):
        self.model_name=""
        self.marker_pos_list=[]

    def set_model_name(self, model_name):
        self.model_name = model_name

    def add_pos(self, pos):
        self.marker_pos_list.append(copy.deepcopy(pos))
        return len(self.marker_pos_list)


    def get_num_points(self):
        return len(self.marker_pos_list)


    def get_as_string(self, tab_str="  ", level=0):
        out_tab_str = get_tab_str(tab_str, level)
        out_tab_str2 = get_tab_str(tab_str, level+1)
        out_str=""
        out_str+="%sMarkerData:\n"%out_tab_str
        if self.model_name != "":
            out_str+="%sModel Name : %s\n"%(out_tab_str, get_as_string(self.model_name))
        marker_count = len(self.marker_pos_list)
        out_str+="%sMarker Count :%3.1d\n"%(out_tab_str, marker_count)
        for i in range(marker_count):
            pos = self.marker_pos_list[i]
            out_str+="%sMarker %3.1d pos : [x=%3.2f,y=%3.2f,z=%3.2f]\n"%(out_tab_str2,i,pos[0], pos[1], pos[2])
        return out_str

class MarkerSetData:
    def __init__(self):
        self.marker_data_list=[]
        self.unlabeled_markers=MarkerData()
        self.unlabeled_markers.set_model_name("")

    def add_marker_data(self, marker_data):
        self.marker_data_list.append(copy.deepcopy(marker_data))
        return len(self.marker_data_list)

    def add_unlabeled_marker(self, pos):
        self.unlabeled_markers.add_pos(pos)

    def get_marker_set_count(self):
        return len(self.marker_data_list)

    def get_unlabeled_marker_count(self):
        return self.unlabeled_markers.get_num_points()
    def get_as_string(self, tab_str="  ", level=0):
        out_tab_str  = get_tab_str(tab_str, level)


        out_str=""

        # Labeled markers count
        marker_data_count = len(self.marker_data_list)
        out_str+= "%sMarkerset Count:%3.1d\n"% (out_tab_str,marker_data_count)
        for marker_data in self.marker_data_list:
            out_str += marker_data.get_as_string(tab_str,level+1)

        # Unlabeled markers count (4 bytes)
        unlabeled_markers_count = self.unlabeled_markers.get_num_points()
        out_str += "%sUnlabeled Marker Count:%3.1d\n"%(out_tab_str, unlabeled_markers_count )
        out_str += self.unlabeled_markers.get_as_string(tab_str,level+1)
        return out_str

class LegacyMarkerData:
    def __init__(self):
        self.marker_pos_list=[]

    def add_pos(self, pos):
        self.marker_pos_list.append(copy.deepcopy(pos))
        return len(self.marker_pos_list)

    def get_marker_count(self):
        return len(self.marker_pos_list)

    def get_as_string(self, tab_str="  ", level=0):
        out_tab_str = get_tab_str(tab_str, level)
        out_tab_str2 = get_tab_str(tab_str, level+1)
        out_str=""
        marker_count = len(self.marker_pos_list)
        out_str+="%sLegacy Marker Count :%3.1d\n"%(out_tab_str, marker_count)
        for i in range(marker_count):
            pos = self.marker_pos_list[i]
            out_str+="%sMarker %3.1d pos : [x=%3.2f,y=%3.2f,z=%3.2f]\n"%(out_tab_str2,i,pos[0], pos[1], pos[2])
        return out_str

class RigidBodyMarker:
    def __init__(self):
        self.pos = [0.0,0.0,0.0]
        self.id_num = 0
        self.size = 0
        self.error = 0
        self.marker_num = -1

    def get_as_string(self, tab_str="  ", level=0):
        out_tab_str = get_tab_str(tab_str, level)
        out_str = ""
        out_str += "%sRBMarker:"%( out_tab_str)
        if ( self.marker_num > -1 ):
            out_str += " %3.1d"%( self.marker_num )
        out_str += "\n"

        out_str += "%sPosition: [%3.2f %3.2f %3.2f]\n"%( out_tab_str, self.pos[0], self.pos[1], self.pos[2] )
        out_str += "%sID      : %3.1d\n"%(out_tab_str, self.id_num)
        out_str += "%sSize    : %3.1d\n"%(out_tab_str, self.size)
        return out_str


class RigidBody:
    def __init__(self, new_id, pos, rot):
        self.id_num = new_id
        self.pos=pos
        self.rot=rot
        self.rb_marker_list=[]
        self.tracking_valid = False
        self.error = 0.0
        self.marker_num = -1

    def add_rigid_body_marker(self, rigid_body_marker):
        self.rb_marker_list.append(copy.deepcopy(rigid_body_marker))
        return len(self.rb_marker_list)

    def save_pos_ori(self):
        return self.pos, self.rot

    def get_as_string(self, tab_str=0, level=0):
        out_tab_str = get_tab_str(tab_str, level)
        out_tab_str2 = get_tab_str(tab_str, level+1)

        out_str=""

        # header
        out_str += "%sRigid Body    :"% (out_tab_str)
        if ( self.marker_num > -1 ):
            out_str += " %3.1d"% (self.marker_num)
        out_str += "\n"
        out_str += "%s  ID            : %3.1d\n"% (out_tab_str, self.id_num)
        # Position and orientation
        out_str += "%s  Position      : [%3.2f, %3.2f, %3.2f]\n"% (out_tab_str, self.pos[0], self.pos[1], self.pos[2] )
        out_str += "%s  Orientation   : [%3.2f, %3.2f, %3.2f, %3.2f]\n"% (out_tab_str, self.rot[0], self.rot[1], self.rot[2], self.rot[3] )

        marker_count = len(self.rb_marker_list)
        marker_count_range = range( 0, marker_count )

        # Marker Data
        if marker_count > 0:
            out_str += "%s  Marker Count  : %3.1d\n"%(out_tab_str, marker_count )
            for i in marker_count_range:
                rbmarker = self.rb_marker_list[i]
                rbmarker.marker_num=i
                out_str += rbmarker.get_as_string(tab_str, level+2)

        out_str += "%s  Marker Error  : %3.2f\n"% (out_tab_str, self.error)

        # Valid Tracking
        tf_string = 'False'
        if self.tracking_valid:
            tf_string = 'True'
        out_str += "%sTracking Valid: %s\n"%(out_tab_str, tf_string)

        return out_str


class RigidBodyData:
    def __init__(self):
        self.rigid_body_list=[]

    def add_rigid_body(self, rigid_body):
        self.rigid_body_list.append(copy.deepcopy(rigid_body))
        return len(self.rigid_body_list)


    def get_rigid_body_count(self): 
        return len(self.rigid_body_list)
    
    def get_pos_ori(self):
        locs = []
        oris = []

        for rigid_body in self.rigid_body_list:
            loc, ori = rigid_body.save_pos_ori()
            locs.append(loc)
            oris.append(ori)
        return locs, oris

    def get_as_string(self, tab_str="  ", level=0):
        out_tab_str = get_tab_str(tab_str, level)
        out_str=""
        rigid_body_count=len(self.rigid_body_list)
        out_str += "%sRigid Body Count: %3.1d\n"%(out_tab_str, rigid_body_count)
        rb_num=0
        for rigid_body in self.rigid_body_list:
            rigid_body.marker_num=rb_num
            out_str += rigid_body.get_as_string(tab_str, level+1)
            rb_num+=1
        return out_str


class Skeleton:
    def __init__(self, new_id=0):
        self.id_num=new_id
        self.rigid_body_list=[]


    def add_rigid_body(self, rigid_body):
        self.rigid_body_list.append(copy.deepcopy(rigid_body))
        return len(self.rigid_body_list)


    def get_as_string(self, tab_str="  ", level=0):
        out_tab_str = get_tab_str(tab_str, level)
        out_tab_str2 = get_tab_str(tab_str, level+1)
        out_str=""
        out_str+="%sID: %3.1d\n"%(out_tab_str, self.id_num)
        rigid_body_count=len(self.rigid_body_list)
        out_str += "%sRigid Body Count: %3.1d\n"%(out_tab_str, rigid_body_count)
        for rb_num in range(rigid_body_count):
            self.rigid_body_list[rb_num].marker_num = rb_num
            out_str += self.rigid_body_list[rb_num].get_as_string(tab_str, level+2)
        return out_str


class SkeletonData:
    def __init__(self):
        self.skeleton_list=[]


    def add_skeleton(self, new_skeleton):
        self.skeleton_list.append(copy.deepcopy(new_skeleton))


    def get_skeleton_count(self):
        return len(self.skeleton_list)


    def get_as_string(self, tab_str = "  ", level=0):
        out_tab_str = get_tab_str(tab_str, level)
        out_tab_str2 = get_tab_str(tab_str, level+1)

        out_str = ""
        skeleton_count = len(self.skeleton_list)
        out_str += "%sSkeleton Count: %3.1d\n"%(out_tab_str, skeleton_count)
        for skeleton_num in range(skeleton_count):
            out_str += "%sSkeleton %3.1d\n"%(out_tab_str2, skeleton_num)
            out_str += self.skeleton_list[skeleton_num].get_as_string(tab_str, level+2)
        return out_str

class AssetMarkerData:
    def __init__(self, marker_id, pos, marker_size=0.0, marker_params=0, residual=0.0, marker_num=-1):
        self.marker_id=marker_id
        self.pos=pos
        self.marker_size=marker_size
        self.marker_params=marker_params
        self.residual=residual
        self.marker_num=marker_num

    def get_as_string(self, tab_str="  ", level=0):
        out_tab_str = get_tab_str(tab_str, level)
        out_tab_str2 = get_tab_str(tab_str, level+1)
        out_str=""
        if( False ):
            out_str+="%sID       : %s\n"%(out_tab_str, get_as_string(self.marker_id))
            out_str+="%sPos      : %3.2f %3.2f %3.2f\n"%(out_tab_str, self.pos[0], self.pos[1], self.pos[2])
            out_str+="%sSize     : %3.2f\n"%(out_tab_str, self.marker_size)
            out_str+="%sParams   : %s\n"%(out_tab_str, self.marker_params)
            out_str+="%sResidual : %3.2f\n"%(out_tab_str, self.residual)
        else:
            out_str+="%s"%(out_tab_str)
            if(self.marker_num > -1):
                out_str+="%3.1d "%(self.marker_num)
            else:
                out_str+="    "
            out_str+="Marker %7.1d"%(self.marker_id)
            out_str+=" pos : [%3.2f, %3.2f, %3.2f] "%(self.pos[0], self.pos[1], self.pos[2])
            out_str+="       size=%3.2f"%(self.marker_size)
            out_str+="       err=%3.2f"%(self.residual)
            out_str+="        params=%d"%(self.marker_params)
            out_str+="\n"
            

        return out_str

class AssetRigidBodyData:
    def __init__(self, new_id, pos, rot, mean_error=0.0, param=0):
        self.id_num=new_id
        self.pos = pos
        self.rot = rot
        self.mean_error = mean_error
        self.param = param
        self.rb_num = -1

    def get_as_string(self, tab_str="  ", level=0):
        out_tab_str = get_tab_str(tab_str, level)
        out_str=""
        out_str += "%sRigid Body :"%(out_tab_str)
        if(self.rb_num > -1):
            out_str += "%3.1d"%(self.rb_num)
        out_str += "\n"
        out_str += "%sID          : %s\n"%(out_tab_str, get_as_string(self.id_num))
        out_str += "%sPosition    : [%3.2f, %3.2f, %3.2f]\n"%(out_tab_str, self.pos[0], self.pos[1], self.pos[2])
        out_str += "%sOrientation : [%3.2f, %3.2f, %3.2f, %3.2f]\n"%(out_tab_str, self.rot[0], self.rot[1], self.rot[2], self.rot[3])
        out_str += "%sMean Error  : %3.2f\n"%(out_tab_str, self.mean_error)
        out_str += "%sParams      : %3.1d\n"%(out_tab_str, self.param)

        return out_str

class Asset:
    def __init__(self):
        self.asset_id=0
        self.rigid_body_list=[]
        self.marker_list=[]

    def set_id(self, new_id):
        self.asset_id=new_id

    def add_rigid_body(self, rigid_body):
        self.rigid_body_list.append(copy.deepcopy(rigid_body))
        return len(self.rigid_body_list)

    def add_marker(self, marker):
        self.marker_list.append(copy.deepcopy(marker))
        return len(self.marker_list)

    def get_rigid_body_count(self):
        return len(self.rigid_body_list)

    def get_marker_count(self):
        return len(self.marker_list)

    def get_as_string(self, tab_str = "  ", level = 0):
        out_tab_str = get_tab_str(tab_str, level)

        out_str = ""
        out_str += "%sAsset ID        : %d\n"%(out_tab_str,self.asset_id)
        rigid_body_count = len(self.rigid_body_list)
        out_str += "%sRigid Body Count: %3.1d\n"%(out_tab_str, rigid_body_count)
        rb_num=0
        for rigid_body in self.rigid_body_list:
            rigid_body.rb_num=rb_num
            out_str += rigid_body.get_as_string(tab_str, level+1)
            rb_num+=1

        marker_count = len(self.marker_list)
        out_str += "%sMarker Count: %3.1d\n"%(out_tab_str, marker_count)
        marker_num = 0
        for marker in self.marker_list:
            marker.marker_num = marker_num
            out_str += marker.get_as_string(tab_str, level+1)
            marker_num+=1
        return out_str



class AssetData:
    def __init__(self):
        self.asset_list=[]

    def add_asset(self, new_asset):
        self.asset_list.append(copy.deepcopy(new_asset))

    def get_asset_count(self):
        return len(self.asset_list)

    def get_as_string(self, tab_str = "  ", level=0):
        out_tab_str = get_tab_str(tab_str, level)
        out_tab_str2 = get_tab_str(tab_str, level+1)

        out_str = ""
        asset_count = self.get_asset_count()
        out_str += "%sAsset Count: %3.1d\n"%(out_tab_str, asset_count)
        for asset_num in range(asset_count):
            out_str += "%sAsset %3.1d\n"%(out_tab_str2, asset_num)
            out_str += self.asset_list[asset_num].get_as_string(tab_str, level+2)
        return out_str



class LabeledMarker:
    def __init__(self, new_id, pos, size=0.0, param = 0, residual=0.0):
        self.id_num=new_id
        self.pos = pos
        self.size = size
        self.param = param
        self.residual = residual
        self.marker_num=-1
        if str(type(size)) == "<class 'tuple'>":
            self.size=size[0]

    def __decode_marker_id(self):
        model_id = self.id_num >> 16
        marker_id = self.id_num & 0x0000ffff
        return model_id, marker_id

    def __decode_param(self):
        occluded = ( self.param & 0x01 ) != 0
        point_cloud_solved = ( self.param & 0x02 ) != 0
        model_solved = ( self.param & 0x04 ) != 0
        return occluded,point_cloud_solved, model_solved

    def get_as_string(self, tab_str, level):
        out_tab_str = get_tab_str(tab_str, level)
        model_id, marker_id = self.__decode_marker_id()
        out_str = ""
        out_str+="%sLabeled Marker"%out_tab_str
        if(self.marker_num > -1):
            out_str+=" %d"%self.marker_num
        out_str+=":\n"
        out_str += "%sID                 : [MarkerID: %3.1d] [ModelID: %3.1d]\n"%(out_tab_str, marker_id,model_id)
        out_str += "%spos                : [%3.2f, %3.2f, %3.2f]\n"%(out_tab_str, self.pos[0],self.pos[1],self.pos[2])
        out_str += "%ssize               : [%3.2f]\n"%(out_tab_str, self.size)
        out_str += "%serr                : [%3.2f]\n"%(out_tab_str, self.residual)

        occluded, point_cloud_solved, model_solved = self.__decode_param()
        out_str += "%soccluded           : [%3.1d]\n"%(out_tab_str, occluded)
        out_str += "%spoint_cloud_solved : [%3.1d]\n"%(out_tab_str, point_cloud_solved)
        out_str += "%smodel_solved       : [%3.1d]\n"%(out_tab_str, model_solved)

        return out_str


class LabeledMarkerData:
    def __init__(self):
        self.labeled_marker_list=[]

    def add_labeled_marker(self, labeled_marker):
        self.labeled_marker_list.append(copy.deepcopy(labeled_marker))
        return len(self.labeled_marker_list)

    def get_labeled_marker_count(self):
        return len(self.labeled_marker_list)

    def get_as_string(self, tab_str = "  ", level = 0):
        out_tab_str = get_tab_str(tab_str, level)
        out_tab_str2 = get_tab_str(tab_str, level+1)
        out_str = ""

        labeled_marker_count = len(self.labeled_marker_list)
        out_str += "%sLabeled Marker Count:%3.1d\n"%(out_tab_str, labeled_marker_count )
        for i in range( 0, labeled_marker_count ):
            labeled_marker = self.labeled_marker_list[i]
            labeled_marker.marker_num=i
            out_str += labeled_marker.get_as_string(tab_str, level+2)
        return out_str

class ForcePlateChannelData:
    def __init__(self):
        # list of floats
        self.frame_list=[]


    def add_frame_entry(self, frame_entry):
        self.frame_list.append(copy.deepcopy(frame_entry))
        return len(self.frame_list)


    def get_as_string(self, tab_str, level, channel_num = -1):
        fc_max = 4
        out_tab_str  = get_tab_str(tab_str, level)

        out_str = ""
        frame_count = len(self.frame_list)
        fc_show = min(frame_count, fc_max)
        out_str += "%s"%(out_tab_str)
        if channel_num >= 0 :
            out_str += "Channel %3.1d: "%channel_num
        out_str += "%3.1d Frames - Frame Data: "%(frame_count)
        for i in range(fc_show):
            out_str += "%3.2f "%(self.frame_list[i])
        if fc_show < frame_count :
            out_str += " - Showing %3.1d of %3.1d frames"%(fc_show, frame_count)
        out_str += "\n"
        return out_str

class ForcePlate:
    def __init__(self, new_id=0):
        self.id_num = new_id
        self.channel_data_list=[]

    def add_channel_data(self, channel_data):
        self.channel_data_list.append(copy.deepcopy(channel_data))
        return len(self.channel_data_list)

    def get_as_string(self, tab_str, level):
        out_tab_str = get_tab_str(tab_str, level)
        out_str = ""

        out_str += "%sID           : %3.1d"%(out_tab_str, self.id_num)
        num_channels = len(self.channel_data_list)
        out_str += "  Channel Count: %3.1d\n"%( num_channels)
        for i in range(num_channels):
            out_str += self.channel_data_list[i].get_as_string(tab_str, level+1,i)
        return out_str

class ForcePlateData:
    def __init__(self):
        self.force_plate_list=[]

    def add_force_plate(self, force_plate):
        self.force_plate_list.append(copy.deepcopy(force_plate))
        return len(self.force_plate_list)


    def get_force_plate_count(self):
        return len(self.force_plate_list)


    def get_as_string(self, tab_str="  ", level=0):
        out_tab_str = get_tab_str(tab_str, level)
        out_tab_str2 = get_tab_str(tab_str, level+1)
        out_str=""

        force_plate_count = len(self.force_plate_list)
        out_str += "%sForce Plate Count: %3.1d\n"%(out_tab_str, force_plate_count)
        for i in range(force_plate_count):
            out_str += "%sForce Plate %3.1d\n"%(out_tab_str2, i)
            out_str += self.force_plate_list[i].get_as_string(tab_str, level+2)

        return out_str

class DeviceChannelData:
    def __init__(self):
        # list of floats
        self.frame_list=[]


    def add_frame_entry(self, frame_entry):
        self.frame_list.append(copy.deepcopy(frame_entry))
        return len(self.frame_list)


    def get_as_string(self, tab_str, level, channel_num = -1):
        fc_max = 4
        out_tab_str  = get_tab_str(tab_str, level)

        out_str = ""
        frame_count = len(self.frame_list)
        fc_show = min(frame_count, fc_max)
        out_str += "%s"%(out_tab_str)
        if channel_num >= 0:
            out_str += "Channel %3.1d: "%channel_num
        out_str += "%3.1d Frames - Frame Data: "%(frame_count)
        for i in range(fc_show):
            out_str += "%3.2f "%(self.frame_list[i])
        if fc_show < frame_count:
            out_str += " - Showing %3.1d of %3.1d frames"%(fc_show, frame_count)
        out_str += "\n"
        return out_str


class Device:
    def __init__(self, new_id):
        self.id_num=new_id
        self.channel_data_list = []

    def add_channel_data(self, channel_data):
        self.channel_data_list.append(copy.deepcopy(channel_data))
        return len(self.channel_data_list)

    def get_as_string(self, tab_str, level, device_num):
        out_tab_str = get_tab_str(tab_str, level)

        out_str = ""

        num_channels = len(self.channel_data_list)
        out_str+= "%sDevice %3.1d      ID: %3.1d Num Channels: %3.1d\n"% (out_tab_str, device_num, self.id_num, num_channels )
        for i in range(num_channels):
            out_str += self.channel_data_list[i].get_as_string(tab_str, level+1, i)

        return out_str


class DeviceData:
    def __init__(self):
        self.device_list=[]

    def add_device(self, device):
        self.device_list.append(copy.deepcopy(device))
        return len(self.device_list)


    def get_device_count(self):
        return len(self.device_list)


    def get_as_string(self, tab_str = "  ", level = 0):
        out_tab_str = get_tab_str(tab_str, level)

        out_str = ""

        device_count = len(self.device_list)
        out_str += "%sDevice Count: %3.1d\n"%(out_tab_str, device_count)
        for i in range(device_count):
            out_str += self.device_list[i].get_as_string(tab_str, level+1, i)
        return out_str

class FrameSuffixData:
    def __init__(self):
        self.timecode=-1
        self.timecode_sub=-1
        self.timestamp = -1
        self.stamp_camera_mid_exposure = -1
        self.stamp_data_received = -1
        self.stamp_transmit = -1
        self.prec_timestamp_secs = -1
        self.prec_timestamp_frac_secs = -1
        self.param = 0
        self.is_recording = False
        self.tracked_models_changed = True
        self.live_mode = False


    def get_as_string(self, tab_str="  ", level=0):
        out_tab_str = get_tab_str(tab_str, level)

        out_str = ""
        if not self.timestamp == -1:
            out_str += "%sTimestamp                      : %3.3f\n"%(out_tab_str, self.timestamp)
        if not self.stamp_camera_mid_exposure == -1:
            out_str += "%sMid-exposure timestamp         : %3.1d\n"%(out_tab_str, self.stamp_camera_mid_exposure)
        if not self.stamp_data_received == -1:
            out_str += "%sCamera data received timestamp : %3.1d\n"%(out_tab_str, self.stamp_data_received)
        if not self.stamp_transmit == -1:
            out_str += "%sTransmit timestamp             : %3.1d\n"%(out_tab_str, self.stamp_transmit)
        if not self.prec_timestamp_secs == -1:
            #hours = int(self.prec_timestamp_secs/3600)
            #minutes=int(self.prec_timestamp_secs/60)%60
            #seconds=self.prec_timestamp_secs%60
            #hms_string="%sPrecision timestamp (hh:mm:ss) : %2.1d:%2.2d:%2.2d\n"%(out_tab_str,hours, minutes, seconds)
            #out_str += hms_string
            out_str += "%sPrecision timestamp (seconds)  : %3.1d\n"%(out_tab_str, self.prec_timestamp_secs)
            if not self.prec_timestamp_frac_secs == -1:
                out_str += "%sPrecision timestamp (fractional seconds) : %3.1d\n"%(out_tab_str, self.prec_timestamp_frac_secs)

        return out_str

class MoCapData:
    def __init__(self):
        #Packet Parts
        self.prefix_data = None
        self.marker_set_data = None
        self.legacy_other_markers = None
        self.rigid_body_data = None
        self.asset_data = None
        self.skeleton_data = None
        self.labeled_marker_data = None
        self.force_plate_data = None
        self.device_data = None
        self.suffix_data = None

    def set_prefix_data(self, new_prefix_data):
        self.prefix_data = new_prefix_data

    def set_marker_set_data(self, new_marker_set_data):
        self.marker_set_data = new_marker_set_data

    def set_legacy_other_markers(self, new_marker_set_data):
        self.legacy_other_markers = new_marker_set_data

    def set_rigid_body_data(self, new_rigid_body_data):
        self.rigid_body_data = new_rigid_body_data

    def set_skeleton_data(self, new_skeleton_data):
        self.skeleton_data = new_skeleton_data

    def set_asset_data(self, new_asset_data):
        self.asset_data=new_asset_data

    def set_labeled_marker_data(self, new_labeled_marker_data):
        self.labeled_marker_data = new_labeled_marker_data

    def set_force_plate_data(self, new_force_plate_data):
        self.force_plate_data = new_force_plate_data

    def set_device_data(self, new_device_data):
        self.device_data = new_device_data

    def set_suffix_data(self, new_suffix_data):
        self.suffix_data = new_suffix_data

    def retrieve_pos_ori(self):
        if not self.rigid_body_data == None:
            locs, oris = self.rigid_body_data.get_pos_ori()
            return locs, oris

    def get_as_string(self, tab_str = "  ", level = 0):
        out_tab_str = get_tab_str(tab_str, level)

        out_str=""
        out_str+= "%sMoCap Frame Begin\n%s-----------------\n"%(out_tab_str,out_tab_str)
        if not self.prefix_data == None:
            out_str+=self.prefix_data.get_as_string()
        else:
            out_str+="%sNo Prefix Data Set\n"%(out_tab_str)

        if not self.marker_set_data == None:
            out_str+=self.marker_set_data.get_as_string(tab_str, level+1)
        else:
            out_str+="%sNo Markerset Data Set\n"%(out_tab_str)

        if not self.rigid_body_data == None:
            out_str+=self.rigid_body_data.get_as_string(tab_str, level+1)
        else:
            out_str+="%sNo Rigid Body Data Set\n"%(out_tab_str)

        if not self.skeleton_data == None:
            out_str+=self.skeleton_data.get_as_string(tab_str, level+1)
        else:
            out_str+="%sNo Skeleton Data Set\n"%(out_tab_str)

        if not self.asset_data == None:
            out_str+=self.asset_data.get_as_string(tab_str, level+1)
        else:
            out_str+="%sNo Asset Data Set\n"%(out_tab_str)

        if not self.labeled_marker_data == None:
            out_str+=self.labeled_marker_data.get_as_string(tab_str, level+1)
        else:
            out_str+="%sNo Labeled Marker Data Set\n"%(out_tab_str)

        if not self.force_plate_data == None:
            out_str+=self.force_plate_data.get_as_string(tab_str, level+1)
        else:
            out_str+="%sNo Force Plate Data Set\n"%(out_tab_str)

        if not self.device_data == None:
            out_str+=self.device_data.get_as_string(tab_str, level+1)
        else:
            out_str+="%sNo Device Data Set\n"%(out_tab_str)

        if not self.suffix_data == None:
            out_str+=self.suffix_data.get_as_string(tab_str, level+1)
        else:
            out_str+="%sNo Suffix Data Set\n"%(out_tab_str)

        out_str+= "%sMoCap Frame End\n%s-----------------\n"%(out_tab_str,out_tab_str)

        return out_str