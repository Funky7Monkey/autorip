import os, sys, fcntl, csv
import subprocess
from enum import Enum
from tqdm import tqdm
import time

class Drive(Enum):
    none = 0
    no_disc = 1
    tray_open = 2
    not_ready = 3
    ready = 4

def discStatus(device):
    fd = os.open(device, os.O_NONBLOCK) or os.exit(1)
    status = fcntl.ioctl(fd, 0x5326)
    os.close(fd)
    return Drive(status)

def parser(line):
    csvparse = csv.reader([line], skipinitialspace=True)
    out = next(csvparse)
    front = out[0].split(':')
    out.pop(0)
    return front + out

def progress(cname, tname, cval, tval, mval):
    cper = cval / mval * 100
    tper = tval / mval * 100
    print("\033[K", end='')
    print("{0} - {1:6.2f}% {2:>30} - {3:6.2f}%\r".format(tname, tper, cname, cper), end='')

def discInfo(device):
    cbar = tqdm(total=65536, position=1)
    tbar = tqdm(total=65536, position=0)
    tqdm.write("Starting MakeMKV with " + device + "\n\n")
    proc = subprocess.Popen(['makemkvcon', '-r', '--noscan', '--progress=-stdout', 'info', 'dev:' + device], stdout=subprocess.PIPE)
    angle = []
    lengths = {}
    name = ""
    cprg = ""
    tprg = ""
    cval = 0
    tval = 0
    cval_prev = 0
    tval_prev = 0
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        line = parser(str(line)[2:-3])
        if line[0] == 'MSG':
            if line[1] in ['3025', '3309']:
                continue
            else:
                tqdm.write(line[4])
        elif line[0] == 'CINFO':
            if line[1] == '2': # makemkvcon code for ap_iaName
                name = line[3]
        elif line[0] == 'TINFO':
            if line[2] == '15': # makemkvcon code for ap_iaAngleInfo
                angle.append(line[1])
            elif line[2] == '9': # makemkvcon code for ap_iaDuration
                h, m, s = line[4].split(':')
                duration = int(h) * 3660 + int(m) * 60 + int(s)
                lengths[int(line[1])] = duration
        elif line[0] == 'PRGC':
            cbar.set_description(cprg, refresh=False)
            cprg = line[3]
        elif line[0] == 'PRGT':
            tbar.set_description(tprg, refresh=False)
            tprg = line[3]
        elif line[0] == 'PRGV':

            cval = int(line[1])
            if cval == 0:
                cbar.refresh()
                cbar.reset()
                cval_prev = cval
            elif cval == cval_prev:
                continue
            else:
                #tqdm.write("before: " + str(cbar.n))
                #tqdm.write("after:  " + str(cval - cval_prev))
                cbar.update(cval - cbar.n)
                cval_prev = cval

            tval = int(line[1])
            if tval == 0:
                tbar.refresh()
                tbar.reset()
                tval_prev = tval
            elif tval == tval_prev:
                continue
            else:
                tbar.update(tval - tbar.n)

    cbar.close()
    tbar.close()
    if (not angle) & (not lengths):
        title = '0'
    elif not angle:
        title = max(lengths, key=lengths.get)
    else:
        title = angle[0]
    return name, str(title)

def discRip(device, title, output):
    cbar = tqdm(total=65536, position=1)
    tbar = tqdm(total=65536, position=0)
    tqdm.write("Starting MakeMKV with " + device + " to " + output)
    proc = subprocess.Popen(['makemkvcon', '-r', '--noscan', '--progress=-stdout', 'mkv', 'dev:' + device, title, output], stdout=subprocess.PIPE)
    cprg = ""
    tprg = ""
    cval = 0
    tval = 0
    cval_prev = 0
    tval_prev = 0
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        line = parser(str(line)[2:-3])
        if line[0] == 'MSG':
            if line[1] in ['3025', '3307', '3309']:
                continue
            else:
                tqdm.write(line[4])
        elif line[0] == 'PRGC':
            cbar.set_description(cprg, refresh=False)
            cprg = line[3]
        elif line[0] == 'PRGT':
            tbar.set_description(tprg, refresh=False)
            tprg = line[3]
        elif line[0] == 'PRGV':

            cval = int(line[1])
            if cval == 0:
                cbar.refresh()
                cbar.reset()
                cval_prev = cval
            elif cval == cval_prev:
                continue
            else:
                #tqdm.write("before: " + str(cbar.n))
                #tqdm.write("after:  " + str(cval - cval_prev))
                cbar.update(cval - cbar.n)
                cval_prev = cval

            tval = int(line[1])
            if tval == 0:
                tbar.refresh()
                tbar.reset()
                tval_prev = tval
            elif tval == tval_prev:
                continue
            else:
                tbar.update(tval - tbar.n)

    cbar.close()
    tbar.close()

last_tray = ""

while True:
    device = sys.argv[1]
    save = sys.argv[2]
    tray = discStatus(device)
    if tray == Drive.ready:
        print("\033[K", end='')
        print("Drive is " + tray.name)
        name, title = discInfo(device)
        save = save + "/" + name
        try:
            os.mkdir(save)
        except FileExistsError as error:
            pass
        print("Ripping ", name)
        discRip(device, title, save)
        print("\a", end='')
        os.system('eject ' + device)
    elif tray == Drive.no_disc:
        print("\a", end='')
        print("No disc, ejecting")
        os.system('eject ' + device)
    else:
        if last_tray != tray:
            print("Waiting for disc. Drive is " + tray.name + "    \r", end='')
        time.sleep(5)
    last_tray = tray
