#!/usr/bin/env python

import subprocess
import sys


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

dns_server = username+"@"+"cs5700cdnproject.ccs.neu.edu"+":~"
permission = "711"

dns_server_for_ssh = username+"@"+"cs5700cdnproject.ccs.neu.edu"

# Deploy dnsserver at DNS server
try:
    subprocess.call(['scp','-o',"%s" % hostcheck,'-i',"%s" % keyfile,'dnsserver',"%s" % dns_server])
    subprocess.Popen(['ssh','-o',"%s" % hostcheck,'-i',"%s" % keyfile,"%s" % dns_server_for_ssh,'chmod',"%s" % permission,'dnsserver'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
except:
    print "File transfer to DNS server failed"


# Deploy httpserver at all replica servers
try:
    for replica in replica_list:
        my_replica = username+"@"+replica+":~"

        replica_server_for_ssh = username+"@"+replica

        subprocess.call(['scp','-o',"%s" % hostcheck,'-i',"%s" % keyfile,'httpserver',"%s" % my_replica])    # Copying httpserver file to replica
        subprocess.Popen(['ssh','-o',"%s" % hostcheck,'-i',"%s" % keyfile,"%s" % replica_server_for_ssh,'chmod',"%s" % permission,'httpserver'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
except:
    print "File transfer to replica server failed"


print "CDN deployed successfully"
