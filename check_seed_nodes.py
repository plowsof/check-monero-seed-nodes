import sys
import socket
import socks
import requests
import pprint
from datetime import datetime

from levin.section import Section
from levin.bucket import Bucket
from levin.ctypes import *
from levin.constants import P2P_COMMANDS, LEVIN_SIGNATURE

testnet_id= b'\x12\x30\xF1\x71\x61\x04\x41\x61\x17\x31\x00\x82\x16\xA1\xA1\x11'
stagenet_id= b'\x12\x30\xF1\x71\x61\x04\x41\x61\x17\x31\x00\x82\x16\xA1\xA1\x12'
default_net_node = "https://raw.githubusercontent.com/monero-project/monero/master/src/p2p/net_node.inl"

def check_ip(host,ip):
    global testnet_id,stagenet_id
    network = None
    if str(ip).startswith("3"):
        network = stagenet_id
    if str(ip).startswith("2"):
        network = testnet_id
    try:
        sock = socket.socket()
        if "onion" in host:
            socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", 9050, True)
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
    global default_net_node
    args = sys.argv
    if len(args) == 2:
        default_net_node = args[1]
        # overwrite net_node with file at url
    r = requests.get(default_net_node)
    lines = r.iter_lines(decode_unicode=True)
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
        if "onion" in line:
            nodes.append(line.split("\"")[1])

    statuses = {}
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
            statuses[node] = "😡"
        else:
            statuses[node] = "🙂"
    parse_readme(statuses)

def parse_readme(statuses):
    # current dateTime
    now = datetime.now()
    date_time_str = now.strftime("%Y-%m-%d")
    with open("../readme.md", "r") as f:
        lines = f.readlines()
    # get existing statuses then clean the slated
    do=1
    new_file=""
    with open("../readme.md" ,"w") as f:
        for line in lines:
            print(line)
            if "|---|" in line:
                do = 0
                f.write(line)
                new_file+=line
                continue
            if not line.strip() and do == 0:
                print("blank line and do=0")
                do = 1
            if do == 0:
                node = line.split("|")[1]
                status = line.split("|")[2]
                if node in statuses:
                    statuses[node] = status + statuses[node]
                    if len(statuses[node]) > 7:
                        statuses[node] = statuses[node][1:]
            if do == 1:
                print(f"writing line")
                f.write(line)
                new_file+=line

    with open("../readme.md" ,"w") as f:
        for line in new_file.splitlines():
            line+="\n"
            if "|---|" in line:
                f.write(line)
                for node in statuses:
                    f.write(f"|{node}|{statuses[node]}|\n")
                f.write(f"\nLast update: {date_time_str}\n")
                continue
            if "Last update:" not in line:
                f.write(line)
    
main()