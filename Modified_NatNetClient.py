# Copyright © 2018 Naturalpoint
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# OptiTrack NatNet direct depacketization library for Python 3.x

import copy
import socket
import struct
import sys
import time
from threading import Thread

import mathutils

from . import DataDescriptions, MoCapData
from .repository.skeleton import BoneData, SkeletonData, SkeletonRepository


def trace(*args):
    # uncomment the one you want to use
    # print( "".join(map(str,args)) )
    pass


# Used for Data Description functions
def trace_dd(*args):
    # uncomment the one you want to use
    # print("".join(map(str, args)))
    pass


# Used for MoCap Frame Data functions
def trace_mf(*args):
    # uncomment the one you want to use
    # print("".join(map(str, args)))
    pass


def get_message_id(data):
    message_id = int.from_bytes(data[0:2], byteorder="little", signed=True)
    return message_id


# Create structs for reading various object types to speed up parsing.
Vector2 = struct.Struct("<ff")
Vector3 = struct.Struct("<fff")
Quaternion = struct.Struct("<ffff")
FloatValue = struct.Struct("<f")
DoubleValue = struct.Struct("<d")
NNIntValue = struct.Struct("<I")
FPCalMatrixRow = struct.Struct("<ffffffffffff")
FPCorners = struct.Struct("<ffffffffffff")


