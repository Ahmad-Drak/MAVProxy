#!/usr/bin/env python
'''
support for a GCS attached DGPS system

DID NOT USE THIS MODULE, I USED THE DGPS_TCP.PY
'''

import socket, errno
from pymavlink import mavutil
from MAVProxy.modules.lib import mp_module

import socket, errno
from pymavlink import mavutil
from MAVProxy.modules.lib import mp_module

class DGPSModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(DGPSModule, self).__init__(mpstate, "DGPS", "DGPS injection support for SBP/RTCP/UBC")
        #self.ipaddress = 192.168.42.1 
        #self.ipaddress = 127.0.0.1
        self.portnum = 9000
        #self.portnum = 13320
        self.port = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.port.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.port.bind(("0.0.0.0", self.portnum))
        #self.port.bind((self.ipaddress, self.portnum))
        mavutil.set_close_on_exec(self.port.fileno())
        self.port.setblocking(0)
        self.inject_seq_nr = 0
        print("DGPS_dove: Listening for RTCM packets on ://%s:%s" % ("127.0.0.1", self.portnum))
    
    def send_rtcm_msg(self, data):
        msglen = 180;
        
        if (len(data) > msglen * 4):
            print("DGPS: Message too large", len(data))
            return
        
        # How many messages will we send?
        msgs = 0
        if (len(data) % msglen == 0):
            msgs = len(data) / msglen
        else:
            msgs = (len(data) / msglen) + 1
        
        for a in range(0, msgs):
            
            flags = 0
            
            # Set the fragment flag if we're sending more than 1 packet.
            if (msgs) > 1:
                flags = 1
            
            # Set the ID of this fragment
            flags |= (a & 0x3) << 1
            
            # Set an overall sequence number
            flags |= (self.inject_seq_nr & 0x1f) << 3
            
            
            amount = min(len(data) - a * msglen, msglen)
            datachunk = data[a*msglen : a*msglen + amount]
            
            self.master.mav.gps_rtcm_data_send(
                flags,
                len(datachunk),
                bytearray(datachunk.ljust(180, '\0')))
        
        # Send a terminal 0-length message if we sent 2 or 3 exactly-full messages.     
        if (msgs < 4) and (len(data) % msglen == 0) and (len(data) > msglen):
            flags = 1 | (msgs & 0x3)  << 1 | (self.inject_seq_nr & 0x1f) << 3
            self.master.mav.gps_rtcm_data_send(
                flags,
                0,
                bytearray("".ljust(180, '\0')))
            
        self.inject_seq_nr += 1



    def idle_task(self):
        '''called in idle time'''
        try:
            data = self.port.recv(1024) # Attempt to read up to 1024 bytes.
        except socket.error as e:
            if e.errno in [ errno.EAGAIN, errno.EWOULDBLOCK ]:
                return
            raise
        try:
            self.send_rtcm_msg(data)

        except Exception as e:
            print("DGPS: GPS Inject Failed:", e)

def init(mpstate):
    '''initialise module'''
    return DGPSModule(mpstate)

