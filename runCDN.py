#!/usr/bin/env python

import subprocess
import sys
import threading

if (len(sys.argv) == 11):
    port = int(sys.argv[2])
    origin = sys.argv[4]
    domain = sys.argv[6]
    username = sys.argv[8]
    keyfile = sys.argv[10]
else:
    print "Program exit due to invalid command line arguments"
    sys.exit()

# List of replica servers
replica_list = ["ec2-54-174-6-90.compute-1.amazonaws.com",
                "ec2-54-149-9-25.us-west-2.compute.amazonaws.com",
                "ec2-54-67-86-61.us-west-1.compute.amazonaws.com",
                "ec2-54-72-167-104.eu-west-1.compute.amazonaws.com",
                "ec2-54-93-182-67.eu-central-1.compute.amazonaws.com",
                "ec2-54-169-146-226.ap-southeast-1.compute.amazonaws.com",
                "ec2-54-65-104-220.ap-northeast-1.compute.amazonaws.com",
                "ec2-54-66-212-131.ap-southeast-2.compute.amazonaws.com",
                "ec2-54-94-156-232.sa-east-1.compute.amazonaws.com"]

# Disable Host Key checking
hostcheck = "StrictHostKeyChecking"+"="+"no"

dns_server = "cs5700cdnproject.ccs.neu.edu"
my_dns = username+"@"+dns_server

# Running dnsserver on the DNS server
try:
    subprocess.Popen(['ssh','-o',"%s" % hostcheck,'-i',"%s" % keyfile,"%s" % my_dns,'./dnsserver','-p',"%i" % port,'-n',"%s" % domain],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
except:
    print "Failed to run DNS server"

# Running httpserver on all the replica servers
for replica in replica_list:
    my_replica = username+"@"+replica
    try:
        subprocess.Popen(['ssh','-o',"%s" % hostcheck,'-i',"%s" % keyfile,"%s" % my_replica,'./httpserver','-p',"%i" % port,'-o',"%s" % origin],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    except:
        print "Failed to run replica server"

print "CDN is now running... All servers waiting for requests..."
