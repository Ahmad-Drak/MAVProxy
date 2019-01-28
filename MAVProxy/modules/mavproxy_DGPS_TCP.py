#!/usr/bin/env python
'''
DGPS client to work with Emlid ReachRTK (for example)
Configure ReachView like so:
Position output: off
Position input: off
Base mode:
TCP, Role: Server, address: localhost, Port: 9000, Format: ERB
Configure Reachiew ON THE ROVER like so:
Base mode: off
Position output: Serial, 38k4, ERB
Position input: Serial, 38k4, RTCM4
Click the green 'Connected to /dev/ttyMFD2' to see if rtcm data is coming in.
'''

import socket, errno, time
#from pymavlink import mavutil
from MAVProxy.modules.lib import mp_module


class DGPSClientModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(DGPSClientModule, self).__init__(mpstate, "DGPSClient", "DGPSClient injection support")
        print "Loading DGPS module"
        self.inject_seq_nr = 0
        #self.connect_to_rtcm_base("127.0.0.1", 9000)
        self.connect_to_rtcm_base("192.168.42.1", 9000)

    def connect_to_rtcm_base(self, ip, port):
        try:
            self.base_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.base_conn.connect((ip, port))
            self.base_conn.settimeout(0.2)
        except:
            print "ERROR: could not connect to RTCM base"
        else:
            print "Connected to base to get RTCM data"

    def idle_task(self):
        '''called in idle time'''
        try:
            data = self.base_conn.recv(1024)  # Attempt to read up to 1024 bytes.
            #data = "blabla"
            #time.sleep(12)
            # while True: pass
        except socket.error as e:
            if e.errno in [errno.EAGAIN, errno.EWOULDBLOCK]:
                return
            raise
        try:
            self.send_rtcm_msg(data)
        except Exception, e:
            print "DGPS: GPS Inject Failed:", e

    def send_rtcm_msg(self, data):
        msglen = 180

        if (len(data) > msglen * 4):
            print "DGPS: Message too large", len(data)
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
            datachunk = data[a * msglen: a * msglen + amount]

            print("Sending DGPS RTCM3 data flags {0}, length {1}".format(bin(flags), len(data)))
            self.master.mav.gps_rtcm_data_send(
                flags,
                len(datachunk),
                bytearray(datachunk.ljust(180, '\0')))

        # Send a terminal 0-length message if we sent 2 or 3 exactly-full messages.
        if (msgs < 4) and (len(data) % msglen == 0) and (len(data) > msglen):
            flags = 1 | (msgs & 0x3) << 1 | (self.inject_seq_nr & 0x1f) << 3
            self.master.mav.gps_rtcm_data_send(
                flags,
                0,
                bytearray("".ljust(180, '\0')))

        self.inject_seq_nr += 1


def init(mpstate):
    '''initialise module'''
    return DGPSClientModule(mpstate)
