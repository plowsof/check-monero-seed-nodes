import sys
import socket
import socks
import requests
import pprint
import os
import subprocess
import time

from levin.section import Section
from levin.bucket import Bucket
from levin.ctypes import *
from levin.constants import P2P_COMMANDS, LEVIN_SIGNATURE

testnet_id= b'\x12\x30\xF1\x71\x61\x04\x41\x61\x17\x31\x00\x82\x16\xA1\xA1\x11'
stagenet_id= b'\x12\x30\xF1\x71\x61\x04\x41\x61\x17\x31\x00\x82\x16\xA1\xA1\x12'
default_net_node = "https://raw.githubusercontent.com/monero-project/monero/master/src/p2p/net_node.inl"
i2pzero_zip = "i2p-zero-linux.v1.20"
i2pzero_url = f"https://github.com/i2p-zero/i2p-zero/releases/download/v1.20/{i2pzero_zip}.zip"

args = sys.argv
if len(args) == 2:
    # overwrite net_node with file at url
    r = requests.get(default_net_node)
    lines = r.iter_lines(decode_unicode=True)
else:
    with open("../net_node.inl","r") as f:
        lines = f.readlines()

def install_i2p():
    global i2pzero_url
    '''
    1. Unpack and navigate to i2p-zero-linux.vX.XX/router/bin.
    3. Launch the I2P-Zero process; ./launch.sh
    4. ???
    5. w00t!!
    '''
    
    r = requests.get(i2pzero_url)  
    with open('i2pzero.zip', 'wb') as f:
        f.write(r.content)

    os.system("unzip i2pzero.zip")
       
    i2p_server = subprocess.Popen(f"{i2pzero_zip}/router/bin/i2p-zero",stdout=subprocess.PIPE)
    for line in iter(i2p_server.stdout.readline,''):
        print(line)
        if b"router now ready to create" in line:
            break

    i2p_socks = subprocess.Popen([f"{i2pzero_zip}/router/bin/tunnel-control.sh", "socks.create", "48085"])
    for line in iter(i2p_socks.stdout.readline,''):
        print(line)
        if "OK" in line:
            break

def check_ip(host,ip):
    global testnet_id,stagenet_id
    network = None
    if str(ip).startswith("3"):
        network = stagenet_id
    if str(ip).startswith("2"):
        network = testnet_id
    try:
        sock = socket.socket()
        if ".onion" in host:
            socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", 9050, True)
            sock = socks.socksocket()
        if ".i2p" in host:
            socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", 48085, True)
            sock = socks.socksocket()
        sock.settimeout(30)
        sock.connect((host,ip))
    except:
        #sys.stderr.write("unable to connect to %s:%d\n" % (host, ip))
        return False

    bucket = Bucket.create_handshake_request(network_id=network)

    sock.send(bucket.header())
    sock.send(bucket.payload())

    # print(">> sent packet \'%s\'" % P2P_COMMANDS[bucket.command])
    buckets = []
    while 1:
        buffer = sock.recv(8)
        if not buffer:
            #sys.stderr.write("Invalid response; exiting\n")
            return False

        if not buffer.startswith(bytes(LEVIN_SIGNATURE)):
            #sys.stderr.write("Invalid response; exiting\n")
            return False
        return True

def main():
    at_ipv4=0
    at_anon=0
    nodes = []
    for line in lines:
        if "::get_ip_seed_nodes()" in line:
            at_ipv4 = 1
        if "full_addrs.insert" in line and at_ipv4 == 1:
                nodes.append(line.split("\"")[1])
        if "return full_addrs;" in line and at_ipv4 == 1:
            at_ipv4 = 0
        if "onion" in line or "b32.i2p" in line:
            nodes.append(line.split("\"")[1])

    for node in nodes:
        host = node.split(":")[0]
        ip=node.split(":")[1]
        attempts = 0
        while attempts < 3:
            if check_ip(host, int(ip)):
                print(f"{node} online")
                attempts = 0
                break
            else:
                attempts+=1
        if attempts != 0:
            print(f"{node} offline")




install_i2p()
main()