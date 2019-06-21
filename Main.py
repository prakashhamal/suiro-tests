import configparser
import fire
import json
import os
import re
import requests
import subprocess
import threading
import csv

class Kanchi(object):

    def runAndPrintCommand(self, command):
        action = subprocess.Popen(command, stdout=subprocess.PIPE)
        output = action.communicate()[0]
        print output
    def runCommandAndReturnOutput(self,command):
       action = subprocess.Popen(command, stdout=subprocess.PIPE)
       return action.communicate()[0]

    def apitest(self, data_file):
        with open(data_file) as data_file:
            data = json.load(data_file)
            tests = []
            for test in data:
                if test["enabled"] == True:
                    print "############# START SUIRO TEST  > " + test["id"] + " #################"
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
                    print "Writing the test results in dir ".format(self._outputdir)
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


   


    def __init__(self,env='local',outputdir='.'):
        self._env = env
        self._outputdir = outputdir

if __name__ == '__main__':
    fire.Fire(Kanchi)
