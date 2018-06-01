import configparser
import fire
import glob
import json
import os
import re
import requests
import subprocess
import threading
import csv
import docker
import sys
import psutil
import datetime
from time import sleep
from requests.exceptions import ConnectionError


class Kanchi(object):
    def help(self):
        print "camerafix | note | notebackup | processinport | killport | apitest(filename) | "
        print "apiLoadTest(filename,threadsCount,Loop) | parseTables | rundDocker | listDockers"

    def runAndPrintCommand(self, command):
        action = subprocess.Popen(command, stdout=subprocess.PIPE)
        output = action.communicate()[0]
        print output
    def runCommandAndReturnOutput(self,command):
       action = subprocess.Popen(command, stdout=subprocess.PIPE)
       return action.communicate()[0]


    def notebackup(self):
        os.chdir(self.getSysConfig('aageno_app', 'aagenoBase') + '/notes/')
        self.runAndPrintCommand(['./brahman.py'])

    def camerafix(self):
        print "sudo killall VDCAssistant";
        self.runAndPrintCommand(['sudo', 'killall', 'VDCAssistant'])

    def processes(self):
        for proc in psutil.process_iter(attrs=['pid', 'name','cmdline']):
          print(proc.pid)
          print "\t"+str(proc.info['name'])
          print "\t"+str(proc.info['cmdline'])


    def killKafkaProcesses(self):
        processids = []
        for proc in psutil.process_iter(attrs=['pid', 'name','cmdline']):
           if str(proc.info['name']) == 'java' and re.search('kafka', str(proc.info['cmdline']), re.IGNORECASE):
               print str(proc.pid) + " " +str(proc.info['name'])
               print "\t"+str(proc.info['cmdline'])
               os.system("kill -9 {0}".format(proc.pid));

    def killwfprocesses(self):
        processids = []
        for proc in psutil.process_iter(attrs=['pid', 'name','cmdline']):
           if str(proc.info['name']) == 'java' and re.search('standalone', str(proc.info['cmdline']), re.IGNORECASE):
               print str(proc.pid) + " " +str(proc.info['name'])
               print "\t"+str(proc.info['cmdline'])
               os.system("kill -9 {0}".format(proc.pid));



    def killport(self, port):
        for processid in self.inport(port):
            print "Port : " + str(port) + " Process : " + str(processid);
            subprocess.call(['kill','-9', processid])

    def inport(self, port):
        from subprocess import Popen, PIPE
        p1 = Popen(['lsof', '-i', ':' + str(port)], stdout=PIPE)
        processids = []
        for line in iter(p1.stdout.readline, ''):
            substrs = str.split(line);
            if (substrs[1].isdigit()):
                processids.append(substrs[1])

        return processids


    def note(self, helptopic):
        helpdir = self.getSysConfig('aageno_app', 'aagenoBase') + '/scripts/help/'
        if helptopic == 'options' or helptopic == '':
            files = glob.glob(helpdir + "*.txt")
            count = 0;
            line = ""
            for file in files:
                print os.path.splitext(os.path.basename(file))[0]


        else:
            if helptopic.find(".") == -1:
                file = helpdir + helptopic + '.txt';
            else:
                file = helpdir + helptopic;

            subprocess.call(['vi', file])

    def apitest(self, data_file):
        with open(data_file) as data_file:
            data = json.load(data_file)
            tests = []
            for test in data:
                if test["enabled"] == True:
                    print "############# START TEST  > " + test["id"] + " #################"
                    test["url"] = self.findAndReplace(test["url"], tests);
                    test["parameter"] = json.loads(self.findAndReplace(json.dumps(test["parameter"]), tests))
                    test["headers"] = json.loads(self.findAndReplace(json.dumps(test["headers"]), tests))
                    print "Request"
                    print "-----------------------"
                    print "## URL : " + test["url"] + "##"
                    print "## Method : " + test["method"] + "##"
                    print "## Param : " + str(test["parameter"]) + "##"
                    print "## Headers : " + str(test["headers"]) + "##"
                    print "-----------------------"


                    response = ""
                    if test["method"] == "PUT":
                        response = requests.put(str(test['url']), json=test["parameter"], headers=test["headers"])
                    elif test["method"] == "GET":
                        response = requests.get(str(test['url']), json=test["parameter"], headers=test["headers"])
                    elif test["method"] == "POST":
                        response = requests.post(str(test['url']), json=test["parameter"], headers=test["headers"])
                    elif test["method"] == "DELETE":
                        response = requests.delete(str(test['url']), json=test["parameter"], headers=test["headers"])

                    print "Response"
                    print "-----------------------"
                    print "Status code : " + str(response.status_code)

                    if response.text :
                        print response.text
                        try:
                            test["response"] = json.loads(response.text)
                            tests.append(test)
                        except ValueError:
                            test["response"] = response.text
                            tests.append(test)

                    print "############## END TEST ################"
                    print "\n\n\n\n\n"

    def apiLoadTest(self, file_name, threadcount, loopCount):
        start_time = time();
        for j in range(0, loopCount):
            thread_list = []

            for i in range(0, threadcount):
                t = threading.Thread(target=self.apitest, args=(str(file_name),))
                thread_list.append(t)

            for thread in thread_list:
                thread.start()

            for thread in thread_list:
                thread.join()

        end_time = time();
        print str(end_time - start_time) + " : seconds"

    def findAndReplace(self, val, tests):
        matches = re.findall("{{(.*?)}}", str(val))
        if (len(matches) > 0):
            for param in matches:
                #param = matches[0]
                newVal = ""
                values = param.split(":")
                if len(tests) > 0:
                    for test1 in tests:
                        if test1['id'] == values[0]:
                            paths = values[1].split(".")
                            if len(paths) > 1:
                                newVal = str(test1[paths[0]][paths[1]])
                            else:
                                newVal = str(test1[paths[0]])
                if len(newVal) > 0:
                    val = str(val).replace("{{" + param + "}}", newVal)
        return val;

    def debug(self, debug, message):
        if debug:
            print message

    def parseTables(self, filename,tocsv=False, debug=False):
        try:
            file_object = open(filename, "r")
            fullFile = file_object.read()
            dbRows = fullFile.split("\n")
            fields = []
            for dbRow in dbRows:
                if (len(dbRow.strip()) > 0):
                    field = {}
                    self.debug(debug, dbRow)
                    field["orig"] = dbRow
                    field["name"] = dbRow[:dbRow.index(" ")]
                    if ("NOT NULL" in dbRow):
                        field["nullable"] = "no"
                        dbRow = dbRow.replace("NOT NULL", "")
                    else:
                        field["nullable"] = "yes"
                    if "|" in dbRow:
                        field["type"] = dbRow[dbRow.index(" "):dbRow.index("|")].strip()
                        field["comment"] = dbRow[dbRow.index("|")+1:].strip()
                    else:
                        field["type"] = dbRow[dbRow.index(" "):].strip()
                        field["comment"] = ""
                    fields.append(field);

        except IOError:
            print  "Error reading file"
        self.debug(debug,fields)
        if tocsv:
            self.toCSV(filename[:filename.index(".")]+".csv",fields)


    def toCSV(self, filename, list):
        with open("csv/"+filename, 'wb') as csvfile:
           spamwriter = csv.writer(csvfile, delimiter=',',
                            quotechar='"', quoting=csv.QUOTE_MINIMAL)

           spamwriter.writerow(["Name","Type","Nullable","Type","Comment"])
           for row in list:
             spamwriter.writerow([row["name"],row["type"],row["nullable"],row["comment"]])

    def runDocker(self):
       print base
       client = docker.from_env()
       print client.containers.run("alpine", ["echo", "hello", "world"])

    def listDockerContainers(self):
       client = docker.from_env()
       for container in client.containers.list():
         print container.id

    def stopAllDockerContainers(self):
        client = docker.from_env()
        for container in client.containers.list():
          container.stop()

    def statuses(self):
        print "Check to see if zookeeper and kafka are running"
        print "Check to see if Gateway is up"
        print "Check to see if SupplierUI, AgencyUI,AdmingUI are uo"
        print "Check to see if document and supplier gateway is up"


    def currentTimestamp(self):
        import time;
        #ts = datetime.datetime.now()
        ts = int(time.time())*1000
        print ts

    def uuid(self):
        import uuid
        print  str(uuid.uuid4())

    def openJson(self,file):
        os.system("python -m json.tool {}".format(file))



if __name__ == '__main__':
    fire.Fire(Kanchi)


