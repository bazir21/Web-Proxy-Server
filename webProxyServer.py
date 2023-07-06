import socket, threading, time

PORT = 5000
cache = {}
blockedSites = {}
nonCachedTimings = {}
screenlock = threading.Semaphore(value = 1)

def handleInput(): # This function handles all of the user inputs
    inp = input("Please enter a command (or type ? to view commands): ")

    check = inp.find(" ")
    inps = inp.split(" ")

    if inp == "?":
        print("\nblock [host] -- This command blocks a certain host from loading, e.g: www.google.com")
        print("unblock [host] -- Unblocks a blocked website")
        print("stop -- Exits the management console and goes back to listening")
        print("exit -- Exits program entirely\n")

    elif inps[0] == "block": # If a website is blocked then it is added to a dictionary of blocked websites and sets them to be true, so that unblocking will be easier
        if check != -1:
            blockedSites[inps[1]] = True
            print(inps[1], "has been successfully blocked\n")
        else:
            print("Please either enter a website or format it correctly e.g: block www.google.com\n")

    elif inps[0] == "unblock":
        if check != -1:
            blockedSites[inps[1]] = False
            print(inps[1], "has been successfully unblocked\n")
        else:
            print("Please either enter a website or format it correctly e.g: unblock www.google.com\n")

    elif inp == "stop":
        return 0

    elif inp == "exit":
        return 1

    else:
        print("Sorry your command was not recognised, please try again\n")

    return 0

def parseData(data): # This function parses the data received by the client and returns a dictionary of all the important parts
    try:
        d = data.decode('utf-8', 'backslashreplace')
        firstline = d.split('\n')[0]
        method = firstline.split(' ')[0]
        url = firstline.split(' ')[1]

        httpPos = url.find("://")

        if httpPos == -1: # Takes out either the http:// or https:// part of the url
            tempHost = url # url does not contain a http:// or https://
        else:
            tempHost = url[(httpPos + 3):]
        
        portPos = tempHost.find(":") # checks if the url contains a port e.g: localhost:443

        hostPos = tempHost.find("/")
        if hostPos == -1:
            hostPos = len(tempHost)

        host = ""
        port = -1

        if portPos == -1 or hostPos < portPos: # if the url doesn't have a port then assign it the default port of 80
            port = 80
            host = tempHost[:hostPos]
        
        else: # otherwise give it the port it came with
            port = int ((tempHost[(portPos+1):])[:hostPos - portPos-1])
            host = tempHost[:portPos]

        return {
            "method" : method,
            "url" : url,
            "host" : host,
            "port" : port,
        }
    except Exception:
        return None

def http(s, connection, data, pData):
    try:
        start = time.time()

        s.settimeout(0.5)
        s.connect((pData["host"], pData["port"])) # connect socket to server
        s.sendall(data) # send data to socket

        cacheData = b""

        try:
            while True:
                resp = s.recv(4096) # constantly receive data until there is no more
                cacheData += resp # add parts of data to store in cache later

                if (len(resp) > 0):
                    connection.send(resp) # send data back to client
                else:
                    break # once data ends stop receiving data
        
        except socket.error:
            pass

        end = time.time()

        cache[pData["url"]] = cacheData # add aggregated data from server into cache
        nonCachedTimings[pData["url"]] = end - start # add timing to compare with cache time later

        print("Time taken with page not in cache = {}s".format(end - start), flush = True)
        print("This page added to cache = {}\n".format(pData["url"]), flush = True)
        screenlock.release()

        s.close()
        connection.close()

    except Exception:
        return

def https(s, connection, data, pData):
    try:
        establishPacket = "HTTP/1.0 200 Connection Established\r\nConnection: close\r\nProxy-agent: Pyx\r\n\r\n\r\n"
        connection.send(establishPacket.encode()) # send header to client to establish HTTPS connection
        s.connect((pData["host"], pData["port"]))
        s.setblocking(0)
        connection.setblocking(0)
        
        while True:
            try:
                req = connection.recv(4096) # constantly send and receive data from both client and server
                if (len(req) > 0):
                    s.send(req)
                else:
                    break
            except Exception:
                pass

            try:
                resp = s.recv(4096)
                if (len(resp) > 0):
                    connection.send(resp)
                else:
                    break
            except Exception:
                pass

    except Exception:
        return

def proxy(connection, address):
    try:
        data = connection.recv(4096) # receive incoming data
        pData = parseData(data) # parse data and return a dictionary for easy access

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        if blockedSites.get(pData["host"]) == True: # check if host website is blocked
            screenlock.acquire()
            print("Cannot connect to host as it is blocked\n", flush = True)
            screenlock.release()
            connection.sendall() # if blocked then don't send anything back to client
            connection.close()
            sock.close()
        else:
            if pData["method"] == "CONNECT": # check if the connection is HTTPS
                print("Address =", str(address), "\nMethod =", pData["method"], "\nHost =", pData["host"], "\nPort =", pData["port"], "\n", flush = True)
                https(sock, connection, data, pData) # enter HTTPS handling
            else:
                start = time.time()
                alreadyCached = cache.get(pData["url"])
                screenlock.acquire()
                print("Address =", str(address), "\nMethod =", pData["method"], "\nHost =", pData["host"], "\nPort =", pData["port"], flush = True)

                if alreadyCached is None: # check if page has been cached yet
                    http(sock, connection, data, pData) # if not then handle HTTP connection
                else:
                    print("Page found in cache", flush = True) # page has been found within cache
                    connection.send(alreadyCached) # load page from cache and send it to client
                    end = time.time()
                    print("Time taken with cache: {}s".format(end - start), flush = True) # return how long it took

                    nonCached = nonCachedTimings.get(pData["url"])
                    timetaken = start - end
                    print("Cached time is {}s faster than non-cached\n".format(nonCached - timetaken))
                    screenlock.release()

    except Exception:
        pass

def proxyServer():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # create a new socket to bind to browser
        s.bind(('', PORT))
        s.listen(5) # start listening for connections
        print("Server initialised! Listening for connections on port", PORT)
        print("Press Ctrl+C to enter management console\n")

        while True:
            try:
                (connection, address) = s.accept() # accept connection from client and return data

                t = threading.Thread(target = proxy, args = (connection, address)) # start threads and handle incoming connections
                t.daemon = True
                t.start()

                #proxy(connection, address)

            except KeyboardInterrupt: # ctrl+c to enter management console to block and unblock or exit
                inp = handleInput()
                if inp == 0:
                    pass

                elif inp == 1:
                    s.close()
                    print("Shutting Down...\n")
                    break

    except Exception as e:
        print(e)
        print("Unable to set up socket")
        s.close()

proxyServer()