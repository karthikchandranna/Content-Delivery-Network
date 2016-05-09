#! /usr/bin/env python

import socket
import struct
import threading
import sys
import urllib
import pickle
import math
import os

#Format strings
UNPACK_FORMAT = struct.Struct("!6H")
UNPACK_QUESTION_FORMAT = struct.Struct("!2H")

#Creating socket
sockfd = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

#Retrieving port number and domain name from command-line 
if (len(sys.argv) == 5):
    port = sys.argv[2]
    port = int(port)
    given_domain_name = sys.argv[4]
    print given_domain_name
else:
    print "Invalid number of command line arguments... Exit"
    sys.exit()

#Finding the IP of our DNS server
dup_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
dup_sock.connect(("david.choffnes.com",80))
host_ip= dup_sock.getsockname()[0]
dup_sock.close()

#Binding the server to the given port
sockfd.bind((host_ip,port))

#Function to find the latitude and longitude of a given IP
def find_lat_long(ip):
    listLatLong = []
    replicaInfo = urllib.urlopen('http://api.ipinfodb.com/v3/ip-city/?key=9505bce04f15216600c655de73cbeaeef52fe2813d507d21a78baff693d7eb0c&ip='+ip).read()
    latLongReplica = replicaInfo.split(';')
    listLatLong.append(latLongReplica[-3])
    listLatLong.append(latLongReplica[-2])
    return listLatLong

#Creating the replica servers database if not present
if not os.path.exists("replica_geo"):
    print "Creating replica servers database. Please wait"

    replica_table = { "54.164.51.70":[99999999,99999999],
                      "54.174.6.90":[float(find_lat_long("54.174.6.90")[0]),float(find_lat_long("54.174.6.90")[1])],
                      "54.149.9.25":[float(find_lat_long("54.149.9.25")[0]),float(find_lat_long("54.149.9.25")[1])],
                      "54.67.86.61":[float(find_lat_long("54.67.86.61")[0]),float(find_lat_long("54.67.86.61")[1])],
                      "54.72.167.104":[float(find_lat_long("54.72.167.104")[0]),float(find_lat_long("54.72.167.104")[1])],
                      "54.93.182.67":[float(find_lat_long("54.93.182.67")[0]),float(find_lat_long("54.93.182.67")[1])],
                      "54.169.146.226":[float(find_lat_long("54.169.146.226")[0]),float(find_lat_long("54.169.146.226")[1])],
                      "54.65.104.220":[float(find_lat_long("54.65.104.220")[0]),float(find_lat_long("54.65.104.220")[1])],
                      "54.66.212.131":[float(find_lat_long("54.66.212.131")[0]),float(find_lat_long("54.66.212.131")[1])],
                      "54.94.156.232":[float(find_lat_long("54.94.156.232")[0]),float(find_lat_long("54.94.156.232")[1])] }

    print "Replica servers database created."

    pickle.dump( replica_table, open( "replica_geo", "wb" ) )

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

    packet += struct.pack("!I", 0)  # TTL (since geoIP is used)
    packet += struct.pack("!H", 4)  # Length

    #Building the answer
    split_ip = ip.split(".")
    for ip_part in split_ip:
        packet += struct.pack("!B", int(ip_part))

    return packet

#Function to find the best replica
def fetch_best_replica(client_ip):
    replica_table = pickle.load( open( "replica_geo", "rb" ) )
    min_dist = 99999999
    ip = ''
    #Find client's latitude and longitude
    lat_client = float(find_lat_long(client_ip)[0])
    longi_client = float(find_lat_long(client_ip)[1])

    #Find the ip with the least distance from the client
    for key in replica_table:
        distance = math.pow((replica_table[key][0] - lat_client),2) + math.pow((replica_table[key][1] - longi_client),2)
        if (distance <= min_dist):
            min_dist = distance
            ip = key

    return ip


#Main Function
def main_function():

    questions = []
    print "Waiting for data...",port

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
while True:
    main_function()
