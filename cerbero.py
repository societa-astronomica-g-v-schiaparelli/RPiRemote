#!/usr/bin/env python

import Tkinter
import time
import threading
import random
import Queue
import numpy as np
import socket
import sys
import json
from PIL import Image, ImageTk
import traceback
import struct

CONFIG_FILE = '/home/osservatorio/cerbero.conf'
#CONFIG_FILE = './cerbero.conf'

# ASI config
ASI_ADDRESS = {}
ASI_PORT = {}
ASI_X = {}
ASI_Y = {}
ASI_IMG_SIZE = {}

ASI_ADDRESS[1] = '192.168.40.122'
ASI_PORT[1] = 10000
ASI_X[1] = 1280
ASI_Y[1] = 960
ASI_IMG_SIZE[1] = ASI_X[1] * ASI_Y[1]

ASI_ADDRESS[2] = '192.168.40.123'
ASI_PORT[2] = 10000
ASI_X[2] = 1280
ASI_Y[2] = 960
ASI_IMG_SIZE[2] = ASI_X[2] * ASI_Y[2]

ASI_ADDRESS[3] = '192.168.40.121'
ASI_PORT[3] = 10000
ASI_X[3] = 1280
ASI_Y[3] = 960
ASI_IMG_SIZE[3] = ASI_X[3] * ASI_Y[3]

# millisec
MIN_EXP_TIME = 1
MAX_EXP_TIME = 15000
DEFAULT_EXP_TIME = 20

SOCKET_TIMEOUT = 20

# Relay board
ETHRLY_IP = '192.168.40.26'
ETHRLY_PORT = 17494
ETHRLY_TH_LAMP_RELAY = 1

class EthRly:

    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

    def __del__(self):
        try:
            self.sock.close()
        except:
            pass

    def connect(self): 
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        self.sock.connect((self.ip, self.port))

    def disconnect(self):
        self.sock.close()

    def write(self, command, expect_output=False):
        out = struct.pack('B', command)
        self.sock.sendall(out)
        if expect_output:
            res = self.sock.recv(1)
        self.sock.sendall('\x00')
        if expect_output:
            return ord(res)

    def turnRelayOn(self, relay_num):
        num = 0x64 + int(relay_num)
        self.write(num)

    def turnRelayOff(self, relay_num):
        num = 0x6E + int(relay_num)
        self.write(num)

    def getRelayStatus(self):
        res = self.write(0x5B, True)
        status = {}
        status[1] = res & 0b00000001
        status[2] = (res & 0b00000010) >> 1
        status[3] = (res & 0b00000100) >> 2
        status[4] = (res & 0b00001000) >> 3
        status[5] = (res & 0b00010000) >> 4
        status[6] = (res & 0b00100000) >> 5
        status[7] = (res & 0b01000000) >> 6
        status[8] = (res & 0b10000000) >> 7
        return status

