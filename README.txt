DESIGN DECISIONS:
==================
1.	Multi-threaded servers to handle multiple simultaneous requests.
2.	Active measurements using Scamper to determine the best replica.
3.	RTT as a measure of network performance.
4.	Caching clients in DNS server and web pages in HTTP server.
5.	Least-frequently used (LFU) algorithm as a cache replacement technique.


EFFECTIVENESS OF DESIGN DECISIONS:
==================================
1.	Multiple requests were sent simultaneously to check whether the servers could handle the simultaneous load. 
    Implementation of multi-threading made sure that the requests were handled fairly well. 
2.	We compared the effectiveness of Scamper with that of GeoIP. Although scamper is not as quick as ping, it still does better than GeoIP, 
    this proves that active measurement is a reliable and efficient method to determine the best replica.
3.	Implementation of caching produces a 90% decrease in the time it takes to serve the client.


IMPLEMENTATION:
===============

1. DNS Server:
==============
 
High-level approach:

We have implemented a multi-threaded DNS server which is capable of handling multiple simultaneous requests. Once the server receives the
DNS request query, it unpacks the packet and checks if the host-name to be resolved to IP Address is the same as the one given in the 
command line arguments. If yes, our DNS server uses Active Measurements to determine the best replica server for a given client. 
Active Measurements are computed by extracting the IP address of the client which has requested the DNS server for the IP of the Web Server.
The DNS Server sends this client IP address to each Replica Server in our CDN using a HTTP Head Message. The Replica Servers, on their end, 
will ping the client using Scamper Tool and compute the Round Trip Time (rtt). The rtt is sent back to the DNS Server in a HTTP Head Message. 
The DNS, after receiving rtt values from all the replicas, will compute the least rtt value and hence find the "best replica" for the client. 
The DNS Server now sends a DNS Response to the client with the IP address of the best replica server.
 
Performance enhancing techniques:
 
The DNS server will receive multiple requests from a client over a short span of time. So, we are caching the best replica for each client
for a period of 500 seconds. This way, any future request from a client will be serviced directly from cache instead of computing the 
best replica again. After 900 seconds the cache will be refreshed.

Initially, for the milestone of this project, we had used GeoIP to find the best replica. But this is not a good approach as the 
nearest replica might not give the best performance. Hence we are using Active Measurements to find the best replica. 
Active Measurements is used to find the replica server which gives the minimum rtt value to the client. 
Hence this is guaranteed to give better performance when compared to GeoIP.
 
Challenges:

1. Unpacking and packing the DNS packet.
2. Implementation of multi-threading to handle multiple requests. Multi-threading is also used to 
   refresh the cache in the background for every 900 seconds.


2. HTTP Server
==============

High-level approach:

We have designed a HTTP server that serves clients in an efficient way by caching the served content for future use.
We have implemented a multi-threading system which is capable of handling multiple simultaneous requests. 
Initially, we create a database file that contains a table to store the URL, content and hit-count of a page. 
Caching is implemented based on the Least-frequently-used (LFU) algorithm. When the server receives a HTTP GET request, 
it extracts the path and checks whether content exists in the database for that path. If yes, it retrieves the content 
and sends it to the client. It then increments the hit-count of that URL signifying a cache-hit. If not, it forwards the 
request to the origin server and sends the content received from the origin server to the client. Soon after it sends the
content to the client, it checks whether the content can be inserted into the database i.e. whether the content 
isn't too big (> 200KB). If that is possible, we check whether the total size of the database is less than 9000KB. 
If it is more than 9000KB, we remove the URL with the least hit-count from the database and insert the current URL, 
content and set the hit-count to 1. If it is less that 9000KB, we just insert the current URL, content and set the hit-count
to 1 without making any other changes to the database. When the server receives the client IP from the DNS server, it computes
the RTT to the given client IP and sends it back to the server as part of a HTTP HEAD response. The RTT is calculated through
active measurements by using the Scamper tool. The client is pinged by using Scamper.

Performance enhancing techniques:

1.	By implementing caching, we make sure that our server does not forward every request to the origin. A cache-hit means there 
    is a 90% decrease in the time it takes to serve the client.
2.	By implementing active measurements using scamper, we make sure that the server does not make more than 1 probe per second. 

Challenges:

1.	Testing whether the given disk quota has been exceeded. This was done by filling the cache to the maximum. 
    Error case was handled in the program.
2.	Testing whether the given RAM quota has been exceeded. This was done using the top command.


What we would do with more time:

1.	We would write a script on the client side to spawn multiple clients and flood the servers with requests and observe the behaviour. 
2.	We would have tried to implement passive measurements and evaluate their efficiency in comparison to active measurements.
