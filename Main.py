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
    baseDir = "/apps/code/argo/"
    logDir = "/apps/web/logs/microservices/"
    msDetail = {
        "config":{
            "port":8083
        },
        "auth":{
            "port":8500
        },
        "suppliergateway":{
            "port":8000
        },
        "admingateway":{
            "port":7000
        },
        "supplier":{
            "port":8081
        },
        "solicitation_collector":{
            "port":8091
        },
        "solicitation_processor":{
            "port":8094
        },
        "company_node":{
            "port":8099
        },
        "notification":{
            "port":8026
        },
        "survivor":{
            "port":8101
        },


    }
    microservices = ["config",'auth','gateway','admingateway','company_node','suppliergateway',"supplier","notification","solicitation_collector","solicitation_processor","survivor"]
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

    def getSysConfig(self, section, key):
        config = configparser.ConfigParser()
        config.read('/etc/aageno/data.ini')
        return config[section][key]

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

    def searchprocess(self,name):
        processids = []
        for proc in psutil.process_iter(attrs=['pid', 'name','cmdline']):
           if re.search(name, str(proc.info['cmdline']), re.IGNORECASE):
               print str(proc.pid) + " " +str(proc.info['name'])
               print "\t"+str(proc.info['cmdline'])
               processids.append(proc.pid)

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

    def log(self, title, story):
        from elasticsearch import TransportError
        from elasticsearch import Elasticsearch

        note = {}
        note["maintag"] = title
        note["body"] = story

        es = Elasticsearch([self.getSysConfig('aageno_app', 'elasticSearchUrl')])
        if len(title) > 0:
            print "Indexing with title " + title
            try:
                es.index(index="brahman", doc_type='note', id=title, body=note)
            except TransportError as e:
                print(e.info)
        else:
            print "Indexing with title : " + title
            es.index(index="brahman", doc_type='note', body=note)

        print "Your story has been saved"

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

    def bidsynctest(self,file):
           dir = ''
           fileNameWithoutExtension = ''
           if file == 'cas':
               dir = "/apps/code/bidsync/bidsync-cas"
           elif file == 'dao':
               dir = "/apps/code/bidsync/bidsync-dao"
           elif file == 'notification':
               dir = "/apps/code/bidsync/notification"
           elif file == 'business':
               dir = "/apps/code/bidsync/business"
           else:
               if file.find(".java") == -1:
                   pattern = str(file) + ".java"
               else:
                   pattern = file

               path = str(self.runCommandAndReturnOutput(['find', '/apps/code/bidsync', '-name', pattern])).strip()

               dashPositions = [pos for pos, char in enumerate(path) if char == "/"]

               dir = path[0:dashPositions[4] + 1]

               fileNameWithoutExtension = os.path.splitext(os.path.basename(file))[0]

           os.chdir(dir)

           if fileNameWithoutExtension != '':
               if fileNameWithoutExtension.endswith("NG"):
                   prefix = path[path.find("com"):dashPositions[len(dashPositions) - 1]].replace("/", ".")
                   self.runAndPrintCommand(['ant', 'test', '-Dtestclass=' + prefix + "." + fileNameWithoutExtension])
               else:
                   self.runAndPrintCommand(['ant', 'test', '-Dtestclass=' + fileNameWithoutExtension])
           else:
               self.runAndPrintCommand(['ant', 'test'])

           print "Opening the test results : "
           self.runAndPrintCommand(['open', 'target/test/reports/index.html'])

    def start(self,*names):
        for ms in names:
            if str(ms).isdigit():
                ms = self.microservices[ms]
            if self.validms(ms):
                microservice = ms
                jarfile = microservice
                directory = microservice
                logoutput = microservice
                print "Starting : "+str(microservice)
                baseCommand  = "java -jar  -Xmx128m  -Dspring.profiles.active=dev -Dlogging.config=/apps/code/argo/{3}/src/main/resources/logback.xml  /apps/code/argo/{0}/target/{1}.jar > /apps/web/logs/microservices/{2}.log &"
                print baseCommand.format(directory,jarfile,logoutput,microservice)
                os.system(baseCommand.format(directory,jarfile,logoutput,microservice))
                self.checkUpStatus(microservice)

    def runbase(self):
        baseMsArr = ['config','auth','gateway','suppliergateway','supplier']
        for ms in baseMsArr:
            isUp = self.isUp(ms)
            print isUp
            if self.isUp(ms) == True:
                print "Starting {0}".format(ms)
            else:
                print "{0} is already up".format(ms)
            print "\n"

    def status(self,*microservices):
        for ms in microservices:
            if str(ms).isdigit():
                ms = self.microservices[ms]

            if str(ms) == "all":
                self.statusAll()
                return

            if self.validms(ms):
                msDetail = self.msDetail[str(ms)]

                try:
                    port = msDetail["port"]
                    print "Microservice : {0} ".format(ms)
                    print "Port : {0}".format(port)
                    response = requests.get("http://localhost:{0}/ready".format(port))
                    if response:
                        print response.text
                        self.printSuccess("{0} is up".format(ms))
                        print "PID : {0}".format(self.inport(port)[0])
                    else:
                        self.printError("{0} is down".format(ms))

                except ConnectionError as e:
                    self.printError("{0} is down.".format(ms))


    def stop(self,ms):
        if str(ms).isdigit():
            ms = self.microservices[ms]

        if str(ms) == "all":
            self.stopAll()
            return
        if self.validms(ms):
            msDetail = self.msDetail[str(ms)]
            port = msDetail["port"]
            self.killport(port)
            print "\n"
            self.status(ms)

    def stopAll(self):
        for ms in self.msDetail:
            self.stop(ms)
            print "\n"

    def statusAll(self):
        for ms in self.msDetail:
            self.status(ms)
            print "\n"

    def restart(self,ms):
        if self.validms(ms):
            self.stop(ms)
            self.start(ms)


    def printError(self,msg):
        print '\033[91m' + msg + '\033[0m'


    def printSuccess(self,msg):
        print '\033[92m' + msg + '\033[0m'

    def install(self,ms):
        if str(ms).isdigit():
            ms = self.microservices[ms]
        if self.validms(ms):
            dir = self.baseDir+ms
            os.chdir(dir)
            os.system("mvn install -DskipTests")

    def cleanbuild(self,ms):
        if str(ms).isdigit():
            ms = self.microservices[ms]
        if self.validms(ms):
            dir = self.baseDir+ms
            os.chdir(dir)
            os.system("mvn -DskipTests clean package")


    def refresh(self,ms):
        self.stop(ms)
        self.cleanbuild(ms)
        self.start(ms)

    def list(self):
        for index,ms in enumerate(self.microservices):
            print str(index)+" "+ms

    def log(self,ms):
        if str(ms).isdigit():
            ms = self.microservices[ms]
        if self.validms(ms):
            os.system("tail -1000f {0}{1}.log".format(self.logDir,ms));
        if ms == 'kafka':
            os.system("tail -1000f {0}{1}.log".format(self.logDir,'kafka'));
        if ms == 'zoo':
            os.system("tail -1000f {0}{1}.log".format(self.logDir,'zookeeper'));

    def test(self,ms):
        if str(ms).isdigit():
            ms = self.microservices[ms]
        if self.validms(ms):
            dir = self.baseDir+ms
            os.chdir(dir)
            os.system("mvn test")


    def validms(self,ms):
        if str(ms).isdigit():
            ms = self.microservices[ms]
        if ms in self.microservices:
            return True
        else:
            print "The service {0} doesnot exist. Here is the list".format(ms)
            self.list()
            return False

    def checkUpStatus(self,ms):
        i = 0;
        while i < 500:
            i = i+1
            try:
                port = self.msDetail[str(ms)]["port"]
                response = requests.get("http://localhost:{0}/ready".format(port))
                if response:
                    self.printSuccess("\n{0} is up and running. PID : {1}".format(ms,self.inport(port)[0]))

                    return True
                else:
                    return False
            except ConnectionError as e:
                sys.stdout.write(str(i)+' ')
                sys.stdout.flush()
            sleep(1)
        return False

    def todo(self):
        self.note('todo')

    def accounts(self):
        self.note('accounts')

    def arch(self):
        self.note('arch');

    def codegen(self):
        command = "java  -cp /apps/code/argo/swagger-codegen/target/ArgoRestGenerator-1.0.0.jar com.periscope.argo.codgen.Generator  -Dlogging.config=file:/apps/code/argo/swagger-codegen/target/classes/logback.xml -i /apps/code/argo/swagger-codegen/src/main/resources/input/suppliergateway/api/solicitation_collector/v1/solicitation_collector.json -c /apps/code/argo/swagger-codegen/src/main/resources/input/suppliergateway/api/solicitation_collector/v1/solicitation_collector.options  -l periscopers -o /apps/code/argo/swagger-codegen "
        os.system(command);

    def parsehub(self):
        response = requests.get("https://www.parsehub.com/api/v2/projects?api_key=tPPU11EGQbxa")
        responseJson = json.loads(response.text)
        total = responseJson["total_projects"]
        offset = 0
        limit = 10
        while offset < total:
            print offset
            response = requests.get("https://www.parsehub.com/api/v2/projects?api_key=tPPU11EGQbxa&limit={0}&offset={1}".format(limit,offset))
            responseJson = json.loads(response.text)
            allProjects = responseJson["projects"]
            for project in allProjects:
                token = project["token"]
                print token
                self.downloadBids(str(token));
            offset = offset + limit





    def downloadBids(self,token):
        from elasticsearch import Elasticsearch,TransportError

        url = "https://www.parsehub.com/api/v2/projects/{0}/last_ready_run/data?api_key=tPPU11EGQbxa".format(token)
        response = requests.get(url)
        print "URL "+url
        print "Status Code : "+token+" : "+str(response.status_code)
        if response.status_code == 200:
            responseJson = json.loads(response.text);
            bids = []
            self.recurJsonRead(responseJson,bids)
            thread_list = []
            for bid in bids:
                self.indexBid(bid,token)
        else:
            print response.text

    def recurJsonRead(self,json,bids):
        from elasticsearch import TransportError
        from elasticsearch import Elasticsearch

        if isinstance(json,dict) and ( "bid_number" in json or "bid_title" in json or "end_date" in json):
            print "Bid Data"+str(json)
            bids.append(json)
        else:
            if isinstance(json,dict) or isinstance(json,list):
                for key in json:
                    if isinstance(json,dict):
                        self.recurJsonRead(json[key],bids);
                    if isinstance(json,list):
                        self.recurJsonRead(key,bids)


    def indexBid(self,bidJson,token):
        from elasticsearch import TransportError
        from elasticsearch import Elasticsearch

        bidJson["token"] = token
        bidJson["downloaded_at"] = datetime.date.today().strftime("%Y-%m-%d")
        es = Elasticsearch(["http://afescluster.bidsync.com:9200"])
        try:
            es.index(index="argo", doc_type='collectedbid',  body=bidJson)
        except TransportError as e:
            print(e.info)

    def startKafka(self):
        os.system("/apps/code/argo/kafka-zoo/bin/kafka-server-start.sh /apps/code/argo/kafka-zoo/config/server.properties > /apps/web/logs/microservices/kafka.log &");

    def stopKafka(self):
        os.system("/apps/code/argo/kafka-zoo/bin/kafka-server-stop.sh");

    def startZoo(self):
        os.system("/apps/code/argo/kafka-zoo/bin/zookeeper-server-start.sh /apps/code/argo/kafka-zoo/config/zookeeper.properties > /apps/web/logs/microservices/zookeeper.log &");

    def stopZoo(self):
        os.system("/apps/code/argo/kafka-zoo/bin/zookeeper-server-stop.sh");

    def timeCheck(self,input):
        t = datetime.datetime.fromtimestamp(float(input)/1000.)
        fmt = "%Y-%m-%d %H:%M:%S"
        print t.strftime(fmt)

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


