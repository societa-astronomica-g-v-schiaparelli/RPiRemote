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

#CONFIG_FILE = '/home/osservatorio/cerbero.conf'
CONFIG_FILE = './cerbero.conf'

# ASI config
ASI1_ADDRESS = '192.168.40.195'
ASI1_PORT = 10000
ASI1_X = 1280
ASI1_Y = 960
ASI1_IMG_SIZE = ASI1_X * ASI1_Y

ASI2_ADDRESS = '192.168.10.44'
ASI2_PORT = 10000
ASI2_X = 1280
ASI2_Y = 960
ASI2_IMG_SIZE = ASI2_X * ASI2_Y

ASI3_ADDRESS = 'localhost'
ASI3_PORT = 10001
ASI3_X = 1280
ASI3_Y = 960
ASI3_IMG_SIZE = ASI3_X * ASI3_Y

# millisec
MIN_EXP_TIME = 1
MAX_EXP_TIME = 3000
DEFAULT_EXP_TIME = 2

SOCKET_TIMEOUT = 30

class GuiPart:
    def __init__(self, master, queue, endCommand):

        with open(CONFIG_FILE) as f:
            self.config = json.load(f)

        self.master = master
        self.queue = queue

        self.master.title("Telecamere terza cupola")
        self.master.geometry("1800x600")

        self.canvas1 = Tkinter.Canvas(self.master, width=600, height=450)
        self.canvas1.grid(row=0, column=0)

        self.canvas2 = Tkinter.Canvas(self.master, width=600, height=450)
        self.canvas2.grid(row=0, column=1)

        self.canvas3 = Tkinter.Canvas(self.master, width=600, height=450)
        self.canvas3.grid(row=0, column=2)

        self.slider_exp1 = Tkinter.Scale(self.master, from_=MIN_EXP_TIME, to=MAX_EXP_TIME, length=400, orient=Tkinter.HORIZONTAL, variable=exp_time1, label='Exp time (ms)')
        self.slider_exp1.set(DEFAULT_EXP_TIME)
        self.slider_exp1.grid(row=1, column=0)
       
        self.slider_gain1 = Tkinter.Scale(self.master, from_=0, to=300, length=400, orient=Tkinter.HORIZONTAL, variable=gain1, label='Gain')
        self.slider_gain1.set(150)
        self.slider_gain1.grid(row=2, column=0)

        self.slider_exp2 = Tkinter.Scale(self.master, from_=MIN_EXP_TIME, to=MAX_EXP_TIME, length=400, orient=Tkinter.HORIZONTAL, variable=exp_time2, label='Exp time (ms)')
        self.slider_exp2.set(DEFAULT_EXP_TIME)
        self.slider_exp2.grid(row=1, column=1)
       
        self.slider_gain2 = Tkinter.Scale(self.master, from_=0, to=300, length=400, orient=Tkinter.HORIZONTAL, variable=gain2, label='Gain')
        self.slider_gain2.set(150)
        self.slider_gain2.grid(row=2, column=1)

        self.frame2 = Tkinter.Frame(self.master)
        self.frame2.grid(row=3, column=1)

        self.crosshair_x_label = Tkinter.Label(self.frame2, text='Crosshair: x')
        self.crosshair_x_label.grid(row=0, column=0)
        self.crosshair_x = Tkinter.Entry(self.frame2)
        self.crosshair_x.insert(0, self.config['crosshair'][0])
        self.crosshair_x.grid(row=0, column=1)

        self.crosshair_y_label = Tkinter.Label(self.frame2, text='y')
        self.crosshair_y_label.grid(row=0, column=2)
        self.crosshair_y = Tkinter.Entry(self.frame2)
        self.crosshair_y.insert(0, self.config['crosshair'][1])
        self.crosshair_y.grid(row=0, column=3)

        self.slider_exp3 = Tkinter.Scale(self.master, from_=MIN_EXP_TIME, to=MAX_EXP_TIME, length=400, orient=Tkinter.HORIZONTAL, variable=exp_time3, label='Exp time (ms)')
        self.slider_exp3.set(DEFAULT_EXP_TIME)
        self.slider_exp3.grid(row=1, column=2)
       
        self.slider_gain3 = Tkinter.Scale(self.master, from_=0, to=300, length=400, orient=Tkinter.HORIZONTAL, variable=gain3, label='Gain')
        self.slider_gain3.set(150)
        self.slider_gain3.grid(row=2, column=2)

        self.canvas1_image = None
        self.canvas2_image = None
        self.canvas3_image = None

    def processIncoming(self):
        """
        Handle all the messages currently in the queue (if any).
        """
        while self.queue.qsize():
            try:
                self.msg = self.queue.get(0)
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
                    self.im2 = Image.frombytes('L', (self.data.shape[1],self.data.shape[0]), self.data.astype('b').tostring()).resize((600,450))
                    self.photo2 = ImageTk.PhotoImage(image=self.im2)
                    self.canvas2.delete('all')
                    self.canvas2_image = self.canvas2.create_image(0,0,image=self.photo2,anchor=Tkinter.NW)

                    # draw crosshair
                    x = int(self.crosshair_x.get())
                    y = int(self.crosshair_y.get())
                    
                    self.canvas2.create_line(x, 0, x, y-10, fill='red', width=1)
                    self.canvas2.create_line(x, y+10, x, 450, fill='red', width=1)

                    self.canvas2.create_line(0, y, x-10, y, fill='red', width=1)
                    self.canvas2.create_line(x+10, y, 600, y, fill='red', width=1)

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

            except Queue.Empty:
                pass

