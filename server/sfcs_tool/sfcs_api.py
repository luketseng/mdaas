#!/usr/bin/python3
import requests
import re

from lxml import etree

class SFCS_API():
    def __init__(self, IP, ServerType='tester'):
        if ServerType.lower() == 'basic':
            self.url="http://{}/basic.webservice/WebService.asmx".format(IP)
            self.serverPattern="http://localhost/Basic.WebService/WebService"
        else:
            self.url="http://{}/Tester.webservice/WebService.asmx".format(IP)
            self.serverPattern="http://localhost/Tester.WebService/WebService"
        self.method=''
        self.requestContent=''

    def fetchInfo(self, xmltree):
        ## The function is used for getting or upload Information to SFCS.
        self.requestContent=xmltree.replace(self.method, 
                '{} xmlns="{}"'.format(self.method, self.serverPattern), 1)
        #header={
        #'Content-Type': 'text/xml; charset=utf-8'
        #}
        body="""<?xml version="1.0" encoding="utf-8"?>
        <soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
        <soap12:Body>
            {}
        </soap12:Body>
        </soap12:Envelope>""".format(self.requestContent)
        header={
        'Content-Type': 'text/xml; charset=utf-8'
        }
        try:
            res=requests.post(self.url, data=body, headers=header)
        except ConnectionError:
            print('[*] Connecting host is fail, please check network connection')
        if res.status_code == 200:
            print("[*] Query successes. return code: [{}]".format(res.status_code))
            res.encoding='utf-8'
            self.QueryResult=res.content
            self.content=res.content
            content=re.findall('<{}Response.+?>.+?</{}Response>'.format(self.method, self.method), \
                self.QueryResult.decode('utf8'))[0]
            self.xmltree=etree.fromstring(content)
        else:
            print("[*] Query fail. return code: [{}]".format(res.status_code))

    def findElemXML(self, element):
        results=self.xmltree.xpath('//*[local-name()="{}"]'.format(element))[0].text
        return results

    def unpackXML(self, tree=None):
        if tree == None:
            tree=self.xmltree
        try:
            tag=tree.tag.split('}')[1]
        except IndexError:
            tag=tree.tag
        print("tag:", tag)
        if tree.getchildren() != []:
            treeItem={}
            treeList=[]
            for subtree in tree.getchildren():
                if tag == 'USNItems':
                    treeList.append(self.unpackXML(subtree))
                else:
                    treeItem.update(self.unpackXML(subtree))
                    print(treeItem)
            if tag == 'USNItems':
                return {tag: treeList }
            else:
                return {tag: treeItem }
        else:
            print("text:", tree.text)
            return {tag: tree.text}

    def constructXML(self, insertDict):
        if type(insertDict) != dict:
            return
        lebelString=''
        for key in insertDict.keys():
            if type(insertDict[key]) == dict:
                lebelString+=r'<{}>{}</{}>'.format(key, self.constructXML(insertDict[key]), key)
            else:
                lebelString+=r'<{}>{}</{}>'.format(key, insertDict[key], key)
        return lebelString

    ## list Methold's requirement with a dict
    def listMethodRequriement(self, method):
        res=requests.get(url="{}?op={}".format(self.url, method))
        if res.status_code == 200:
            ## return list
            xmltree=etree.HTML(res.content)
            string=''.join([ i.replace('\r\n', '') for i in xmltree.xpath('//span[2]/pre[1]/text()') ])
            try:
                string=re.findall('<{}.+?>.+?</{}>'.format(method, method), string)[0]
                self.xmltree=etree.fromstring(string)
                return self.unpackXML()
            except:
                print("[*] Can not get methold list, please contact developer.")
                return None
        else:
            print("[*] Can not get methold list, please contact developer.")
            return None

    ########################### Metholds ###########################
    def FetchMethodList(self):
        ## stage1
        res=requests.get(self.url)
        if res.status_code == 200:
            xmltree=etree.HTML(res.content)
            methodList=[i.replace(r'WebService.asmx?op=', '') for i in xmltree.xpath("//ul/li/a/@href")]
            for m in methodList:
                try:
                    print(m)
                    #print('  -- {}'.format(self.listMethodRequriement(method=m)))
                except etree.XMLSyntaxError as err:
                    print("That is not a nice xml file, it can not be decoded.")
                    continue
        else:
            print("[*] Can not get methold list, please contact developer.")
            return

    def Action(self, Method, InsertDict={}):
        if InsertDict == {}:
            return self.listMethodRequriement(method=Method)
        else:
            self.method=Method
            self.fetchInfo(self.constructXML(InsertDict))
            return self.unpackXML()

    ############################# API #############################
    def CheckRoute(self, UnitSerialNumber, StageCode):
        ## Items forms:
        ##     UnitSerialNumber: String
        ##     StageCode       : String
        self.method='CheckRoute'
        insertDict={self.method: {'UnitSerialNumber': UnitSerialNumber,'StageCode': StageCode}}
        self.fetchInfo(self.constructXML(insertDict))
        return self.unpackXML()

    def GetUPNInformation(self, UnitSerialNumber, StageCode, InfoName, InfoValue):
        ## Items forms:
        ##     UnitSerialNumber   : String
        ##     StageCode:         : String
        ##     InfoName           : String
        ##     InfoValue          : String

        self.method='GetUPNInformation'
        insertDict={self.method: {'UnitSerialNumber': UnitSerialNumber,
                                  'StageCode': StageCode,
                                  'InfoName': InfoName,
                                  'InfoValue':InfoValue,
                                 }
                  }
        self.fetchInfo(self.constructXML(insertDict))
        return self.unpackXML()