class GuiPart:
    def __init__(self, master, queue, endCommand, relay_queue):

        with open(CONFIG_FILE) as f:
            self.config = json.load(f)

        self.master = master
        self.queue = queue
        self.relay_queue = relay_queue

        self.master.title("Telecamere terza cupola")
        self.master.geometry("1650x940")

        self.master.protocol("WM_DELETE_WINDOW", endCommand)


        self.frame_w = Tkinter.Frame(self.master)
        self.frame_w.grid(row=0, column=0, rowspan=2, sticky="NW")
        self.frame_ne = Tkinter.Frame(self.master)
        self.frame_ne.grid(row=0, column=1, sticky="NE")
        self.frame_se = Tkinter.Frame(self.master)
        self.frame_se.grid(row=1, column=1, sticky="SE")


        self.canvas1 = Tkinter.Canvas(self.frame_ne, width=600, height=450)
        self.canvas1.grid(row=0, column=0, rowspan=2, sticky="N")

        Tkinter.Label(self.frame_ne, text='Exp time (ms)').grid(row=0, column=1)
        self.slider_exp1 = Tkinter.Scale(self.frame_ne, from_=MIN_EXP_TIME, to=MAX_EXP_TIME, resolution=10, length=400, variable=exp_time[1])
        self.slider_exp1.set(DEFAULT_EXP_TIME)
        self.slider_exp1.grid(row=1, column=1)
       
        Tkinter.Label(self.frame_ne, text='Gain').grid(row=0, column=2)
        self.slider_gain1 = Tkinter.Scale(self.frame_ne, from_=0, to=300, length=400, variable=gain[1])
        self.slider_gain1.set(150)
        self.slider_gain1.grid(row=1, column=2)



        self.canvas2 = Tkinter.Canvas(self.frame_w, width=853, height=640)
        self.canvas2.grid(row=0, column=0, sticky="N")

        self.slider_exp2 = Tkinter.Scale(self.frame_w, from_=MIN_EXP_TIME, to=MAX_EXP_TIME, resolution=10, length=580, orient=Tkinter.HORIZONTAL, variable=exp_time[2], label='Exp time (ms)')
        self.slider_exp2.set(DEFAULT_EXP_TIME)
        self.slider_exp2.grid(row=1, column=0)
       
        self.slider_gain2 = Tkinter.Scale(self.frame_w, from_=0, to=300, length=580, orient=Tkinter.HORIZONTAL, variable=gain[2], label='Gain')
        self.slider_gain2.set(150)
        self.slider_gain2.grid(row=2, column=0)

        self.frame2 = Tkinter.Frame(self.frame_w)
        self.frame2.grid(row=3, column=0)

        self.crosshair_x_label = Tkinter.Label(self.frame2, text='Crosshair: x')
        self.crosshair_x_label.grid(row=0, column=0, sticky="W")
        self.crosshair_x = Tkinter.Entry(self.frame2)
        self.crosshair_x.insert(0, self.config['crosshair'][0])
        self.crosshair_x.grid(row=0, column=1, sticky="W")

        self.crosshair_y_label = Tkinter.Label(self.frame2, text='y')
        self.crosshair_y_label.grid(row=0, column=2, sticky="W")
        self.crosshair_y = Tkinter.Entry(self.frame2)
        self.crosshair_y.insert(0, self.config['crosshair'][1])
        self.crosshair_y.grid(row=0, column=3, sticky="W")

        self.thLampStatus = False
        self.thLampSwitchOn = Tkinter.Button(self.frame2, text="4-20mA switch ON", command= lambda: self.switchLamp(True))
        self.thLampSwitchOn.grid(row=1, column=0)
        self.thLampSwitchOff = Tkinter.Button(self.frame2, text="4-20mA switch OFF", command= lambda: self.switchLamp(False))
        self.thLampSwitchOff.grid(row=1, column=1)
        self.thLampSwitchStatus = Tkinter.Label(self.frame2, text="OFF", background='red', width=5)
        self.thLampSwitchStatus.grid(row=1, column=2)



        self.canvas3 = Tkinter.Canvas(self.frame_se, width=600, height=450)
        self.canvas3.grid(row=0, column=0, rowspan=2, sticky="N")

        Tkinter.Label(self.frame_se, text='Exp time (ms)').grid(row=0, column=1)
        self.slider_exp3 = Tkinter.Scale(self.frame_se, from_=MIN_EXP_TIME, to=MAX_EXP_TIME, resolution=10, length=400, variable=exp_time[3])
        self.slider_exp3.set(DEFAULT_EXP_TIME)
        self.slider_exp3.grid(row=1, column=1)

        Tkinter.Label(self.frame_se, text='Gain').grid(row=0, column=2)
        self.slider_gain3 = Tkinter.Scale(self.frame_se, from_=0, to=300, length=400, variable=gain[3])
        self.slider_gain3.set(150)
        self.slider_gain3.grid(row=1, column=2)

        self.canvas1_image = None
        self.canvas2_image = None
        self.canvas3_image = None

    def switchLamp(self, status):
        self.relay_queue.put({'action':'change_status', 'relay_num':ETHRLY_TH_LAMP_RELAY, 'status':status})

    def changeSwitchLabelStatus(self, label, status):
        if status:
            label.config(text='ON')
            label.config(background='green')
        else:
            label.config(text='OFF')
            label.config(background='red')

    def processIncoming(self):
        while self.queue.qsize():
            try:
                self.msg = self.queue.get(0)

                if self.msg['type'] == 'image':

                    self.data = self.msg['image']
                    self.data_id = self.msg['id']

                    if self.data_id == 1:
                        if self.canvas1_image is not None:
                            self.canvas1.delete(self.canvas1_image)
                        self.im1 = Image.frombytes('L', (self.data.shape[1],self.data.shape[0]), self.data.astype('b').tostring()).resize((600,450))
                        self.photo1 = ImageTk.PhotoImage(image=self.im1)
                        self.canvas1_image = self.canvas1.create_image(0,0,image=self.photo1,anchor=Tkinter.NW)

                    if self.data_id == 2:
                        if self.canvas2_image is not None:
                            self.canvas2.delete(self.canvas2_image)
                        self.im2 = Image.frombytes('L', (self.data.shape[1],self.data.shape[0]), self.data.astype('b').tostring()).resize((853,640))
                        self.photo2 = ImageTk.PhotoImage(image=self.im2)
                        self.canvas2.delete('all')
                        self.canvas2_image = self.canvas2.create_image(0,0,image=self.photo2,anchor=Tkinter.NW)

                        # draw crosshair
                        x = int(self.crosshair_x.get())
                        y = int(self.crosshair_y.get())
                        
                        self.canvas2.create_line(x, 0, x, y-10, fill='red', width=1)
                        self.canvas2.create_line(x, y+10, x, 640, fill='red', width=1)

                        self.canvas2.create_line(0, y, x-10, y, fill='red', width=1)
                        self.canvas2.create_line(x+10, y, 853, y, fill='red', width=1)

                        self.config['crosshair'][0] = self.crosshair_x.get()
                        self.config['crosshair'][1] = self.crosshair_y.get()

                        with open(CONFIG_FILE, 'w') as f:
                            json.dump(self.config, f)

                    if self.data_id == 3:
                        if self.canvas3_image is not None:
                            self.canvas3.delete(self.canvas3_image)
                        self.im3 = Image.frombytes('L', (self.data.shape[1],self.data.shape[0]), self.data.astype('b').tostring()).resize((600,450))
                        self.photo3 = ImageTk.PhotoImage(image=self.im3)
                        self.canvas3.delete('all')
                        self.canvas3_image = self.canvas3.create_image(0,0,image=self.photo3,anchor=Tkinter.NW)

                if self.msg['type'] == 'relaystatus':
                    self.changeSwitchLabelStatus(self.thLampSwitchStatus, self.msg['status'][ETHRLY_TH_LAMP_RELAY])

            except Queue.Empty:
                pass