class ThreadedClient:
   
    def __init__(self, master):

        self.master = master

        # Create the queue
        self.queue = Queue.Queue()

        # Set up the GUI part
        self.gui = GuiPart(master, self.queue, self.endApplication)

        # Set up the thread to do asynchronous I/O
        # More can be made if necessary
        self.running = 1
    	self.thread1 = threading.Thread(target=self.workerThread1)
        self.thread1.start()

    	self.thread2 = threading.Thread(target=self.workerThread2)
        self.thread2.start()

    	self.thread3 = threading.Thread(target=self.workerThread3)
        self.thread3.start()

        # Start the periodic call in the GUI to check if the queue contains
        # anything
        self.periodicCall()

    def periodicCall(self):
        self.gui.processIncoming()
        if not self.running:
            sys.exit(1)
        self.master.after(100, self.periodicCall)

    def workerThread1(self):
        while self.running:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
            sock.connect((ASI1_ADDRESS, ASI1_PORT))

            # send capture parameters
            params = {}
            params['exp_time'] = 1000*exp_time1.get()
            params['gain'] = gain1.get()
            sock.sendall(json.dumps(params))

            # receive capture
            arr = b''
            time_start = time.time()
            try:
                while len(arr) < ASI1_IMG_SIZE:
                    now = time.time()
                    if (now - time_start) > SOCKET_TIMEOUT:
                        break
                    data  = sock.recv(2**16)
                    if data:
                        arr += data
                image_array = np.frombuffer(arr, dtype=np.dtype(np.uint8)).reshape((ASI1_Y,ASI1_X))
                sock.close()
                msg = {'id':1, 'image':image_array}
                self.queue.put(msg)
            except:
                pass

    def workerThread2(self):
        while self.running:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
            sock.connect((ASI2_ADDRESS, ASI2_PORT))

            # send capture parameters
            params = {}
            params['exp_time'] = 1000*exp_time2.get()
            params['gain'] = gain2.get()
            sock.sendall(json.dumps(params))

            # receive capture
            arr = b''
            time_start = time.time()
            try:
                while len(arr) < ASI2_IMG_SIZE:
                    now = time.time()
                    if (now - time_start) > SOCKET_TIMEOUT:
                        break
                    data  = sock.recv(2**16)
                    if data:
                        arr += data
                image_array = np.frombuffer(arr, dtype=np.dtype(np.uint8)).reshape((ASI2_Y,ASI2_X))
                sock.close()
                msg = {'id':2, 'image':image_array}
                self.queue.put(msg)
            except:
                traceback.print_exc()
                pass

    def workerThread3(self):
        while self.running:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
            sock.connect((ASI3_ADDRESS, ASI3_PORT))

            # send capture parameters
            params = {}
            params['exp_time'] = 1000*exp_time3.get()
            params['gain'] = gain3.get()
            sock.sendall(json.dumps(params))

            # receive capture
            arr = b''
            time_start = time.time()

            while len(arr) < ASI3_IMG_SIZE:
                now = time.time()
                if (now - time_start) > SOCKET_TIMEOUT:
                    break
                data  = sock.recv(2**16)
                if data:
                    arr += data
            image_array = np.frombuffer(arr, dtype=np.dtype(np.uint8)).reshape((ASI3_Y,ASI3_X))
            sock.close()
            msg = {'id':3, 'image':image_array}
            self.queue.put(msg)


    def endApplication(self):
        self.running = 0

root = Tkinter.Tk()

exp_time1 = Tkinter.IntVar()
gain1 = Tkinter.IntVar()

exp_time2 = Tkinter.IntVar()
gain2 = Tkinter.IntVar()

exp_time3 = Tkinter.IntVar()
gain3 = Tkinter.IntVar()

client = ThreadedClient(root)
root.mainloop()
