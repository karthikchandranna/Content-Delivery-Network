#!/usr/bin/env python

import socket
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import zlib
import os
import sqlite3
from SocketServer import ThreadingMixIn
from threading import Thread
import httplib2
import sys
import subprocess

#Retrieving port number and origin name from command-line
if (len(sys.argv) == 5):
    PORT_NUMBER = int(sys.argv[2])
    ORIGIN_NAME = sys.argv[4]
else:
    print "Program exit due to invalid command line arguments"
    sys.exit()

# Setting the port for DNS-HTTP communication
DNS_PORT_NUMBER = PORT_NUMBER + 50

#Finding our host name
HOST_NAME = socket.getfqdn()

dns_ip = socket.gethostbyname('cs5700cdnproject.ccs.neu.edu')

#Creating a cache table if it does not exist
if not os.path.exists("MainCacheFile"):
    conn = sqlite3.connect('MainCacheFile')
    c = conn.cursor()
    c.execute('''CREATE TABLE cache_tbl (url text, content text, hitcount integer)''')
    conn.commit()
    conn.close()

#Defining a MyHandler class
class MyHandler(BaseHTTPRequestHandler):

    #Sending a HTTP HEAD message
    def do_HEAD(s):
        if (s.client_address[0] == dns_ip):
            print s.path[1:]
            client_ip = s.path[1:]
            scamper = subprocess.check_output("scamper -c 'ping -c 1' -i %s" % client_ip, shell=True)  # Using scamper for active measurement
            outputSplit = scamper.split('/')
            rtt = outputSplit[-3]
            s.send_response(200)
            s.send_header("Content-type",rtt)
            s.end_headers()

    #Sending a HTTP GET message
    def do_GET(s):
            s.send_response(200)
            conn = sqlite3.connect('MainCacheFile')     # Connecting to MainCacheFile
            url_tuple = (s.path,)

            c = conn.cursor()

            c.execute('SELECT content FROM cache_tbl WHERE url=?', url_tuple)
            fetched_data = c.fetchone()

            s.send_header("Content-type", "text/html")
            s.end_headers()

            #Retrieving the file if present in cache
            if (fetched_data != None):
                print "Request being served from cache"
                s.wfile.write(zlib.decompress(fetched_data[0]))
                c.execute('UPDATE cache_tbl SET hitcount = hitcount+1 WHERE url = ?', url_tuple)

            #Requesting the file from origin and storing it in cache
            else:
                #Request to origin
                resobj = httplib2.Http()
                head, contents = resobj.request("http://"+ORIGIN_NAME+":8080"+s.path)

                s.wfile.write(contents)

                print "Requested page being fetched from origin server"
                #Checking the cache size
                stat = os.stat('MainCacheFile')
                cacheFileDiskUsage = (stat.st_blocks * 512) / 1024   # In KB

                sizeOfContent = (int(head['content-length'])/1024)         # In KB

                #Inserting the file into cache if possible
                if (sizeOfContent < 200):
                    if (sizeOfContent + cacheFileDiskUsage <= 9000):
                        c.execute('INSERT INTO cache_tbl VALUES (?,?,1)',(s.path,(buffer(zlib.compress(contents)))))
                    else:
                        c.execute('DELETE FROM cache_tbl WHERE url = (SELECT url FROM cache_tbl WHERE hitcount = (SELECT MIN(hitcount) FROM cache_tbl) LIMIT 1)')
                        c.execute('INSERT INTO cache_tbl VALUES (?,?,1)',(s.path,(buffer(zlib.compress(contents)))))

            conn.commit()
            conn.close()

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """ Server starts """

def serve_at_port(port_no):
    httpd = ThreadedHTTPServer((HOST_NAME, port_no), MyHandler)
    try:
        #Serving the requested web content
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass

    httpd.server_close()

    print "Stopped the server"

# Thread to listen to DNS communication
t=Thread(target=serve_at_port, args=[DNS_PORT_NUMBER])
t.daemon = True
t.start()

# Start server at the given port number
serve_at_port(PORT_NUMBER)

