#!/usr/bin/python
import os, struct

def s(i):
    return struct.pack('>H', i)
def b(i):
    return struct.pack('>B', i)
def us(i):
    return struct.unpack('>H', i)[0]
def ub(i):
    return struct.unpack('>B', i)[0]

SERVERS = []
SERV_CURR = 0

# DEFAULTS
TRANS_ID = us(os.urandom(2))
FLAGS_QR = 0 #Query
FLAGS_Opcode = 0 #Std query
FLAGS_AA = 0 #not an authority
FLAGS_TC = 0 #not truncated
FLAGS_RD = 1 #recurse please!
FLAGS_RA = 0 #recursion not allowed (or is a request)
FLAGS_Zero = 0 # always zero
FLAGS_RCode = 0 # no errors
FLAGS = 0

NUM_QUESTIONS = 1
NUM_ANSWERS = 0
NUM_AUTHORITY = 0
NUM_ADDITIONAL = 0

QType = 1 # A record
QClass = 1 # IN

def serverSetup():
    global SERVERS
    SERVERS = open('./servers.conf').read().split('\n')
    if SERVERS[-1] == '':
        SERVERS = SERVERS[:-1]

def genFlags(query):
    global FLAGS_QR, FLAGS_RA, NUM_ANSWERS, FLAGS
    if not query:
        FLAGS_QR = 1
        FLAGS_RA = 1
        NUM_ANSWERS = 1

    FLAGS_B1 = FLAGS_QR<<7 | FLAGS_Opcode <<3 | FLAGS_AA <<2 | FLAGS_TC <<1 | FLAGS_RD
    FLAGS_B2 = FLAGS_RA<<7 | FLAGS_RCode
    FLAGS = FLAGS_B1<<8 | FLAGS_B2

def genMessage(query_str, query=1):
    global SERV_CURR

    if not query and len(SERVERS) == 0:
        serverSetup()

    genFlags(query)

    message = s(TRANS_ID)+s(FLAGS)+s(NUM_QUESTIONS)+s(NUM_ANSWERS)+s(NUM_AUTHORITY)+ \
        s(NUM_ADDITIONAL)

    # Calc lengths for Query string
    lens = []
    i = 0
    while i in xrange(len(query_str)):
        k = 0
        for j in xrange(i,len(query_str)):
            if query_str[j] == '.':
                lens.append(k)
                break
            k += 1
        i = j+1
    lens.append(len(query_str)-lens[-1]-1)

    # Insert lengths and names into message
    message += b(lens[0])
    l = 1
    for i,c in enumerate(query_str):
        if c == '.':
            message += b(lens[l])
            l += 1
        else:
            message += struct.pack('c',c)
    message += b(0)

    message += s(QType)
    message += s(QClass)

    # build RR's
    if not query:
        RR_NAME = 49164 #C0 0C
        RR_QTYPE = 1 #A record
        RR_QCLASS = 1 #IN
        RR_TTL = 201 # C9 --> 3:21
        RR_DATALENGTH = 4
        RR_ADDR = SERVERS[SERV_CURR]
        SERV_CURR = (SERV_CURR + 1) % len(SERVERS)
        
        message += s(RR_NAME)+s(RR_QTYPE)+s(RR_QCLASS) + \
            struct.pack('>I',RR_TTL) + s(RR_DATALENGTH)
        RR_ADDR = [int(float(a)) for a in RR_ADDR.split('.')]
        for a in RR_ADDR:
            message += b(a)
    return message

def parseMessage(data, query=0):
    global TRANS_ID
    R_TRANS_ID = us(data[0:2])
    if query:
        TRANS_ID = R_TRANS_ID

    R_FLAGS = us(data[2:4])
    R_FLAGS_B1 = R_FLAGS >> 8
    R_FLAGS_B2 = R_FLAGS & 255

    R_FLAGS_QR = (R_FLAGS_B1 & 128) >> 7
    R_FLAGS_Opcode = (R_FLAGS_B1 & (15<<3)) >> 3
    R_FLAGS_AA = (R_FLAGS_B1 & 4) >> 2
    R_FLAGS_TC = (R_FLAGS_B1 & 2) >> 1
    R_FLAGS_RD = (R_FLAGS_B1 & 1)

    R_FLAGS_RA = (R_FLAGS_B2 & 128) >> 7
    R_FLAGS_Zero = (R_FLAGS_B2 & (7<<4)) >> 4
    R_FLAGS_RCode = R_FLAGS_B2 & 15

    R_NUM_QUESTIONS = us(data[4:6])
    R_NUM_ANSWERS = us(data[6:8])
    R_NUM_AUTHORITY = us(data[8:10])
    R_NUM_ADDITIONAL = us(data[10:12])

    R_INPUT = []
    i = 13
    l = ub(data[12])
    while l != 0:
        R_INPUT += data[i]
        i += 1
        l -= 1
        if l == 0:
            l = ub(data[i])
            i += 1
            R_INPUT += '.'
    R_INPUT = ''.join(R_INPUT[:-1])

    R_QType = us(data[i:i+2]) # A record
    i += 2
    R_QClass = us(data[i:i+2]) # IN
    i += 2

    # print R_FLAGS_QR, R_FLAGS_Opcode, R_FLAGS_AA, R_FLAGS_TC, R_FLAGS_RD
    # print R_FLAGS_RA, R_FLAGS_Zero, R_FLAGS_RCode
    # print R_NUM_QUESTIONS, R_NUM_ANSWERS, R_NUM_AUTHORITY, R_NUM_ADDITIONAL


    RR_ADDR = ""
    if R_NUM_ANSWERS:
        RR_NAME = us(data[i:i+2]) # should be C0 0C
        i += 2
        RR_TYPE = us(data[i:i+2]) # A record
        i += 2
        RR_CLASS = us(data[i:i+2]) # IN
        i += 2
        RR_TTL = (us(data[i:i+2])<<8) + (us(data[i+2:i+4]))
        i += 4
        RR_DL = us(data[i:i+2])
        i += 2
        addr = [ub(data[i:i+1]),ub(data[i+1:i+2]),ub(data[i+2:i+3]),ub(data[i+3:i+4])]
        addr = [str(a) for a in addr]
        RR_ADDR = '.'.join(addr)
        # print RR_NAME, RR_TYPE, RR_CLASS, RR_TTL, RR_DL


    return (R_INPUT, RR_ADDR)