class ThreadedClient:
   
    def __init__(self, master):

        self.master = master

        self.queue = Queue.Queue()

        self.relay_queue = Queue.Queue()

        self.gui = GuiPart(master, self.queue, self.endApplication, self.relay_queue)

        self.running = 1
    	self.thread1 = threading.Thread(target=self.getRemoteImage, args=(1,))
        self.thread1.start()

    	self.thread2 = threading.Thread(target=self.getRemoteImage, args=(2,))
        self.thread2.start()

    	self.thread3 = threading.Thread(target=self.getRemoteImage, args=(3,))
        self.thread3.start()

    	self.thread4 = threading.Thread(target=self.getEthRlyStatus)
        self.thread4.start()

    	self.thread5 = threading.Thread(target=self.handleRelayQueue)
        self.thread5.start()

        self.periodicCall()

    def periodicCall(self):
        self.gui.processIncoming()
        if not self.running:
            sys.exit(1)
        self.master.after(100, self.periodicCall)

    def getRemoteImage(self, camera_id):
        while self.running:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
            sock.connect((ASI_ADDRESS[camera_id], ASI_PORT[camera_id]))

            # send capture parameters
            params = {}
            params['exp_time'] = 1000*exp_time[camera_id].get()
            params['gain'] = gain[camera_id].get()
            sock.sendall(json.dumps(params))

            # receive capture
            arr = b''
            time_start = time.time()
            try:
                while len(arr) < ASI_IMG_SIZE[camera_id]:
                    now = time.time()
                    if (now - time_start) > SOCKET_TIMEOUT:
                        break
                    data  = sock.recv(2**16)
                    if data:
                        arr += data
                image_array = np.frombuffer(arr, dtype=np.dtype(np.uint8)).reshape((ASI_Y[camera_id], ASI_X[camera_id]))
                sock.close()
                msg = {'type':'image', 'id':camera_id, 'image':image_array}
                self.queue.put(msg)
            except:
                traceback.print_exc()
                pass

    def getEthRlyStatus(self):
        while self.running:
            self.relay_queue.put({'action':'get_status'})
            time.sleep(5)

    def handleRelayQueue(self):
        board = EthRly(ETHRLY_IP, ETHRLY_PORT)
        while self.running:
            while self.relay_queue.qsize():
                try:
                    msg = self.relay_queue.get(0)
                    board.connect()
                    if msg['action'] == 'get_status':
                        status = board.getRelayStatus()
                        self.queue.put({'type':'relaystatus', 'status':status})

                    if msg['action'] == 'change_status':
                        if msg['status']:
                            board.turnRelayOn(msg['relay_num'])
                        else:
                            board.turnRelayOff(msg['relay_num'])

                        status = board.getRelayStatus()
                        self.queue.put({'type':'relaystatus', 'status':status})

                    board.disconnect()
                except Queue.Empty:
                    pass

    def endApplication(self):
        self.running = 0

root = Tkinter.Tk()

exp_time = {}
gain = {}

exp_time[1] = Tkinter.IntVar()
gain[1] = Tkinter.IntVar()

exp_time[2] = Tkinter.IntVar()
gain[2] = Tkinter.IntVar()

exp_time[3] = Tkinter.IntVar()
gain[3] = Tkinter.IntVar()

client = ThreadedClient(root)
root.mainloop()
