import tkinter as tk
import socket
import threading
from threading import Thread
from textwrap import wrap
from operator import itemgetter
from tkinter import filedialog
from tkinter import Frame, Button
from tkinter import *
from datetime import datetime
import time
import sys

def exit_function():
    Server.skt.close()
    Client.clientSocket.close()
    window.destroy()
    sys.exit()
class User():
    current_time = time.strftime('%H:%M')

    def __init__(self, myip, theirip,myuser):
        self.myip = myip
        self.theirip = theirip
        self.myuser = myuser
    def update_clock():
        new_time = time.strftime('%H:%M')
        Client.current_time = new_time
        window.after(1, Client.update_clock)

class Client(User):
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    clientSocket.bind((User.myip,8888))
    serveraddress = (User.theirip,9999)
    clientSocket.settimeout(2)
    seqnum = 1
    filename = ''
    
    def browseFiles():
        filename = filedialog.askopenfilename(initialdir = "/",title = "Select a File",filetypes = (("Text files","*.txt*"),("All files", "*.*")))
        w2=tk.Tk()
        w2.title('Send File')
        output = tk.Text(w2)
        output.bind("<Key>", lambda e: "break")
        output.pack()
        sendfile_button = tk.Button(w2,command=Client.send_file,text='Send File').pack() 
        Client.filename = filename
        output.insert(tk.END, filename)


    def send_message():
        message = user_input.get()
        Client.update_clock()
        chat_output.insert(tk.END, message+"\n", 'tag-left')
        chat_output.insert(tk.END, Client.current_time+"\n", 'tag-left')

        user_input.delete(0, tk.END)
        textlength = len(message)
        #splitting text into fragments
        packets = wrap(message, 256)
        finalPackets = []
        #creating packets
        for packet in packets:
            flag = False
            textlength -= len(packet)
            if (textlength == 0) or (len(message)<=256): #check if final fragment
                flag = True
            finalPackets.append({'text':packet, 'length':len(packet), 'seqnum':Client.seqnum,'IsFinal':flag})
            Client.seqnum += len(packet)
            lastseq = 0
            currentseq = 0#expected acknum from server
            for i in finalPackets:
                currentseq = i["seqnum"]
                print("currentseq: ",currentseq)
                if lastseq != currentseq:
                    Client.clientSocket.sendto(str(i).encode(),Client.serveraddress)
                else:
                    continue
                #handling acks received from server
                sent =0
                while True:
                    try:
                        ack = 1
                        Client.clientSocket.settimeout(2)               
                        ack = Client.clientSocket.recvfrom(1024)[0].decode() #ack received from server
                        print("ack: ",ack)
                        if int(ack) == int(currentseq + i["length"]): #if ack received = next seqnum, packet is acked
                            print("acked")
                            lastseq = currentseq
                            chat_output.insert(tk.END, "received"+"\n", 'tag-left')
                            break
                    except:
                        sent+=1
                        print(sent)
                        print("not acked")
                        print("resending")
                        Client.clientSocket.sendto(str(i).encode(),Client.serveraddress)
                        if sent == 20:
                            user_input.delete(0,tk.END)
                            chat_output.insert(tk.END, "not received"+"\n", 'tag-left')

                            break

    def send_file():
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((Client.tip,8080))
        file = open(Client.filename,"rb")
        data = file.read()
        client.sendall(data)
        client.send(b"STOP")
        print("sent")
        file.close()
        client.close()

class Server(User): 

    mip = '127.0.0.1'
    tip = '127.0.0.1'
    skt= socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    skt.bind((mip,9999))
    print('listening on', skt)

    def receivefile():
        Server.update_clock()
        host = Server.mip
        port = 8080

        server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        server.bind((host,port))
        server.listen()

        client,addr = server.accept()

        file = open("file","wb")

        file_bytes = b""
        done = False

        while not done:
            data = client.recv(1024)
            print(data)
            if file_bytes[-4:] == b"STOP":
                done = True
            else:
                file_bytes += data

        file.write(file_bytes[:len(file_bytes)-4])
        chat_output.insert(tk.END, f' sent a file'+"\n",'tag-right')

        file.close()
        client.close()
        server.close()

    def receive_message():
        skt = Server.skt
        datalist = [] #list of received packets
        text = ''

        length = 1
        #receive packets from client
        while True:
            acknum = 0
            lastacknum =0 
            data = skt.recvfrom(1024)[0]
            data = data.decode()
            datadict = eval(data) 

            acknum = datadict["seqnum"]+datadict["length"] 
            
            print("acknum: ",acknum)
            if datadict in datalist:
                skt.sendto(str(acknum).encode(),(Server.tip,8888)) #send ack
                
            else:
                datalist.append(datadict)
                length += datadict["length"]
                lastacknum = acknum

                print(length)
                datalist = sorted(datalist, key=itemgetter('seqnum')) #sort datalist based on seqnum
    
                print(datalist)
                skt.sendto(str(acknum).encode(),(Server.tip,8888)) #send ack
                if datalist[-1]["IsFinal"] == True and datalist[-1]["seqnum"]+datalist[-1]["length"] == length: #if fragment is last one and if all fragments before it are received
                    for i in datalist:
                        text += i["text"] #if message was fragmented join them together
                    chat_output.insert(tk.END, text+"\n", 'tag-right')
                    chat_output.insert(tk.END, Server.current_time+"\n", 'tag-right')

                    text = ''
                    datalist = []    

#gui
window = tk.Tk()

window.config(bg="#f5f5f5")
window.resizable(False,False)
window.geometry("580x441")

#window.grid()
window.protocol('WM_DELETE_WINDOW', exit_function)
window.title('Python Chat App')

chat_output = tk.Text(window, font=('Roboto',12),background="#f5f5f5",width=64,height=21, highlightthickness = 0, bd = 0)
chat_output.bind("<Key>", lambda e: "break")
chat_output.tag_configure('tag-right', justify='right')
chat_output.tag_configure('tag-left', justify='left')


chat_output.pack()
chat_output.place(x=0,y=0)
user_input = tk.Entry(window,width=30,font=("Roboto",18),fg="Black", highlightthickness = 0, bd = 0)
user_input.pack()
user_input.place(x=30,y=405)
img = PhotoImage(file="attachmenticon.png")
send_button = tk.Button(window,command=Client.send_message,text='Send',background="#000000",fg = "#ffffff",font=("Roboto",13), width=18, highlightthickness = 0, bd = 0)
send_button.pack()
send_button.place(x=414,y=405,height=36)
button_explore =tk.Button(window,image=img,command = Client.browseFiles,height=30,width=30,background='#f5f5f5', highlightthickness = 0, bd = 0)
button_explore.place(x=0, y=405)
t = threading.Thread(target=Server.receive_message)
t.daemon = True
t2 = threading.Thread(target=Server.receivefile)
t2.daemon = True

t.start()
t2.start()
window.update()
window.update_idletasks()

window.mainloop()