class NatNetClient:
    # print_level = 0 off
    # print_level = 1 on
    # print_level = >1 on / print every nth mocap frame
    print_level = 1

    def __init__(self):
        # Change this value to the IP address of the NatNet server.
        self.server_ip_address = "127.0.0.1"

        # Change this value to the IP address of your local network interface
        self.local_ip_address = "127.0.0.1"

        # This should match the multicast address listed in Motive's streaming settings.
        self.multicast_address = "239.255.42.99"

        # NatNet Command channel
        self.command_port = 1510

        # NatNet Data channel
        self.data_port = 1511

        self.use_multicast = True

        # Set this to a callback method of your choice to receive per-rigid-body data at each frame.
        self.rigid_body_listener = None
        # self.model_changed = None
        # self.motive_edit = None
        self.new_frame_listener = None
        self.rb_listener = None
        self.data_listener = None

        # Set Application Name
        self.__application_name = "Not Set"

        # NatNet stream version server is capable of. This will be updated during initialization only.
        self.__nat_net_stream_version_server = [0, 0, 0, 0]

        # NatNet stream version. This will be updated to the actual version the server is using \
        # during runtime.
        self.__nat_net_requested_version = [0, 0, 0, 0]

        # server stream version. This will be updated to the actual version the server is \
        # using during initialization.
        self.__server_version = [0, 0, 0, 0]

        # Lock values once run is called
        self.__is_locked = False

        # Server has the ability to change bitstream version
        self.__can_change_bitstream_version = False

        self.command_thread = None
        self.data_thread = None
        self.command_socket = None
        self.data_socket = None

        self.stop_threads = False

    # Client/server message ids
    NAT_CONNECT = 0
    NAT_SERVERINFO = 1
    NAT_REQUEST = 2
    NAT_RESPONSE = 3
    NAT_REQUEST_MODELDEF = 4
    NAT_MODELDEF = 5
    NAT_REQUEST_FRAMEOFDATA = 6
    NAT_FRAMEOFDATA = 7
    NAT_MESSAGESTRING = 8
    NAT_DISCONNECT = 9
    NAT_KEEPALIVE = 10
    NAT_UNRECOGNIZED_REQUEST = 100
    NAT_UNDEFINED = 999999.9999

    def set_client_address(self, local_ip_address):
        if not self.__is_locked:
            self.local_ip_address = local_ip_address

    def get_client_address(self):
        return self.local_ip_address

    def set_server_address(self, server_ip_address):
        if not self.__is_locked:
            self.server_ip_address = server_ip_address

    def get_server_address(self):
        return self.server_ip_address

    def set_use_multicast(self, use_multicast):
        if not self.__is_locked:
            self.use_multicast = use_multicast

    def can_change_bitstream_version(self):
        return self.__can_change_bitstream_version

    def set_nat_net_version(self, major, minor):
        """checks to see if stream version can change, then changes it with position reset"""
        return_code = -1
        if self.__can_change_bitstream_version and (
            (major != self.__nat_net_requested_version[0])
            or (minor != self.__nat_net_requested_version[1])
        ):
            sz_command = "Bitstream,%1.1d.%1.1d" % (major, minor)
            return_code = self.send_command(sz_command)
            if return_code >= 0:
                self.__nat_net_requested_version[0] = major
                self.__nat_net_requested_version[1] = minor
                self.__nat_net_requested_version[2] = 0
                self.__nat_net_requested_version[3] = 0
                print("changing bitstream MAIN")
                # get original output state
                # print_results = self.get_print_results()
                # turn off output
                # self.set_print_results(False)
                # force frame send and play reset
                self.send_command("TimelinePlay")
                time.sleep(0.1)
                tmpCommands = [
                    "TimelinePlay",
                    "TimelineStop",
                    "SetPlaybackCurrentFrame,0",
                    "TimelineStop",
                ]
                self.send_commands(tmpCommands, False)
                time.sleep(2)
                # reset to original output state
                # self.set_print_results(print_results)
            else:
                print("Bitstream change request failed")
        return return_code

    def get_major(self):
        return self.__nat_net_requested_version[0]

    def get_minor(self):
        return self.__nat_net_requested_version[1]

    def set_print_level(self, print_level=0):
        if print_level >= 0:
            self.print_level = print_level
        return self.print_level

    def get_print_level(self):
        return self.print_level

    def connected(self):
        ret_value = True
        # check sockets
        if self.command_socket == None:
            ret_value = False
        elif self.data_socket == None:
            ret_value = False
        # check versions
        elif self.get_application_name() == "Not Set":
            ret_value = False
        elif (
            (self.__server_version[0] == 0)
            and (self.__server_version[1] == 0)
            and (self.__server_version[2] == 0)
            and (self.__server_version[3] == 0)
        ):
            ret_value = False
        return ret_value

    # Create a command socket to attach to the NatNet stream
    def __create_command_socket(self):
        result = None
        if self.use_multicast:
            # Multicast case
            result = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
            # allow multiple clients on same machine to use multicast group address/port
            result.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                result.bind(("", 0))
            except socket.error as msg:
                print("ERROR: command socket error occurred:\n%s" % msg)
                print(
                    "Check Motive/Server mode requested mode agreement.  You requested Multicast "
                )
                result = None
            except socket.herror:
                print("ERROR: command socket herror occurred")
                result = None
            except socket.gaierror:
                print("ERROR: command socket gaierror occurred")
                result = None
            except socket.timeout:
                print("ERROR: command socket timeout occurred. Server not responding")
                result = None
            # set to broadcast mode
            result.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            # set timeout to allow for keep alive messages
            result.settimeout(2.0)
        else:
            # Unicast case
            result = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
            )
            try:
                result.bind((self.local_ip_address, 0))
            except socket.error as msg:
                print("ERROR: command socket error occurred:\n%s" % msg)
                print(
                    "Check Motive/Server mode requested mode agreement.  You requested Unicast "
                )
                result = None
            except socket.herror:
                print("ERROR: command socket herror occurred")
                result = None
            except socket.gaierror:
                print("ERROR: command socket gaierror occurred")
                result = None
            except socket.timeout:
                print("ERROR: command socket timeout occurred. Server not responding")
                result = None

            # set timeout to allow for keep alive messages
            result.settimeout(2.0)
            result.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        return result

    # Create a data socket to attach to the NatNet stream
    def __create_data_socket(self, port):
        result = None

        if self.use_multicast:
            # Multicast case
            result = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM, 0  # Internet
            )  # UDP
            result.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            result.setsockopt(
                socket.IPPROTO_IP,
                socket.IP_ADD_MEMBERSHIP,
                socket.inet_aton(self.multicast_address)
                + socket.inet_aton(self.local_ip_address),
            )
            try:
                result.bind((self.local_ip_address, port))
            except socket.error as msg:
                print("ERROR: data socket error occurred:\n%s" % msg)
                print(
                    "  Check Motive/Server mode requested mode agreement.  You requested Multicast "
                )
                result = None
            except socket.herror:
                print("ERROR: data socket herror occurred")
                result = None
            except socket.gaierror:
                print("ERROR: data socket gaierror occurred")
                result = None
            except socket.timeout:
                print("ERROR: data socket timeout occurred. Server not responding")
                result = None
        else:
            # Unicast case
            result = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP  # Internet
            )
            result.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # result.bind( (self.local_ip_address, port) )
            try:
                result.bind(("", 0))
            except socket.error as msg:
                print("ERROR: data socket error occurred:\n%s" % msg)
                print(
                    "Check Motive/Server mode requested mode agreement. You requested Unicast "
                )
                result = None
            except socket.herror:
                print("ERROR: data socket herror occurred")
                result = None
            except socket.gaierror:
                print("ERROR: data socket gaierror occurred")
                result = None
            except socket.timeout:
                print("ERROR: data socket timeout occurred. Server not responding")
                result = None

            if self.multicast_address != "255.255.255.255":
                result.setsockopt(
                    socket.IPPROTO_IP,
                    socket.IP_ADD_MEMBERSHIP,
                    socket.inet_aton(self.multicast_address)
                    + socket.inet_aton(self.local_ip_address),
                )

        return result

    # Unpack Mocap Data Functions
    def __unpack_frame_prefix_data(self, data):
        offset = 0
        global frame_number
        # Frame number (4 bytes)
        frame_number = int.from_bytes(
            data[offset : offset + 4], byteorder="little", signed=True
        )
        offset += 4
        frame_prefix_data = MoCapData.FramePrefixData(frame_number)
        return offset, frame_prefix_data

    def __unpack_marker_set_data(self, data, packet_size, major, minor):
        offset = 0
        # Markerset count (4 bytes)
        marker_set_count = int.from_bytes(
            data[offset : offset + 4], byteorder="little", signed=True
        )
        offset += 4

        # get data size (4 bytes)
        offset_tmp, unpackedDataSize = self.__unpack_data_size(
            data[offset:], major, minor
        )
        offset += offset_tmp

        for i in range(0, marker_set_count):
            model_name, separator, remainder = bytes(data[offset:]).partition(b"\0")
            offset += len(model_name) + 1
            # Marker count (4 bytes)
            marker_count = int.from_bytes(
                data[offset : offset + 4], byteorder="little", signed=True
            )
            offset += 4
            if marker_count < 0:
                print("WARNING: Early return.  Invalid marker count")
                offset = len(data)
                return offset
            elif marker_count > 10000:
                print("WARNING: Early return.  Marker count too high")
                offset = len(data)
                return offset

            # trace_mf( "Marker Count    : ", marker_count )
            for j in range(0, marker_count):
                if len(data) < (offset + 12):
                    print(
                        "WARNING: Early return.  Out of data at marker ",
                        j,
                        " of ",
                        marker_count,
                    )
                    offset = len(data)
                    return offset
                offset += 12
        return offset

    def __unpack_legacy_other_markers(self, data, packet_size, major, minor):
        offset = 0

        # Markerset count (4 bytes)
        other_marker_count = int.from_bytes(
            data[offset : offset + 4], byteorder="little", signed=True
        )
        offset += 4

        # get data size (4 bytes)
        offset_tmp, unpackedDataSize = self.__unpack_data_size(
            data[offset:], major, minor
        )
        offset += offset_tmp

        if other_marker_count > 0:
            # get legacy_marker positions
            ### legacy_marker_data
            for j in range(0, other_marker_count):
                offset += 12
        return offset

    # Unpack a rigid body object from a data packet
    def __unpack_rigid_body(self, data, major, minor, rb_num):
        offset = 0

        # ID (4 bytes)
        new_id = int.from_bytes(
            data[offset : offset + 4], byteorder="little", signed=True
        )
        offset += 4

        trace_mf("RB: %3.1d ID: %3.1d" % (rb_num, new_id))

        # Position and orientation
        pos = Vector3.unpack(data[offset : offset + 12])
        offset += 12
        trace_mf("\tPosition    : [%3.2f, %3.2f, %3.2f]" % (pos[0], pos[1], pos[2]))

        rot = Quaternion.unpack(data[offset : offset + 16])
        offset += 16
        trace_mf(
            "\tOrientation : [%3.2f, %3.2f, %3.2f, %3.2f]"
            % (rot[0], rot[1], rot[2], rot[3])
        )

        rigid_body = MoCapData.RigidBody(new_id, pos, rot)

        frame_num = frame_number

        # Send information to any listener.
        if self.rigid_body_listener is not None:
            self.rigid_body_listener(new_id, pos, rot, frame_num)

        # RB Marker Data ( Before version 3.0.  After Version 3.0 Marker data is in description )
        if major < 3 and major != 0:
            # Marker count (4 bytes)
            marker_count = int.from_bytes(
                data[offset : offset + 4], byteorder="little", signed=True
            )
            offset += 4
            marker_count_range = range(0, marker_count)
            trace_mf("\tMarker Count:", marker_count)

            rb_marker_list = []
            for i in marker_count_range:
                rb_marker_list.append(MoCapData.RigidBodyMarker())

            # Marker positions
            for i in marker_count_range:
                pos = Vector3.unpack(data[offset : offset + 12])
                offset += 12
                trace_mf("\tMarker", i, ":", pos[0], ",", pos[1], ",", pos[2])
                rb_marker_list[i].pos = pos

            if major >= 2:
                # Marker ID's
                for i in marker_count_range:
                    new_id = int.from_bytes(
                        data[offset : offset + 4], byteorder="little", signed=True
                    )
                    offset += 4
                    trace_mf("\tMarker ID", i, ":", new_id)
                    rb_marker_list[i].id = new_id

                # Marker sizes
                for i in marker_count_range:
                    size = FloatValue.unpack(data[offset : offset + 4])
                    offset += 4
                    trace_mf("\tMarker Size", i, ":", size[0])
                    rb_marker_list[i].size = size

            for i in marker_count_range:
                rigid_body.add_rigid_body_marker(rb_marker_list[i])
        if major >= 2:
            (marker_error,) = FloatValue.unpack(data[offset : offset + 4])
            offset += 4
            trace_mf("\tMean Marker Error: %3.2f" % marker_error)
            rigid_body.error = marker_error

        # Version 2.6 and later
        if ((major == 2) and (minor >= 6)) or major > 2:
            (param,) = struct.unpack("h", data[offset : offset + 2])
            tracking_valid = (param & 0x01) != 0
            offset += 2
            is_valid_str = "False"
            if tracking_valid:
                is_valid_str = "True"
            trace_mf("\tTracking Valid: %s" % is_valid_str)
            if tracking_valid:
                rigid_body.tracking_valid = True
            else:
                rigid_body.tracking_valid = False

        return offset, rigid_body

    def __unpack_rigid_body_data(self, data, packet_size, major, minor):
        rigid_body_data = MoCapData.RigidBodyData()
        offset = 0
        # Rigid body count (4 bytes)
        rigid_body_count = int.from_bytes(
            data[offset : offset + 4], byteorder="little", signed=True
        )
        offset += 4

        # get data size (4 bytes)
        offset_tmp, unpackedDataSize = self.__unpack_data_size(
            data[offset:], major, minor
        )
        offset += offset_tmp

        for i in range(0, rigid_body_count):
            offset_tmp, rigid_body = self.__unpack_rigid_body(
                data[offset:], major, minor, i
            )
            offset += offset_tmp
            rigid_body_data.add_rigid_body(rigid_body)

        # self.rigid_body_id_listener = rigid_body_data.get_id_list()

        return offset, rigid_body_data

    # def __unpack_skeleton_rigid_body( self, data, major, minor, rb_num):
    #     offset = 0

    #     # ID (4 bytes)
    #     offset += 4

    #     # Position and orientation
    #     offset += 12 # pos
    #     offset += 16 # ori

    #     # RB Marker Data ( Before version 3.0.  After Version 3.0 Marker data is in description )
    #     if( major < 3  and major != 0) :
    #         # Marker count (4 bytes)
    #         marker_count = int.from_bytes( data[offset:offset+4], byteorder='little',  signed=True )
    #         offset += 4

    #         # Marker positions
    #         for i in range( 0, marker_count ):
    #             offset += 12

    #         if major >= 2:
    #             # Marker ID's
    #             for i in range( 0, marker_count ):
    #                 offset += 4

    #             # Marker sizes
    #             for i in range( 0, marker_count ):
    #                 offset += 4

    #     if major >= 2 :
    #         offset += 4

    #     # Version 2.6 and later
    #     if ( ( major == 2 ) and ( minor >= 6 ) ) or major > 2 :
    #         offset += 2

    #     return offset

    def __unpack_skeleton_rigid_body(self, data, major, minor, rb_num):
        offset = 0

        # ID (4 bytes)
        new_id = int.from_bytes(
            data[offset : offset + 4], byteorder="little", signed=True
        )
        offset += 4

        trace_mf("RB: %3.1d ID: %3.1d" % (rb_num, new_id))

        # Position and orientation
        pos = Vector3.unpack(data[offset : offset + 12])
        offset += 12
        trace_mf("\tPosition    : [%3.2f, %3.2f, %3.2f]" % (pos[0], pos[1], pos[2]))

        rot = Quaternion.unpack(data[offset : offset + 16])
        offset += 16
        trace_mf(
            "\tOrientation : [%3.2f, %3.2f, %3.2f, %3.2f]"
            % (rot[0], rot[1], rot[2], rot[3])
        )

        rigid_body = MoCapData.RigidBody(new_id, pos, rot)

        # RB Marker Data ( Before version 3.0.  After Version 3.0 Marker data is in description )
        if major < 3 and major != 0:
            # Marker count (4 bytes)
            marker_count = int.from_bytes(
                data[offset : offset + 4], byteorder="little", signed=True
            )
            offset += 4
            marker_count_range = range(0, marker_count)
            trace_mf("\tMarker Count:", marker_count)

            rb_marker_list = []
            for i in marker_count_range:
                rb_marker_list.append(MoCapData.RigidBodyMarker())

            # Marker positions
            for i in marker_count_range:
                pos = Vector3.unpack(data[offset : offset + 12])
                offset += 12
                trace_mf("\tMarker", i, ":", pos[0], ",", pos[1], ",", pos[2])
                rb_marker_list[i].pos = pos

            if major >= 2:
                # Marker ID's
                for i in marker_count_range:
                    new_id = int.from_bytes(
                        data[offset : offset + 4], byteorder="little", signed=True
                    )
                    offset += 4
                    trace_mf("\tMarker ID", i, ":", new_id)
                    rb_marker_list[i].id = new_id

                # Marker sizes
                for i in marker_count_range:
                    size = FloatValue.unpack(data[offset : offset + 4])
                    offset += 4
                    trace_mf("\tMarker Size", i, ":", size[0])
                    rb_marker_list[i].size = size

            for i in marker_count_range:
                rigid_body.add_rigid_body_marker(rb_marker_list[i])
        if major >= 2:
            (marker_error,) = FloatValue.unpack(data[offset : offset + 4])
            offset += 4
            trace_mf("\tMean Marker Error: %3.2f" % marker_error)
            rigid_body.error = marker_error

        # Version 2.6 and later
        if ((major == 2) and (minor >= 6)) or major > 2:
            (param,) = struct.unpack("h", data[offset : offset + 2])
            tracking_valid = (param & 0x01) != 0
            offset += 2
            is_valid_str = "False"
            if tracking_valid:
                is_valid_str = "True"
            trace_mf("\tTracking Valid: %s" % is_valid_str)
            if tracking_valid:
                rigid_body.tracking_valid = True
            else:
                rigid_body.tracking_valid = False

        return offset, rigid_body

    def __unpack_skeleton_rigid_body_data(self, data, packet_size, major, minor):
        rigid_body_data = MoCapData.RigidBodyData()
        offset = 0
        # Rigid body count (4 bytes)
        rigid_body_count = int.from_bytes(
            data[offset : offset + 4], byteorder="little", signed=True
        )
        offset += 4
        trace_mf("Rigid Body Count:", rigid_body_count)

        # get data size (4 bytes)
        offset_tmp, unpackedDataSize = self.__unpack_data_size(
            data[offset:], major, minor
        )
        offset += offset_tmp

        for i in range(0, rigid_body_count):
            offset_tmp, rigid_body = self.__unpack_rigid_body(
                data[offset:], major, minor, i
            )
            offset += offset_tmp
            rigid_body_data.add_rigid_body(rigid_body)

        return offset, rigid_body_data

    # Unpack a skeleton object from a data packet
    # def __unpack_skeleton( self, data, major, minor, skeleton_num=0):
    #     offset = 0
    #     offset += 4

    #     rigid_body_count = int.from_bytes( data[offset:offset+4], byteorder='little',  signed=True )
    #     offset += 4
    #     if(rigid_body_count > 0):
    #         for rb_num in range( 0, rigid_body_count ):
    #             offset_tmp = self.__unpack_skeleton_rigid_body( data[offset:], major, minor, rb_num )
    #             offset+=offset_tmp
    #     return offset

    def __unpack_skeleton(self, data, major, minor, skeleton_num=0):
        offset = 0
        new_id = int.from_bytes(
            data[offset : offset + 4], byteorder="little", signed=True
        )
        offset += 4
        trace_mf("Skeleton %3.1d ID: %3.1d" % (skeleton_num, new_id))
        skeleton = MoCapData.Skeleton(new_id)

        rigid_body_count = int.from_bytes(
            data[offset : offset + 4], byteorder="little", signed=True
        )
        offset += 4
        trace_mf("Rigid Body Count : %3.1d" % rigid_body_count)
        if rigid_body_count > 0:
            for rb_num in range(0, rigid_body_count):
                offset_tmp, rigid_body = self.__unpack_skeleton_rigid_body(
                    data[offset:], major, minor, rb_num
                )
                skeleton.add_rigid_body(rigid_body)
                offset += offset_tmp

        return offset, skeleton

    # def __unpack_skeleton_data( self, data, packet_size, major, minor):
    #     offset = 0
    #     # Version 2.1 and later
    #     skeleton_count = 0
    #     if( ( major == 2 and minor > 0 ) or major > 2 ):
    #         skeleton_count = int.from_bytes( data[offset:offset+4], byteorder='little',  signed=True )
    #         offset += 4

    #         # Get data size (4 bytes)
    #         offset_tmp, unpackedDataSize = self.__unpack_data_size(data[offset:],major, minor)
    #         offset += offset_tmp
    #         if(skeleton_count > 0):
    #             for skeleton_num in range( 0, skeleton_count ):
    #                 rel_offset = self.__unpack_skeleton( data[offset:], major, minor, skeleton_num )
    #                 offset += rel_offset
    #     return offset

    def __unpack_skeleton_data(self, data, packet_size, major, minor):
        skeleton_data = MoCapData.SkeletonData()

        offset = 0
        # Version 2.1 and later
        skeleton_count = 0
        if (major == 2 and minor > 0) or major > 2:
            skeleton_count = int.from_bytes(
                data[offset : offset + 4], byteorder="little", signed=True
            )
            offset += 4
            trace_mf("Skeleton Count:", skeleton_count)

            # Get data size (4 bytes)
            offset_tmp, unpackedDataSize = self.__unpack_data_size(
                data[offset:], major, minor
            )
            offset += offset_tmp
            if skeleton_count > 0:
                for skeleton_num in range(0, skeleton_count):
                    rel_offset, skeleton = self.__unpack_skeleton(
                        data[offset:], major, minor, skeleton_num
                    )
                    offset += rel_offset
                    skeleton_data.add_skeleton(skeleton)

        return offset, skeleton_data

    def __unpack_asset(self, data, major, minor, asset_num=0):
        offset = 0
        offset += 4

        # # of RigidBodies
        numRBs = int.from_bytes(data[offset : offset + 4], "little", signed=True)
        offset += 4

        offset1 = 0
        for rb_num in range(numRBs):
            # # of RigidBodies
            offset1, rigid_body = self.__unpack_asset_rigid_body_data(
                data[offset:], major, minor
            )
            offset += offset1

        # # of Markers
        numMarkers = int.from_bytes(data[offset : offset + 4], "little", signed=True)
        offset += 4

        for marker_num in range(numMarkers):
            # # of Markers
            offset1, marker = self.__unpack_asset_marker_data(
                data[offset:], major, minor
            )
            offset += offset1

        return offset

    def __unpack_asset_data(self, data, packet_size, major, minor):
        offset = 0
        # # Asset Count
        asset_count = int.from_bytes(
            data[offset : offset + 4], byteorder="little", signed=True
        )
        offset += 4

        # Get data size (4 bytes)
        offset_tmp, unpackedDataSize = self.__unpack_data_size(
            data[offset:], major, minor
        )
        offset += offset_tmp

        # Unpack assets
        for asset_num in range(0, asset_count):
            rel_offset, asset = self.__unpack_asset(
                data[offset:], major, minor, asset_num
            )
            offset += rel_offset

        return offset

    def __unpack_labeled_marker_data(self, data, packet_size, major, minor):
        offset = 0
        # # Labeled markers (Version 2.3 and later)
        labeled_marker_count = 0
        if (major == 2 and minor > 3) or major > 2:
            labeled_marker_count = int.from_bytes(
                data[offset : offset + 4], byteorder="little", signed=True
            )
            offset += 4

            # get data size (4 bytes)
            offset_tmp, unpackedDataSize = self.__unpack_data_size(
                data[offset:], major, minor
            )
            offset += offset_tmp

            for lm_num in range(0, labeled_marker_count):
                offset += 4
                offset += 12
                offset += 4

                # Version 2.6 and later
                if (major == 2 and minor >= 6) or major > 2:
                    offset += 2

                # Version 3.0 and later
                if major >= 3:
                    offset += 4

        return offset

    def __unpack_force_plate_data(self, data, packet_size, major, minor):
        n_frames_show_max = 4
        offset = 0
        # Force Plate data (version 2.9 and later)
        force_plate_count = 0
        if (major == 2 and minor >= 9) or major > 2:
            offset += 4

            # get data size (4 bytes)
            offset_tmp, unpackedDataSize = self.__unpack_data_size(
                data[offset:], major, minor
            )
            offset += offset_tmp

            for i in range(0, force_plate_count):
                offset += 4

                # Channel Count
                force_plate_channel_count = int.from_bytes(
                    data[offset : offset + 4], byteorder="little", signed=True
                )
                offset += 4

                # Channel Data
                for j in range(force_plate_channel_count):
                    force_plate_channel_frame_count = int.from_bytes(
                        data[offset : offset + 4], byteorder="little", signed=True
                    )
                    offset += 4

                    # Force plate frames
                    n_frames_show = min(
                        force_plate_channel_frame_count, n_frames_show_max
                    )
                    for k in range(force_plate_channel_frame_count):
                        offset += 4

                        if k < n_frames_show:
                            pass
                    if n_frames_show < force_plate_channel_frame_count:
                        pass
        return offset

    def __unpack_device_data(self, data, packet_size, major, minor):
        n_frames_show_max = 4
        offset = 0
        # Device data (version 2.11 and later)
        device_count = 0
        if (major == 2 and minor >= 11) or (major > 2):
            offset += 4

            # get data size (4 bytes)
            offset_tmp, unpackedDataSize = self.__unpack_data_size(
                data[offset:], major, minor
            )
            offset += offset_tmp

            for i in range(0, device_count):
                offset += 4
                # Channel Count
                device_channel_count = int.from_bytes(
                    data[offset : offset + 4], byteorder="little", signed=True
                )
                offset += 4

                # Channel Data
                for j in range(0, device_channel_count):
                    device_channel_frame_count = int.from_bytes(
                        data[offset : offset + 4], byteorder="little", signed=True
                    )
                    offset += 4

                    # Device Frame Data
                    n_frames_show = min(device_channel_frame_count, n_frames_show_max)
                    for k in range(0, device_channel_frame_count):
                        offset += 4
                        if k < n_frames_show:
                            pass
                    if n_frames_show < device_channel_frame_count:
                        pass
        return offset

    def __unpack_frame_suffix_data(self, data, packet_size, major, minor):
        frame_suffix_data = MoCapData.FrameSuffixData()
        offset = 0

        # Timecode
        timecode = int.from_bytes(
            data[offset : offset + 4], byteorder="little", signed=True
        )
        offset += 4
        frame_suffix_data.timecode = timecode

        timecode_sub = int.from_bytes(
            data[offset : offset + 4], byteorder="little", signed=True
        )
        offset += 4
        frame_suffix_data.timecode_sub = timecode_sub

        param = 0
        # check to see if there is enough data
        if (packet_size - offset) <= 0:
            print("ERROR: Early End of Data Frame Suffix Data")
            print("\tNo time stamp info available")
        else:
            # Timestamp (increased to double precision in 2.7 and later)
            if (major == 2 and minor >= 7) or (major > 2):
                (timestamp,) = DoubleValue.unpack(data[offset : offset + 8])
                offset += 8
            else:
                (timestamp,) = FloatValue.unpack(data[offset : offset + 4])
                offset += 4
            trace_mf("Timestamp : %3.2f" % timestamp)
            frame_suffix_data.timestamp = timestamp

            # Hires Timestamp (Version 3.0 and later)
            if major >= 3:
                stamp_camera_mid_exposure = int.from_bytes(
                    data[offset : offset + 8], byteorder="little", signed=True
                )
                trace_mf(
                    "Mid-exposure timestamp         : %3.1d" % stamp_camera_mid_exposure
                )
                offset += 8
                frame_suffix_data.stamp_camera_mid_exposure = stamp_camera_mid_exposure

                stamp_data_received = int.from_bytes(
                    data[offset : offset + 8], byteorder="little", signed=True
                )
                offset += 8
                frame_suffix_data.stamp_data_received = stamp_data_received
                trace_mf("Camera data received timestamp : %3.1d" % stamp_data_received)

                stamp_transmit = int.from_bytes(
                    data[offset : offset + 8], byteorder="little", signed=True
                )
                offset += 8
                trace_mf("Transmit timestamp             : %3.1d" % stamp_transmit)
                frame_suffix_data.stamp_transmit = stamp_transmit

            # Precision Timestamp (Version 4.1 and later) (defaults as 0 if N/A)
            if major >= 4:
                prec_timestamp_secs = int.from_bytes(
                    data[offset : offset + 4], byteorder="little", signed=True
                )
                # hours = int(prec_timestamp_secs/3600)
                # minutes=int(prec_timestamp_secs/60)%60
                # seconds=prec_timestamp_secs%60
                # out_string="Precision timestamp (h:m:s) - %4.1d:%2.2d:%2.2d"%(hours, minutes, seconds)
                # trace_mf("%s"%out_string)
                trace_mf("Precision timestamp (sec)      : %3.1d" % prec_timestamp_secs)
                offset += 4
                frame_suffix_data.prec_timestamp_secs = prec_timestamp_secs

                prec_timestamp_frac_secs = int.from_bytes(
                    data[offset : offset + 4], byteorder="little", signed=True
                )
                trace_mf(
                    "Precision timestamp (frac sec) : %3.1d" % prec_timestamp_frac_secs
                )
                offset += 4
                frame_suffix_data.prec_timestamp_frac_secs = prec_timestamp_frac_secs

            # Frame parameters
            (param,) = struct.unpack("h", data[offset : offset + 2])
            offset += 2
        is_recording = (param & 0x01) != 0
        tracked_models_changed = (param & 0x02) != 0
        edit_mode = (param & 0x04) != 0
        frame_suffix_data.param = param
        frame_suffix_data.is_recording = is_recording
        frame_suffix_data.tracked_models_changed = tracked_models_changed
        frame_suffix_data.edit_mode = edit_mode

        return offset, frame_suffix_data

    def __unpack_data_size(self, data, major, minor):
        sizeInBytes = 0
        offset = 0

        if ((major == 4) and (minor > 0)) or (major > 4):
            sizeInBytes = int.from_bytes(
                data[offset : offset + 4], byteorder="little", signed=True
            )
            offset += 4
            trace_mf("Byte Count: %3.1d" % sizeInBytes)

        return offset, sizeInBytes

    def __decode_marker_id(self, new_id):
        model_id = 0
        marker_id = 0
        model_id = new_id >> 16
        marker_id = new_id & 0x0000FFFF
        return model_id, marker_id

    # Unpack data from a motion capture frame message
    def __unpack_mocap_data(self, data: bytes, packet_size, major, minor):
        mocap_data = MoCapData.MoCapData()
        data = memoryview(data)
        offset = 0
        rel_offset = 0

        # Frame Prefix Data
        rel_offset, frame_prefix_data = self.__unpack_frame_prefix_data(data[offset:])
        offset += rel_offset
        mocap_data.set_prefix_data(frame_prefix_data)
        frame_number = frame_prefix_data.frame_number

        # Markerset Data
        rel_offset = self.__unpack_marker_set_data(
            data[offset:], (packet_size - offset), major, minor
        )
        offset += rel_offset

        # Legacy Other Markers
        rel_offset = self.__unpack_legacy_other_markers(
            data[offset:], (packet_size - offset), major, minor
        )
        offset += rel_offset

        # Rigid Body Data
        rel_offset, rigid_body_data = self.__unpack_rigid_body_data(
            data[offset:], (packet_size - offset), major, minor
        )
        offset += rel_offset
        mocap_data.set_rigid_body_data(rigid_body_data)
        rigid_body_count = rigid_body_data.get_rigid_body_count()
        # rigid_body_ls = rigid_body_data.rigid_body_list

        # Skeleton Data
        # rel_offset = self.__unpack_skeleton_data(data[offset:], (packet_size - offset),major, minor)
        # offset += rel_offset

        rel_offset, skeleton_data = self.__unpack_skeleton_data(
            data[offset:], (packet_size - offset), major, minor
        )
        offset += rel_offset
        mocap_data.set_skeleton_data(skeleton_data)
        skeleton_count = skeleton_data.get_skeleton_count()
        # skeleton_ls = skeleton_data.skeleton_list

        # Assets ( Motive 3.1/NatNet 4.1 and greater)
        if ((major == 4) and (minor > 0)) or (major > 4):
            rel_offset = self.__unpack_asset_data(
                data[offset:], (packet_size - offset), major, minor
            )
            offset += rel_offset

        # Labeled Marker Data
        rel_offset = self.__unpack_labeled_marker_data(
            data[offset:], (packet_size - offset), major, minor
        )
        offset += rel_offset

        # Force Plate Data
        rel_offset = self.__unpack_force_plate_data(
            data[offset:], (packet_size - offset), major, minor
        )
        offset += rel_offset

        # Device Data
        rel_offset = self.__unpack_device_data(
            data[offset:], (packet_size - offset), major, minor
        )
        offset += rel_offset

        # Frame Suffix Data
        rel_offset, frame_suffix_data = self.__unpack_frame_suffix_data(
            data[offset:], (packet_size - offset), major, minor
        )
        offset += rel_offset
        mocap_data.set_suffix_data(frame_suffix_data)

        timecode = frame_suffix_data.timecode
        timecode_sub = frame_suffix_data.timecode_sub
        timestamp = frame_suffix_data.timestamp
        is_recording = frame_suffix_data.is_recording
        tracked_models_changed = frame_suffix_data.tracked_models_changed
        edit_mode = frame_suffix_data.edit_mode

        # if self.model_changed is not None:
        #     self.model_changed(tracked_models_changed)

        # if self.motive_edit is not None:
        #     self.motive_edit(edit_mode)

        # if self.rb_listener is not None:
        #     rb_dict = {}
        #     rb_dict["frame_number"] = frame_number
        #     rb_dict[ "rb_id"] = rigid_body

        #     self.rb_listener( rb_dict )

        # rb_data = {}
        # for rb in rigid_body_data:
        #     rb_data[rigid_body_ls[i].id_num] = {'pos': rigid_body_ls[i].pos, 'rot': rigid_body_ls[i].rot}

        # ske_data = {}
        # for i in range(skeleton_count):
        #     ske = skeleton_ls[i]
        #     ske_data[ske.id_num] = {}
        #     ske_rb = ske.rigid_body_list
        #     for j in range(len(ske_rb)):
        #         ske_data[ske.id_num][ske_rb[j].id_num] = {'pos': ske_rb[j].pos, 'rot': ske_rb[j].rot}

        # Send information to any listener.
        if self.data_listener is not None:
            data_dict = {}
            data_dict["tracked_models_changed"] = tracked_models_changed
            data_dict["edit_mode"] = edit_mode
            data_dict["frame_number"] = frame_number
            # data_dict[ "rigid_body_count" ] = rigid_body_count
            # data_dict["rb_data"] = rb_data
            # data_dict[ "skeleton_count" ] = skeleton_count
            # data_dict[ "ske_data"] = ske_data
            data_dict["rb_data"] = rigid_body_data.rb_data
            data_dict["ske_data"] = skeleton_data.ske_data
            # print(data_dict)
            self.data_listener(data_dict)

        return offset, mocap_data

    # Unpack a Markerset description packet
    def __unpack_marker_set_description(self, data, major, minor):
        ms_desc = DataDescriptions.MarkerSetDescription()

        offset = 0

        name, separator, remainder = bytes(data[offset:]).partition(b"\0")
        offset += len(name) + 1
        trace_dd("Markerset Name: %s" % (name.decode("utf-8")))
        ms_desc.set_name(name)

        marker_count = int.from_bytes(
            data[offset : offset + 4], byteorder="little", signed=True
        )
        offset += 4
        trace_dd("Marker Count : %3.1d" % marker_count)
        if marker_count > 0:
            for i in range(0, marker_count):
                name, separator, remainder = bytes(data[offset:]).partition(b"\0")
                offset += len(name) + 1
                trace_dd("\t%2.1d Marker Name: %s" % (i, name.decode("utf-8")))
                ms_desc.add_marker_name(name)

        return offset, ms_desc

    # Unpack a rigid body description packet
    def __unpack_rigid_body_description(self, data, major, minor):
        rb_desc = DataDescriptions.RigidBodyDescription()
        offset = 0

        # Version 2.0 or higher
        if (major >= 2) or (major == 0):
            name, separator, remainder = bytes(data[offset:]).partition(b"\0")
            offset += len(name) + 1
            rb_desc.set_name(name)
            trace_dd("\tRigid Body Name   : ", name.decode("utf-8"))

        # ID
        new_id = int.from_bytes(
            data[offset : offset + 4], byteorder="little", signed=True
        )
        offset += 4
        rb_desc.set_id(new_id)
        trace_dd("\tRigid Body ID       : ", str(new_id))

        # Parent ID
        parent_id = int.from_bytes(
            data[offset : offset + 4], byteorder="little", signed=True
        )
        offset += 4
        rb_desc.set_parent_id(parent_id)
        trace_dd("\tParent ID         : ", parent_id)

        # Position Offsets
        pos = Vector3.unpack(data[offset : offset + 12])
        offset += 12
        rb_desc.set_pos(pos[0], pos[1], pos[2])

        trace_dd(
            "\tPosition          : [%3.2f, %3.2f, %3.2f]" % (pos[0], pos[1], pos[2])
        )

        # Version 4.2 and higher, quaternion rotation offset contained in description
        if (major == 4 and minor >= 2) or (major == 0):
            offset += 16
            # trace_dd( "\tRotation          : [%3.2f, %3.2f, %3.2f, %3.2f]"% (quat[0], quat[1], quat[2], quat[3] ))

        # Version 3.0 and higher, rigid body marker information contained in description
        if (major >= 3) or (major == 0):
            # Marker Count
            marker_count = int.from_bytes(
                data[offset : offset + 4], byteorder="little", signed=True
            )
            offset += 4
            trace_dd("\tNumber of Markers : ", marker_count)
            if marker_count > 0:
                trace_dd("\tMarker Positions : ")

            marker_count_range = range(0, marker_count)
            offset1 = offset
            offset2 = offset1 + (12 * marker_count)
            offset3 = offset2 + (4 * marker_count)
            # Marker Offsets X,Y,Z
            marker_name = ""
            for marker in marker_count_range:
                # Offset
                marker_offset = Vector3.unpack(data[offset1 : offset1 + 12])
                offset1 += 12

                # Active Label
                active_label = int.from_bytes(
                    data[offset2 : offset2 + 4], byteorder="little", signed=True
                )
                offset2 += 4

                # Marker Name
                if (major >= 4) or (major == 0):
                    # markername
                    marker_name, separator, remainder = bytes(data[offset3:]).partition(
                        b"\0"
                    )
                    marker_name = marker_name.decode("utf-8")
                    offset3 += len(marker_name) + 1

                rb_marker = DataDescriptions.RBMarker(
                    marker_name, active_label, marker_offset
                )
                rb_desc.add_rb_marker(rb_marker)
                trace_dd(
                    "\t%3.1d Marker Label: %s Position: [ %3.2f %3.2f %3.2f] %s"
                    % (
                        marker,
                        active_label,
                        marker_offset[0],
                        marker_offset[1],
                        marker_offset[2],
                        marker_name,
                    )
                )

            offset = offset3

        trace_dd("\tunpack_rigid_body_description processed bytes: ", offset)
        return offset, rb_desc

    # Unpack a skeleton description packet
    def __unpack_skeleton_description(self, data, major, minor):
        skeleton_desc = DataDescriptions.SkeletonDescription()
        offset = 0

        # Name
        name, separator, remainder = bytes(data[offset:]).partition(b"\0")
        offset += len(name) + 1
        skeleton_desc.set_name(name)
        trace_dd("Name : %s" % name.decode("utf-8"))

        # ID
        new_id = int.from_bytes(
            data[offset : offset + 4], byteorder="little", signed=True
        )
        offset += 4
        skeleton_desc.set_id(new_id)
        trace_dd("ID : %3.1d" % new_id)

        # # of RigidBodies
        rigid_body_count = int.from_bytes(
            data[offset : offset + 4], byteorder="little", signed=True
        )
        offset += 4
        trace_dd("Rigid Body (Bone) Count : %3.1d" % rigid_body_count)

        # Loop over all Rigid Bodies
        for i in range(0, rigid_body_count):
            trace_dd("Rigid Body (Bone) %d:" % (i))
            offset_tmp, rb_desc_tmp = self.__unpack_rigid_body_description(
                data[offset:], major, minor
            )
            offset += offset_tmp
            skeleton_desc.add_rigid_body_description(rb_desc_tmp)
        return offset, skeleton_desc

    def __unpack_force_plate_description(self, data, major, minor):
        fp_desc = None
        offset = 0
        if major >= 3:
            fp_desc = DataDescriptions.ForcePlateDescription()
            # ID
            new_id = int.from_bytes(
                data[offset : offset + 4], byteorder="little", signed=True
            )
            offset += 4
            fp_desc.set_id(new_id)
            trace_dd("\tID : ", str(new_id))

            # Serial Number
            serial_number, separator, remainder = bytes(data[offset:]).partition(b"\0")
            offset += len(serial_number) + 1
            fp_desc.set_serial_number(serial_number)
            trace_dd("\tSerial Number : ", serial_number.decode("utf-8"))

            # Dimensions
            f_width = FloatValue.unpack(data[offset : offset + 4])
            offset += 4
            trace_dd("\tWidth  : %3.2f" % f_width)
            f_length = FloatValue.unpack(data[offset : offset + 4])
            offset += 4
            fp_desc.set_dimensions(f_width[0], f_length[0])
            trace_dd("\tLength : %3.2f" % f_length)

            # Origin
            origin = Vector3.unpack(data[offset : offset + 12])
            offset += 12
            fp_desc.set_origin(origin[0], origin[1], origin[2])
            trace_dd(
                "\tOrigin : [%3.2f, %3.2f, %3.2f]" % (origin[0], origin[1], origin[2])
            )

            # Calibration Matrix 12x12 floats
            trace_dd("Cal Matrix:")
            cal_matrix_tmp = [[0.0 for col in range(12)] for row in range(12)]

            for i in range(0, 12):
                cal_matrix_row = FPCalMatrixRow.unpack(data[offset : offset + (12 * 4)])
                trace_dd(
                    "\t%3.1d %3.3e %3.3e %3.3e %3.3e %3.3e %3.3e %3.3e %3.3e \
                         %3.3e %3.3e %3.3e %3.3e"
                    % (
                        i,
                        cal_matrix_row[0],
                        cal_matrix_row[1],
                        cal_matrix_row[2],
                        cal_matrix_row[3],
                        cal_matrix_row[4],
                        cal_matrix_row[5],
                        cal_matrix_row[6],
                        cal_matrix_row[7],
                        cal_matrix_row[8],
                        cal_matrix_row[9],
                        cal_matrix_row[10],
                        cal_matrix_row[11],
                    )
                )
                cal_matrix_tmp[i] = copy.deepcopy(cal_matrix_row)
                offset += 12 * 4
            fp_desc.set_cal_matrix(cal_matrix_tmp)
            # Corners 4x3 floats
            corners = FPCorners.unpack(data[offset : offset + (12 * 4)])
            offset += 12 * 4
            o_2 = 0
            trace_dd("Corners:")
            corners_tmp = [[0.0 for col in range(3)] for row in range(4)]
            for i in range(0, 4):
                trace_dd(
                    "\t%3.1d %3.3e %3.3e %3.3e"
                    % (i, corners[o_2], corners[o_2 + 1], corners[o_2 + 2])
                )
                corners_tmp[i][0] = corners[o_2]
                corners_tmp[i][1] = corners[o_2 + 1]
                corners_tmp[i][2] = corners[o_2 + 2]
                o_2 += 3
            fp_desc.set_corners(corners_tmp)

            # Plate Type int
            plate_type = int.from_bytes(
                data[offset : offset + 4], byteorder="little", signed=True
            )
            offset += 4
            fp_desc.set_plate_type(plate_type)
            trace_dd("Plate Type : ", plate_type)

            # Channel Data Type int
            channel_data_type = int.from_bytes(
                data[offset : offset + 4], byteorder="little", signed=True
            )
            offset += 4
            fp_desc.set_channel_data_type(channel_data_type)
            trace_dd("Channel Data Type : ", channel_data_type)

            # Number of Channels int
            num_channels = int.from_bytes(
                data[offset : offset + 4], byteorder="little", signed=True
            )
            offset += 4
            trace_dd("Number of Channels : ", num_channels)

            # Channel Names list of NoC strings
            for i in range(0, num_channels):
                channel_name, separator, remainder = bytes(data[offset:]).partition(
                    b"\0"
                )
                offset += len(channel_name) + 1
                trace_dd("\tChannel Name %3.1d: %s" % (i, channel_name.decode("utf-8")))
                fp_desc.add_channel_name(channel_name)

        trace_dd("unpackForcePlate processed ", offset, " bytes")
        return offset, fp_desc

    def __unpack_device_description(self, data, major, minor):
        device_desc = None
        offset = 0
        if major >= 3:
            # new_id
            new_id = int.from_bytes(
                data[offset : offset + 4], byteorder="little", signed=True
            )
            offset += 4
            trace_dd("\tID : ", str(new_id))

            # Name
            name, separator, remainder = bytes(data[offset:]).partition(b"\0")
            offset += len(name) + 1
            trace_dd("\tName : ", name.decode("utf-8"))

            # Serial Number
            serial_number, separator, remainder = bytes(data[offset:]).partition(b"\0")
            offset += len(serial_number) + 1
            trace_dd("\tSerial Number : ", serial_number.decode("utf-8"))

            # Device Type int
            device_type = int.from_bytes(
                data[offset : offset + 4], byteorder="little", signed=True
            )
            offset += 4
            trace_dd("Device Type : ", device_type)

            # Channel Data Type int
            channel_data_type = int.from_bytes(
                data[offset : offset + 4], byteorder="little", signed=True
            )
            offset += 4
            trace_dd("Channel Data Type : ", channel_data_type)

            device_desc = DataDescriptions.DeviceDescription(
                new_id, name, serial_number, device_type, channel_data_type
            )

            # Number of Channels int
            num_channels = int.from_bytes(
                data[offset : offset + 4], byteorder="little", signed=True
            )
            offset += 4
            trace_dd("Number of Channels ", num_channels)

            # Channel Names list of NoC strings
            for i in range(0, num_channels):
                channel_name, separator, remainder = bytes(data[offset:]).partition(
                    b"\0"
                )
                offset += len(channel_name) + 1
                device_desc.add_channel_name(channel_name)
                trace_dd("\tChannel ", i, " Name : ", channel_name.decode("utf-8"))

        trace_dd("unpack_device_description processed ", offset, " bytes")
        return offset, device_desc

    def __unpack_camera_description(self, data, major, minor):
        offset = 0
        # Name
        name, separator, remainder = bytes(data[offset:]).partition(b"\0")
        offset += len(name) + 1
        trace_dd("\tName       : %s" % name.decode("utf-8"))
        # Position
        position = Vector3.unpack(data[offset : offset + 12])
        offset += 12
        trace_dd(
            "\tPosition   : [%3.2f, %3.2f, %3.2f]"
            % (position[0], position[1], position[2])
        )

        # Orientation
        orientation = Quaternion.unpack(data[offset : offset + 16])
        offset += 16
        trace_dd(
            "\tOrientation: [%3.2f, %3.2f, %3.2f, %3.2f]"
            % (orientation[0], orientation[1], orientation[2], orientation[3])
        )
        trace_dd("unpack_camera_description processed %3.1d bytes" % offset)

        camera_desc = DataDescriptions.CameraDescription(name, position, orientation)
        return offset, camera_desc

    def __unpack_marker_description(self, data, major, minor):
        offset = 0

        # Name
        name, separator, remainder = bytes(data[offset:]).partition(b"\0")
        offset += len(name) + 1
        trace_dd("\tName       : %s" % name.decode("utf-8"))

        # ID
        marker_id = int.from_bytes(
            data[offset : offset + 4], byteorder="little", signed=True
        )
        offset += 4
        trace_dd("\tID         : %d" % (marker_id))

        # Initial Position
        initialPosition = Vector3.unpack(data[offset : offset + 12])
        offset += 12
        trace_dd(
            "\tPosition   : [%3.2f, %3.2f, %3.2f]"
            % (initialPosition[0], initialPosition[1], initialPosition[2])
        )

        # Size
        marker_size = FloatValue.unpack(data[offset : offset + 4])
        offset += 4
        trace_mf("\tMarker Size:", marker_size)

        # Params
        (marker_params,) = struct.unpack("h", data[offset : offset + 2])
        offset += 2
        trace_mf("\tParams     :", marker_params)

        trace_dd("\tunpack_marker_description processed %3.1d bytes" % offset)

        # Package for return object
        marker_desc = DataDescriptions.MarkerDescription(
            name, marker_id, initialPosition, marker_size, marker_params
        )
        return offset, marker_desc

    def __unpack_asset_rigid_body_data(self, data, major, minor):
        offset = 0
        # ID
        rbID = int.from_bytes(data[offset : offset + 4], "little", signed=True)
        offset += 4
        trace_dd("\tID         : %d" % (rbID))

        # Position: x,y,z
        pos = Vector3.unpack(data[offset : offset + 12])
        offset += 12
        trace_mf("\tPosition    : [%3.2f, %3.2f, %3.2f]" % (pos[0], pos[1], pos[2]))

        # Orientation: qx, qy, qz, qw
        rot = Quaternion.unpack(data[offset : offset + 16])
        offset += 16
        trace_mf(
            "\tOrientation : [%3.2f, %3.2f, %3.2f, %3.2f]"
            % (rot[0], rot[1], rot[2], rot[3])
        )

        # Mean error
        (mean_error,) = FloatValue.unpack(data[offset : offset + 4])
        offset += 4
        trace_mf("\tMean Error  : %3.2f" % mean_error)

        # Params
        (marker_params,) = struct.unpack("h", data[offset : offset + 2])
        offset += 2
        trace_mf("\tParams      :", marker_params)

        trace_dd("unpack_marker_description processed %3.1d bytes" % offset)

        # Package for return object
        rigid_body_data = MoCapData.AssetRigidBodyData(
            rbID, pos, rot, mean_error, marker_params
        )

        return offset, rigid_body_data

    def __unpack_asset_marker_data(self, data, major, minor):
        offset = 0
        # ID
        marker_id = int.from_bytes(data[offset : offset + 4], "little", signed=True)
        offset += 4
        trace_dd("\tID          : %d" % (marker_id))

        # Position: x,y,z
        pos = Vector3.unpack(data[offset : offset + 12])
        offset += 12
        trace_mf("\tPosition    : [%3.2f, %3.2f, %3.2f]" % (pos[0], pos[1], pos[2]))

        # Size
        (marker_size,) = FloatValue.unpack(data[offset : offset + 4])
        offset += 4
        trace_mf("\tMarker Size : %3.2f" % marker_size)

        # Params
        (marker_params,) = struct.unpack("h", data[offset : offset + 2])
        offset += 2
        trace_mf("\tParams      :", marker_params)

        # Residual
        (residual,) = FloatValue.unpack(data[offset : offset + 4])
        offset += 4
        trace_mf("\tResidual    : %3.2f" % residual)

        marker_data = MoCapData.AssetMarkerData(
            marker_id, pos, marker_size, marker_params, residual
        )
        return offset, marker_data

    def __unpack_asset_description(self, data, major, minor):
        offset = 0

        # Name
        name, separator, remainder = bytes(data[offset:]).partition(b"\0")
        offset += len(name) + 1
        trace_dd("\tName       : %s" % name.decode("utf-8"))

        # Asset Type 4 bytes
        assetType = int.from_bytes(
            data[offset : offset + 4], byteorder="little", signed=True
        )
        offset += 4
        trace_dd("\tType       : %d" % (assetType))

        # ID 4 bytes
        assetID = int.from_bytes(
            data[offset : offset + 4], byteorder="little", signed=True
        )
        offset += 4
        trace_dd("\tID         : %d" % (assetID))

        # # of RigidBodies
        numRBs = int.from_bytes(
            data[offset : offset + 4], byteorder="little", signed=True
        )
        offset += 4
        trace_dd("\tRigid Body (Bone) Count : %d" % (numRBs))

        rigidbodyArray = []
        offset1 = 0
        for rbNum in range(numRBs):
            # # of RigidBodies
            trace_dd("\tRigid Body (Bone) %d:" % (rbNum))
            offset1, rigidbody = self.__unpack_rigid_body_description(
                data[offset:], major, minor
            )
            offset += offset1
            rigidbodyArray.append(rigidbody)

        # # of Markers
        numMarkers = int.from_bytes(
            data[offset : offset + 4], byteorder="little", signed=True
        )
        offset += 4
        trace_dd("\tMarker Count: %d" % (numMarkers))

        markerArray = []
        for markerNum in range(numMarkers):
            # # of Markers
            trace_dd("\tMarker %d:" % (markerNum))
            offset1, marker = self.__unpack_marker_description(
                data[offset:], major, minor
            )
            offset += offset1
            markerArray.append(marker)

        trace_dd("\tunpack_asset_description processed %3.1d bytes" % offset)

        # package for output
        asset_desc = DataDescriptions.AssetDescription(
            name, assetType, assetID, rigidbodyArray, markerArray
        )
        return offset, asset_desc

    # Unpack a data description packet
    def __unpack_data_descriptions(self, data: bytes, packet_size, major, minor):
        data_descs = DataDescriptions.DataDescriptions()
        offset = 0
        # # of data sets to process
        dataset_count = int.from_bytes(
            data[offset : offset + 4], byteorder="little", signed=True
        )
        offset += 4
        trace_dd("Dataset Count : ", str(dataset_count))
        for i in range(0, dataset_count):
            trace_dd("Dataset ", str(i))
            data_type = int.from_bytes(
                data[offset : offset + 4], byteorder="little", signed=True
            )
            offset += 4
            if ((major == 4) and (minor >= 1)) or (major > 4):
                size_in_bytes = int.from_bytes(
                    data[offset : offset + 4], byteorder="little", signed=True
                )
                offset += 4
            data_tmp = None
            if data_type == 0:
                trace_dd("Type: 0 Markerset")
                offset_tmp, data_tmp = self.__unpack_marker_set_description(
                    data[offset:], major, minor
                )
            elif data_type == 1:
                trace_dd("Type: 1 Rigid Body")
                offset_tmp, data_tmp = self.__unpack_rigid_body_description(
                    data[offset:], major, minor
                )
            elif data_type == 2:
                trace_dd("Type: 2 Skeleton")
                offset_tmp, data_tmp = self.__unpack_skeleton_description(
                    data[offset:], major, minor
                )
            elif data_type == 3:
                trace_dd("Type: 3 Force Plate")
                offset_tmp, data_tmp = self.__unpack_force_plate_description(
                    data[offset:], major, minor
                )
            elif data_type == 4:
                trace_dd("Type: 4 Device")
                offset_tmp, data_tmp = self.__unpack_device_description(
                    data[offset:], major, minor
                )
            elif data_type == 5:
                trace_dd("Type: 5 Camera")
                offset_tmp, data_tmp = self.__unpack_camera_description(
                    data[offset:], major, minor
                )
            elif data_type == 6:
                trace_dd("Type: 6 Asset")
                offset_tmp, data_tmp = self.__unpack_asset_description(
                    data[offset:], major, minor
                )
            else:
                print("Type: Unknown " + str(data_type))
                print("ERROR: Type decode failure")
                print(
                    "\t" + str(i + 1) + " datasets processed of " + str(dataset_count)
                )
                print("\t " + str(offset) + " bytes processed of " + str(packet_size))
                print("\tPACKET DECODE STOPPED")
                return offset
            offset += offset_tmp
            data_descs.add_data(data_tmp)
            trace_dd("\t" + str(i + 1) + " datasets processed of " + str(dataset_count))
            trace_dd("\t " + str(offset) + " bytes processed of " + str(packet_size))

        return offset, data_descs

    # __unpack_server_info is for local use of the client
    # and will update the values for the versions/ NatNet capabilities
    # of the server.
    def __unpack_server_info(self, data, packet_size, major, minor):
        offset = 0
        # Server name
        # szName = data[offset: offset+256]
        self.__application_name, separator, remainder = bytes(
            data[offset : offset + 256]
        ).partition(b"\0")
        self.__application_name = str(self.__application_name, "utf-8")
        offset += 256
        # Server Version info
        server_version = struct.unpack("BBBB", data[offset : offset + 4])
        offset += 4
        self.__server_version[0] = server_version[0]
        self.__server_version[1] = server_version[1]
        self.__server_version[2] = server_version[2]
        self.__server_version[3] = server_version[3]

        # NatNet Version info
        nnsvs = struct.unpack("BBBB", data[offset : offset + 4])
        offset += 4
        self.__nat_net_stream_version_server[0] = nnsvs[0]
        self.__nat_net_stream_version_server[1] = nnsvs[1]
        self.__nat_net_stream_version_server[2] = nnsvs[2]
        self.__nat_net_stream_version_server[3] = nnsvs[3]
        if (self.__nat_net_requested_version[0] == 0) and (
            self.__nat_net_requested_version[1] == 0
        ):
            # print("resetting requested version to %d %d %d %d from %d %d %d %d"%(
            #     self.__nat_net_stream_version_server[0],
            #     self.__nat_net_stream_version_server[1],
            #     self.__nat_net_stream_version_server[2],
            #     self.__nat_net_stream_version_server[3],
            #     self.__nat_net_requested_version[0],
            #     self.__nat_net_requested_version[1],
            #     self.__nat_net_requested_version[2],
            #     self.__nat_net_requested_version[3]))

            self.__nat_net_requested_version[0] = self.__nat_net_stream_version_server[
                0
            ]
            self.__nat_net_requested_version[1] = self.__nat_net_stream_version_server[
                1
            ]
            self.__nat_net_requested_version[2] = self.__nat_net_stream_version_server[
                2
            ]
            self.__nat_net_requested_version[3] = self.__nat_net_stream_version_server[
                3
            ]
            # Determine if the bitstream version can be changed
            if (self.__nat_net_stream_version_server[0] >= 4) and (
                self.use_multicast == False
            ):
                self.__can_change_bitstream_version = True

        trace_mf("Sending Application Name: ", self.__application_name)
        trace_mf(
            "NatNetVersion ",
            str(self.__nat_net_stream_version_server[0]),
            " ",
            str(self.__nat_net_stream_version_server[1]),
            " ",
            str(self.__nat_net_stream_version_server[2]),
            " ",
            str(self.__nat_net_stream_version_server[3]),
        )

        trace_mf(
            "ServerVersion ",
            str(self.__server_version[0]),
            " ",
            str(self.__server_version[1]),
            " ",
            str(self.__server_version[2]),
            " ",
            str(self.__server_version[3]),
        )
        return offset

    # __unpack_bitstream_info is for local use of the client
    # and will update the values for the current bitstream
    # of the server.

    def __unpack_bitstream_info(self, data, packet_size, major, minor):
        nn_version = []
        inString = data.decode("utf-8")
        messageList = inString.split(",")
        if len(messageList) > 1:
            if messageList[0] == "Bitstream":
                nn_version = messageList[1].split(".")
        return nn_version

    def __command_thread_function(
        self, in_socket, stop, gprint_level, msg_id, desc_dict
    ):
        message_id_dict = {}
        if not self.use_multicast:
            in_socket.settimeout(2.0)
        data = bytearray(0)
        # 64k buffer size
        recv_buffer_size = 64 * 1024
        while not stop():
            # Block for input
            try:
                data, addr = in_socket.recvfrom(recv_buffer_size)
            except socket.error as msg:
                if stop():
                    # print("ERROR: command socket access error occurred:\n  %s" %msg)
                    # return 1
                    print("shutting down")
            except socket.herror:
                print("ERROR: command socket access herror occurred")
                return 2
            except socket.gaierror:
                print("ERROR: command socket access gaierror occurred")
                return 3
            except socket.timeout:
                if self.use_multicast:
                    print(
                        "ERROR: command socket access timeout occurred. Server not responding"
                    )
                    # return 4

            if len(data) > 0:
                # peek ahead at message_id
                message_id = get_message_id(data)
                tmp_str = "mi_%1.1d" % message_id
                if tmp_str not in message_id_dict:
                    message_id_dict[tmp_str] = 0
                message_id_dict[tmp_str] += 1

                print_level = gprint_level()
                if message_id == self.NAT_FRAMEOFDATA:
                    if print_level > 0:
                        if (message_id_dict[tmp_str] % print_level) == 0:
                            print_level = 1
                        else:
                            print_level = 0
                # print("command_thread_function")
                message_id, dict_temp = self.__process_message(data, print_level)

                if dict_temp is not None:
                    self.desc_dict = dict_temp

                # self.command_ready_event.set()
                data = bytearray(0)

            if not self.use_multicast:
                if not stop():
                    self.send_keep_alive(
                        in_socket, self.server_ip_address, self.command_port
                    )
        return 0

    def __data_thread_function(self, in_socket, stop, gprint_level):
        message_id_dict = {}
        data = bytearray(0)
        # 64k buffer size
        recv_buffer_size = 64 * 1024

        while not stop():
            # Block for input
            try:
                data, addr = in_socket.recvfrom(recv_buffer_size)
            except socket.error as msg:
                if not stop():
                    print("ERROR: data socket access error occurred:\n  %s" % msg)
                    return 1
            except socket.herror:
                print("ERROR: data socket access herror occurred")
                # return 2
            except socket.gaierror:
                print("ERROR: data socket access gaierror occurred")
                # return 3
            except socket.timeout:
                # if self.use_multicast:
                print(
                    "ERROR: data socket access timeout occurred. Server not responding"
                )
                # return 4
            if len(data) > 0:
                # peek ahead at message_id
                message_id = get_message_id(data)
                tmp_str = "mi_%1.1d" % message_id
                if tmp_str not in message_id_dict:
                    message_id_dict[tmp_str] = 0
                message_id_dict[tmp_str] += 1

                print_level = gprint_level()
                if message_id == self.NAT_FRAMEOFDATA:
                    if print_level > 0:
                        if (message_id_dict[tmp_str] % print_level) == 0:
                            print_level = 1
                        else:
                            print_level = 0
                message_id, dict_temp = self.__process_message(data, print_level)

                data = bytearray(0)
        return 0

    def __process_message(self, data: bytes, print_level=0):
        # print("process_message")
        # return message ID
        major = self.get_major()
        minor = self.get_minor()
        desc_dict = None

        trace("Begin Packet\n-----------------")
        show_nat_net_version = False
        if show_nat_net_version:
            trace(
                "NatNetVersion ",
                str(self.__nat_net_requested_version[0]),
                " ",
                str(self.__nat_net_requested_version[1]),
                " ",
                str(self.__nat_net_requested_version[2]),
                " ",
                str(self.__nat_net_requested_version[3]),
            )

        message_id = get_message_id(data)

        packet_size = int.from_bytes(data[2:4], byteorder="little", signed=True)

        # skip the 4 bytes for message ID and packet_size
        offset = 4
        if message_id == self.NAT_FRAMEOFDATA:
            trace("Message ID  : %3.1d NAT_FRAMEOFDATA" % message_id)
            trace("Packet Size : ", packet_size)

            offset_tmp, mocap_data = self.__unpack_mocap_data(
                data[offset:], packet_size, major, minor
            )
            offset += offset_tmp
            # print("MoCap Frame: %d\n"%(mocap_data.prefix_data.frame_number))
            # get a string version of the data for output
            mocap_data_str = mocap_data.get_as_string()
            if print_level == 0:
                print("%s\n" % mocap_data_str)

        elif message_id == self.NAT_MODELDEF:
            # global rigid_body_dict
            trace("Message ID  : %3.1d NAT_MODELDEF" % message_id)
            trace("Packet Size : %d" % packet_size)
            offset_tmp, data_descs = self.__unpack_data_descriptions(
                data[offset:], packet_size, major, minor
            )
            offset += offset_tmp

            desc_dict = {}

            desc_dict["rb_desc"] = {}
            for rigid_body in data_descs.rigid_body_list:
                desc_dict["rb_desc"][rigid_body.id_num] = {
                    "name": DataDescriptions.get_as_string(rigid_body.sz_name)
                }

            desc_dict["ske_desc"] = {}
            for skeleton in data_descs.skeleton_list:

                skeleton_bones: dict[int, BoneData] = {
                    0: BoneData(
                        bone_id=0,
                        bone_name="Root",
                        t_pose_head=mathutils.Vector(),
                        parent=None,
                    )
                }

                skeleton_name = DataDescriptions.get_as_string(skeleton.name)

                ske_name_len = len(DataDescriptions.get_as_string(skeleton.name))
                desc_dict["ske_desc"][skeleton.id_num] = {}
                desc_dict["ske_desc"][skeleton.id_num]["name"] = (
                    DataDescriptions.get_as_string(skeleton.name)
                )
                desc_dict["ske_desc"][skeleton.id_num]["rb_id"] = {}
                desc_dict["ske_desc"][skeleton.id_num]["rb_name"] = {}
                for rigid_body in skeleton.rigid_body_description_list:
                    desc_dict["ske_desc"][skeleton.id_num]["rb_id"][
                        rigid_body.id_num
                    ] = {
                        "name": DataDescriptions.get_as_string(rigid_body.sz_name)[
                            ske_name_len + 1 :
                        ],
                        "pos": rigid_body.pos,
                        "parent_id": rigid_body.parent_id,
                    }
                    desc_dict["ske_desc"][skeleton.id_num]["rb_name"][
                        DataDescriptions.get_as_string(rigid_body.sz_name)[
                            ske_name_len + 1 :
                        ]
                    ] = {
                        "id": rigid_body.id_num,
                        "pos": rigid_body.pos,
                        "parent_id": rigid_body.parent_id,
                    }

                    bone_name = DataDescriptions.get_as_string(rigid_body.sz_name)[
                        ske_name_len + 1 :
                    ]

                    parent_bone_data = skeleton_bones.get(
                        rigid_body.parent_id, skeleton_bones[0]
                    )

                    bone_data = BoneData(
                        bone_id=rigid_body.id_num,
                        bone_name=bone_name,
                        t_pose_head=mathutils.Vector(rigid_body.pos),
                        parent=parent_bone_data,
                    )

                    skeleton_bones[rigid_body.id_num] = bone_data

                skeleton_data = SkeletonData.create_skeleton(
                    skeleton_id=skeleton.id_num,
                    skeleton_name=skeleton_name,
                    bones=skeleton_bones,
                )

                SkeletonRepository.append_skeleton(skeleton=skeleton_data)

        elif message_id == self.NAT_SERVERINFO:
            trace("Message ID  : %3.1d NAT_SERVERINFO" % message_id)
            trace("Packet Size : ", packet_size)
            offset += self.__unpack_server_info(
                data[offset:], packet_size, major, minor
            )

        elif message_id == self.NAT_RESPONSE:
            trace("Message ID  : %3.1d NAT_RESPONSE" % message_id)
            trace("Packet Size : ", packet_size)
            if packet_size == 4:
                command_response = int.from_bytes(
                    data[offset : offset + 4], byteorder="little", signed=True
                )
                trace(
                    "Command response: %d - %d %d %d %d"
                    % (
                        command_response,
                        data[offset],
                        data[offset + 1],
                        data[offset + 2],
                        data[offset + 3],
                    )
                )
                offset += 4
            else:
                show_remainder = False
                message, separator, remainder = bytes(data[offset:]).partition(b"\0")
                if len(message) < 30:
                    tmpString = message.decode("utf-8")
                    # Decode bitstream version
                    if tmpString.startswith("Bitstream"):
                        nn_version = self.__unpack_bitstream_info(
                            data[offset:], packet_size, major, minor
                        )
                        # This is the current server version
                        if len(nn_version) > 1:
                            for i in range(len(nn_version)):
                                self.__nat_net_stream_version_server[i] = int(
                                    nn_version[i]
                                )
                            for i in range(len(nn_version), 4):
                                self.__nat_net_stream_version_server[i] = 0

                offset += len(message) + 1

                if show_remainder:
                    trace(
                        "Command response:",
                        message.decode("utf-8"),
                        " separator:",
                        separator,
                        " remainder:",
                        remainder,
                    )
                else:
                    trace("Command response:", message.decode("utf-8"))
        elif message_id == self.NAT_UNRECOGNIZED_REQUEST:
            trace("Message ID  : %3.1d NAT_UNRECOGNIZED_REQUEST: " % message_id)
            trace("Packet Size : ", packet_size)
            trace("Received 'Unrecognized request' from server")
        elif message_id == self.NAT_MESSAGESTRING:
            trace("Message ID  : %3.1d NAT_MESSAGESTRING" % message_id)
            trace("Packet Size : ", packet_size)
            message, separator, remainder = bytes(data[offset:]).partition(b"\0")
            offset += len(message) + 1
            trace("Received message from server:", message.decode("utf-8"))
        else:
            trace("Message ID  : %3.1d UNKNOWN" % message_id)
            trace("Packet Size : ", packet_size)
            trace("ERROR: Unrecognized packet type")

        trace("End Packet\n-----------------")
        return message_id, desc_dict  # rigid_body_dict

    def send_request(self, in_socket, command, command_str, address):
        # Compose the message in our known message format
        packet_size = 0
        if (
            command == self.NAT_REQUEST_MODELDEF
            or command == self.NAT_REQUEST_FRAMEOFDATA
        ):
            # print("send_request")
            packet_size = 0
            command_str = ""
        elif command == self.NAT_REQUEST:
            packet_size = len(command_str) + 1
        elif command == self.NAT_CONNECT:
            tmp_version = [4, 1, 0, 0]
            # print("NAT_CONNECT to Motive with %d %d %d %d\n"%(
            #     tmp_version[0],
            #     tmp_version[1],
            #     tmp_version[2],
            #     tmp_version[3]
            # ))
            # allocate a byte array for 270 bytes
            # to connect with a specific version
            # The first 4 bytes spell out "Ping"
            command_str = []
            command_str = [0 for i in range(270)]
            command_str[0] = 80
            command_str[1] = 105
            command_str[2] = 110
            command_str[3] = 103
            command_str[264] = 0
            command_str[265] = tmp_version[0]
            command_str[266] = tmp_version[1]
            command_str[267] = tmp_version[2]
            command_str[268] = tmp_version[3]
            packet_size = len(command_str) + 1
        elif command == self.NAT_KEEPALIVE:
            packet_size = 0
            command_str = ""

        data = command.to_bytes(2, byteorder="little", signed=True)
        data += packet_size.to_bytes(2, byteorder="little", signed=True)

        if command == self.NAT_CONNECT:
            data += bytearray(command_str)
        else:
            data += command_str.encode("utf-8")
        data += b"\0"

        return in_socket.sendto(data, address)

    def send_command(self, command_str):
        # print("Send command %s"%command_str)
        nTries = 3
        ret_val = -1
        while nTries:
            nTries -= 1
            ret_val = self.send_request(
                self.command_socket,
                self.NAT_REQUEST,
                command_str,
                (self.server_ip_address, self.command_port),
            )
            if ret_val != -1:
                break
        return ret_val

        # return self.send_request(self.data_socket,    self.NAT_REQUEST, command_str,  \
        # (self.server_ip_address, self.command_port) )

    def send_modeldef_command(self):
        # print("Send command %s"%command_str)
        nTries = 3
        ret_val = -1
        while nTries:
            nTries -= 1
            ret_val = self.send_request(
                self.command_socket,
                self.NAT_REQUEST_MODELDEF,
                "",
                (self.server_ip_address, self.command_port),
            )
            if ret_val != -1:
                break
        return ret_val

    def send_commands(self, tmpCommands, print_results: bool = True):
        for sz_command in tmpCommands:
            return_code = self.send_command(sz_command)
            if print_results:
                print("Command: %s - return_code: %d" % (sz_command, return_code))

    def send_keep_alive(self, in_socket, server_ip_address, server_port):
        return self.send_request(
            in_socket, self.NAT_KEEPALIVE, "", (server_ip_address, server_port)
        )

    def get_command_port(self):
        return self.command_port

    def refresh_configuration(self):
        # query for application configuration
        # print("Request current configuration")
        sz_command = "Bitstream"
        return_code = self.send_command(sz_command)
        time.sleep(0.5)

    def get_application_name(self):
        return self.__application_name

    def get_nat_net_requested_version(self):
        return self.__nat_net_requested_version

    def get_nat_net_version_server(self):
        return self.__nat_net_stream_version_server

    def get_server_version(self):
        return self.__server_version

    def run(self):
        # Create the data socket
        self.data_socket = self.__create_data_socket(self.data_port)
        if self.data_socket is None:
            print("Could not open data channel")
            return False

        # Create the command socket
        self.command_socket = self.__create_command_socket()
        if self.command_socket is None:
            print("Could not open command channel")
            return False
        self.__is_locked = True

        self.stop_threads = False

        self.msg_id = 1
        # self.desc_dict_updated = False
        self.desc_dict = {}

        # Create a separate thread for receiving data packets
        self.data_thread = Thread(
            target=self.__data_thread_function,
            args=(
                self.data_socket,
                lambda: self.stop_threads,
                lambda: self.print_level,
            ),
        )
        self.data_thread.start()

        # Create a separate thread for receiving command packets
        self.command_thread = Thread(
            target=self.__command_thread_function,
            args=(
                self.command_socket,
                lambda: self.stop_threads,
                lambda: self.print_level,
                lambda: self.msg_id,
                lambda: self.desc_dict,
            ),
        )
        self.command_thread.start()

        # Required for setup
        # Get NatNet and server versions
        self.send_request(
            self.command_socket,
            self.NAT_CONNECT,
            "",
            (self.server_ip_address, self.command_port),
        )
        return True

    def shutdown(self):
        # print("shutdown called")
        self.stop_threads = True
        # closing sockets causes blocking recvfrom to throw
        # an exception and break the loop
        self.command_socket.close()
        self.data_socket.close()
        # attempt to join the threads back.
        self.command_thread.join()
        self.data_thread.join()
