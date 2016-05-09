#! /usr/bin/env python

import socket
import struct
import threading
import sys
import urllib
import pickle
import math
import os
import httplib2
import timeit

#Format strings
UNPACK_FORMAT = struct.Struct("!6H")
UNPACK_QUESTION_FORMAT = struct.Struct("!2H")


# List of replica servers
replica_list = ["54.174.6.90","54.149.9.25","54.67.86.61","54.72.167.104","54.93.182.67","54.169.146.226","54.65.104.220","54.66.212.131","54.94.156.232"]


#Creating socket
sockfd = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

#Retrieving port number and domain name from command-line
if (len(sys.argv) == 5):
    port = sys.argv[2]
    port = int(port)
    given_domain_name = sys.argv[4]
else:
    print "Invalid number of command line arguments... Program exited"
    sys.exit()

# Check if cache exists. If it does not, create an empty cache
if not os.path.exists("dns_cache"):
    empty_map = dict()
    pickle.dump( empty_map , open("dns_cache","wb") )

# Load contents from the cache to the local dictionary
client_replica_map = pickle.load(open("dns_cache","rb"))


# Port for DNS-HTTP communication
second_port = port + 50


#Finding the IP of our DNS server
dup_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
dup_sock.connect(("david.choffnes.com",80))
host_ip= dup_sock.getsockname()[0]
dup_sock.close()

#Binding the server to the given port
sockfd.bind((host_ip,port))

#Function to find the labels in a DNS section
def unpack_labels(packet, offset):
    labels = []

    while True:
        lgth, = struct.unpack_from("!B", packet, offset)

        if (lgth & 192) == 192:
            ptr, = struct.unpack_from("!H", packet, offset)
            offset += 2

            return labels + unpack_labels(packet, ptr & 16383), offset

        if (lgth & 192) != 0:
            print "Invalid label"
            sys.exit()

        offset += 1

        if lgth == 0:
            return labels, offset

        labels.append(*struct.unpack_from("!%ds" % lgth, packet, offset))
        offset += lgth


#Function to build a DNS response packet
def build_response_packet(url,ip,tid):
    packet = struct.pack("!H", tid)  # Query Ids (Just 1 for now)
    packet += struct.pack("!H", 32768)  # Flags
    packet += struct.pack("!H", 1)  # Questions
    packet += struct.pack("!H", 1)  # Answers
    packet += struct.pack("!H", 0)  # Authorities
    packet += struct.pack("!H", 0)  # Additional
    split_url = url.split(".")
    #Building the questions
    for part in split_url:
        packet += struct.pack("!B", len(part))
        for byte in bytes(part):
            packet += struct.pack("!c", byte)
    packet += struct.pack("!B", 0)  # End of String
    packet += struct.pack("!H", 1)  # Query Type
    packet += struct.pack("!H", 1)  # Query Class
    packet += struct.pack("!H",49164) #dname using ptr
    packet += struct.pack("!H", 1)  # Query Type
    packet += struct.pack("!H", 1)  # Query Class

    packet += struct.pack("!I", 1)  # TTL
    packet += struct.pack("!H", 4)  # Length

    #Building the answer
    split_ip = ip.split(".")
    for ip_part in split_ip:
        packet += struct.pack("!B", int(ip_part))

    return packet

#Function to find the best replica
def fetch_best_replica(client_ip):

    if client_ip in client_replica_map:
        return client_replica_map[client_ip]
    else:
        return calc_best_replica(client_ip)


# Function to check which replica has the least RTT ot the client
def calc_best_replica(client_ip):
    min_rtt = 9999999999999999         # Setting initial minimum RTT to a high value
    best_replica_ip = ''
    rtt = 0
    
    # Send the client IP to each replica server to re-compute RTT
    for replica in replica_list:
        resobj = httplib2.Http()
        head = resobj.request("http://"+replica+":"+str(second_port)+"/"+client_ip,"HEAD")
        rtt = float(head[0]['content-type'])
        if (rtt <= min_rtt):
            min_rtt = rtt
            best_replica_ip = replica
    client_replica_map[client_ip] = best_replica_ip
    return best_replica_ip

# Recompute the RTT values for each client in the hashtable
def recompute_best_replicas():
    for client in client_replica_map:
        ret = calc_best_replica(client)
    expiry_time = timeit.default_timer()
    pickle.dump(client_replica_map, open("dns_cache","wb"))


#Main Function
def main_function():

    questions = []
    print "Waiting for request at port: ",port

    try:
        #Receive DNS request
        data = sockfd.recvfrom(2048)

        #Create another thread to listen
        t = threading.Thread(target=main_function)
        t.daemon = True
        t.start()

        #Extract the contents of the DNS request
        received_msg = data[0]
        client_address_port = data[1]
        client_ip = client_address_port[0]

        tid, n, quesCntr, ansCntr, nsCntr, authCntr = UNPACK_FORMAT.unpack_from(received_msg)

        offset = UNPACK_FORMAT.size

        #Unpack every question in the DNS request
        for x in range(quesCntr):
            domain_name, offset = unpack_labels(received_msg, offset)

            ques_type, ques_class = UNPACK_QUESTION_FORMAT.unpack_from(received_msg, offset)
            offset += UNPACK_QUESTION_FORMAT.size

            question = {"NAME": domain_name,
                        "TYPE": ques_type,
                        "CLASS": ques_class}

            questions.append(question)

        #Retrieving DNS packet details
        decoded_packet = {"id": tid, "questions": questions}
        decoded_packet_id = decoded_packet['id']
        decoded_packet_questions = decoded_packet['questions']
        decoded_packet_domain_name = decoded_packet_questions[0]
        domain_name = decoded_packet_domain_name['NAME']
        domain_name_in_packet = ".".join(domain_name)

        #Send the DNS response if domain name is valid
        if (domain_name_in_packet == given_domain_name):
            ip_address = fetch_best_replica(client_ip)
            response_packet = build_response_packet(domain_name_in_packet,ip_address,decoded_packet_id)
            send = sockfd.sendto(bytes(response_packet), 0, (client_ip,client_address_port[1]))

            if send <= 0:
                print "sending response failed"

        else:
            print "Received Invalid Domain Name"


    #Stop server on Keyboard interrupt
    except KeyboardInterrupt:
        print "Server stopped\n"
        sys.exit()


#Server running
domain_name = []
expiry_time = timeit.default_timer()


while True:
    if (timeit.default_timer() - expiry_time >= 900):
        recompute_best_replicas()                      # 500 seconds have elapsed, so the cache table needs to be recomputed
    main_function()

