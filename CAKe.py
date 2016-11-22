# written for python 2.7
#
# CAKe : 	CEF Army Knife experiment
#        	A versatile CEF manipulation and generation tool
#
# Author : 	Gaetan Cardinal
#               cardinal_gaetan |at| yahoo.fr
#
# Version: 	0.2
# Updated: 	Jan 2014
# 
#----------------------------------------------------------------------------
# The MIT License
#
#Copyright(c) 2014 Gaetan Cardinal
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import re, socket, sys, time, os, string, getopt, time, random, fileinput, struct
from datetime import date, datetime
from calendar import monthrange
from random import randrange
errormessage=currentoutputfile=''
writtenlines=1


##################################
### Custom Parameters
##################################

##### maxeps indicates the max value allowed for EPS.  You can increase it if your system is able to deal with higher speed
maxeps=50000

##### timeformat
# change the timeformat according to your need but don't use the column ':' character which is used as separator.
#If you introduce space character in the time format, you will have to double-quote absolute time values passed as argument.
timeformat='%d/%m/%Y-%H-%M-%S'

##### maxCEFmem
# max CEF events number to keep in memory before writing to file. Higher value could improve perf but would increase memory used
maxCEFmem=5000

##### default CEF format
# Format of a CEF event considered as being valid when found in a file, can be adapted to your needs
validCEFevt='^(CEF:)[^\|]*\|[^\|]*\|[^\|]*\|[^\|]*\|[^\|]*\|[^\|]*\|[^\|]*\|.*$'

##### syslog udp delay
# udpdelay is the time the script will wait between 2 batch of udp events being sent via syslog UDP.
# This parameter only matters when syslog output is selected with 'ud' value as protocol.
# For instance if udpdelay=0.001 and delaybatchsize=5, the script will wait for 1msec every 5 events sent via syslog/udp
udpdelay=0.001
delaybatchsize=5

##### default timestamp(s) to modify
# By default CAKe only modifies rt timestamp. If you want to modify a different or multiple timestamp, use -t option
# You should only change the list of timestamps hereunder if you want to modify the default behavior
timelist=['rt']

##### CEF output file size
# CEF output file size limit : define the max size for an output file. By default there is no limit (0). If you want to modify the max
# size you should use the -l option. You should only change the parameter hereunder if you want to modify the default file size value. 
outputfilesize=0 # in MB
outputfilesize=outputfilesize*1024*1024 # don't touch this --> conversion in bytes

##### csv header
# This is the default csv header which is going to be used to create a csv file. When a fieldname which is not part of the csv header
# is found, it will be added at the end of the csv header. If you want to force the order of the columns in the csv file, you can change
# the csvheader according to your needs. NB: it is allowed to use any field name in the csv header. If no value can be found for this
# field name, the column will be empty.
csvheaderlist=['cefVersion' , 'deviceVendor' ,'deviceProduct' ,'deviceVersion' ,'signatureId' ,'name' ,'severity', 'rt' ]
# mandatoryfieldlist contains all fields being part of the CEF header. This list should normally not be changed. If you remove fields from
# this list and if they are not listed in csvheaderlist, they will simply not be written down to your csv file.
mandatoryfieldlist=['cefVersion' , 'deviceVendor' ,'deviceProduct' ,'deviceVersion' ,'signatureId' ,'name' ,'severity']
# csv values. The csv file will be generated in such a way that the delimiter userd doesn't matter for the user (default delimiter different in US and Europe) if the csv is displayed in excel
# If you intent to use excel file, you should normally not change these values. However if experience problems you can modify the default delimiter and/or choose a replacement string when
# the delimiter is found in a value. 
csvqualifier='"'
csvdelimiter=',' # default csv delimiter. 
allowdelimiterinvalue="true" #if set to true, the original value is kept even if it contains the delimiter character. If set to true, the delimiter will be replaced by "replacementcsvdelimiter"
replacementcsvdelimiter=' '
# Hereunder you can define the range of IP addresses which can be used when sanitizing IP addresses with random IPs (  ip:rnd option)
rndipmin="0.0.0.1"
rndipmax="223.255.255.255"

##################################
### Procedures
##################################

### usage
def usage():
    mypluslen=len(errormessage)+7
    if mypluslen>95:
        mypluslen=95
    if mypluslen>7:
        print("\n")
        print ("+"*mypluslen)
        #print ("ERROR Found:\n")
        print ("ERROR: "+errormessage)
        print ("+"*mypluslen)
    print("""

Usage : CAKe.py <action> <action-type> <input> <output> [options]
=================================================================

action, action-type, input and output parameters are mandatory
action and action-type must be unique

<action>      : -g (--generate) : generate random CEF events based a template file
                -p (--play)     : play CEF events stored in file(s)
                
<action-type> : -r (--realtime) EPS
                    ex: -r 200
                -k (--keeptimestamp) EPS
                    ex: -k 200
                -c (--customtime) starttime:endtime:eventscount
                    ex: -c today-1d:now:10000
                        -c 1234567890:now:500
                    
                    Time format can be  epoch    : 10 digits starting with 1 (ex: 1234567890)
                                        absolute : format is """+timeformat+"""
                                                   must be double-quoted if format contains space
                                        relative : standard Arcsight format (ex: Now-1h)
                -n (--notimestamp) EPS
                    ex: -n 200
                                    
<input>       : -i (--inputfile) filename(s)
                    ex: -i /foo,/tmp/bar
                    Multi input files only allowed with play action but not with generate

<output>      : -o (--ceffile) CEF_filename
                -v (--csvfile) CSV_filename
                -d (--display) 
                -s (--syslog) destinationhost:port:protocol
                    ex: -s mysyslog:514:u
                    destination value can be IPv4 address or hostname
                    protocol value can be u (udp), t (tcp) or ud (udp delay)
                    
[options]     : -f (--force)               : doesn't prompt for confirmation before overwriting a file
                -t (--timetype) field      : list of timestamp to modify. Default is rt only.
                    ex: -t rt,art
                -l (--limitoutputsize) size: create a new output file when max file size is reached 
                    ex: -l 50                value in MB
                -b (--blend)               : blending CEF events output
                    ex: -b
                -w (--sanitize)            : remove sensitive data from CEF events
                    ex: -w ip:rm           : remove all "field=value" strings containing IP
                        -w ip:rnd          : replace all IP by random IPs
                        -w field:src,dst   : remove the "field=value" string if field=src or field=dst
                        -w value:foo,bar   : remove the "field=value" string if value contains foo or bar
                        -w header:foo,bar  : remove all occurrences of "foo" and "bar" from the CEF header
                        -w string:foo,bar  : remove all occurrences of "foo" and "bar" from ANY place in the CEF event 
                                             (can lead to incorrect CEF event--> Use with caution!!)						
                -e (--extract) fieldname   : keep CEF header and remove all fields not listed
                    ex: -e src,proto         keep CEF header, source address and protocol
                -S (--select) pattern      : keep only CEF events containing a given pattern. (OR between patterns)
                    ex: -S foo,bar           keep only CEF events containing "foo" OR "bar" 
                -U (--unselect) pattern    : keep only CEF events NOT containing a pattern. (AND NOT between patterns)
                    ex: -U foo,bar           keep only CEF events NOT containing foo AND NOT containing bar
                -A (--add) "field=value"   : add a tailing string to the CEF event
                    ex: -A "cs1=f o o"     
                -F (--fix) oldstr,newstr   : fix a broken CEF event with a search and replace function
                    ex: -F Prduct,Product    replaces all occurrences of "Prduct" by "Product"
""")
    exit()

## restartline
## used to overwrite stdout
def restartline():
    sys.stdout.write('\r')
    sys.stdout.flush()

## dottedQuadToNum
def dottedquadtonum(myip):
    return struct.unpack('!L',socket.inet_aton(myip))[0]
## numToDottedQuad
def numtodottedquad(myn):
    return socket.inet_ntoa(struct.pack('!L',myn))


### epoch conversion
### receives a timestamp in human readable, epoch or relative format and converts it to epoch format
### the timeformat is only used for human readable format and can be modified in custom parameters
def epochconversion(mytime):
    global errormessage 
    myepoch=''
    myregex=re.match('^(1\d{9})\s?$',mytime)    
    if myregex:
        # the time format seems to be epoch (acceptable values are 10 digits starting with 1)
        myepoch = myregex.group(1)
        return(myepoch)
    else:
        try:
            # trying to convert the time format to epoch (works only if time format follows the 'timeformat' convention)
            myepoch = int(time.mktime(time.strptime(mytime, timeformat)))
        except:
        
         
                myregex = re.match ('(Now|now|Today|today)\s?(\+|\-)\s?(\d+)(m|h|d|w|M)$', mytime)
                if myregex:
                    # time format is relative and contain extra parameters (ex: Today +1h)
                    if myregex.group(1) in ('now', 'Now'):
                        myepoch=int(time.time())
                    else:
                        #if myregex.group(1) = today
                        myepoch = int(time.mktime(time.strptime(str(date.today()), '%Y-%m-%d')))
                    if myregex.group(4)in ('m'):
                        myvariationinsec=60*int(myregex.group(3))
                    elif myregex.group(4)in ('h'):
                        myvariationinsec=3600*int(myregex.group(3))
                    elif myregex.group(4)in ('d'):
                        myvariationinsec=86400*int(myregex.group(3))
                    elif myregex.group(4)in ('w'):
                        myvariationinsec=604800*int(myregex.group(3))
                    elif myregex.group(4)in ('M'):
                        mytmpdate=str(date.today()).split('-')
                        myyear=mytmpdate[0]
                        mynewyear=myyear
                        mymonth=mytmpdate[1]
                        myday=mytmpdate[2]
                        mynewday=myday
                        mynewmonth=(int(mymonth) - (int(myregex.group(3))))
                        while (int(mynewmonth)<1):
                            mynewmonth=int(mynewmonth)+12
                            mynewyear=int(mynewyear)-1
                        # when doing something like -1M the resulting month is likely to have a max number of days different than
                        # the original one.  It can be a problem when the day is 29,30,31.  We need to ensure the resulting month
                        # contains enough days and, if it doesn't, we need to take the last day of the month to mimic Arcsight behavior
                        mytmp=monthrange(int(mynewyear),int(mynewmonth))
                        mynumofdays=mytmp[1]
                        if int(mynumofdays)<int(mynewday):
                            mynewday=mynumofdays    
                        mydiffdays=(date(int(myyear),int(mymonth),int(myday)) - date(int(mynewyear),int(mynewmonth),int(mynewday))).days
                        myvariationinsec=mydiffdays*86400
                    if myregex.group(2) in ("+"):
                        myepoch=myepoch+myvariationinsec
                    elif myregex.group(2) in ("-"):
                        myepoch=myepoch-myvariationinsec
                else:
                    myregex = re.match ('(Now|now|Today|today)\s?$', mytime)
                    if myregex:
                        # the time format is relative and doesn't contain extra parameters (Ex: Today)
                        if myregex.group(1) in ('now', 'Now'):
                            myepoch=int(time.time())
                        else:
                            # value is today
                            myepoch = int(time.mktime(time.strptime(str(date.today()), '%Y-%m-%d')))
                            
                    else:                    
                        errormessage=str(mytime)+' is not a valid time format'
                        usage()
        return(myepoch)

### input validation
### verifies the arguments used at the command line are correct
def inputvalidation(argv):                         
    global errormessage
    global outputfilesize
    global currentoutputfile
    global csvheaderlist
    # var initialisation
    myactioncnt=myactiontypecnt=myinputcnt=myoutputfilecnt=myoutputsyscnt=myoutputcnt=myinputfilescnt=mycsvfilecnt=0
    mysyshost=mysysport=mysysproto=myeps=myepochstarttime=myepochendtime=mycustomeventscnt=myoutputfile=mysanitizeopt=mycsvfile=mynoheadercsvfile='' 
    myaddstring=mydisplay=''
    myselectlist=[];myunselectlist=[];myextractlist=[];myfixlist=[]
    mytimetypelist=timelist
    myoptionslist=[];myinputfilelinescntlist=[];myinputfileslist=[]
    try:                                
        opts, args = getopt.getopt(argv, "gpr:k:c:n:s:o:v:i:hft:l:bw:e:S:U:A:F:d", ["generate", "play", "realtime=", "keeptimestamp=", "customtime=", "notimestamp=", "syslog=", "ceffile=", "csvfile=", "inputfile=", "help", "force", "timetype=", "limitoutputsize=", "blend", "sanitize=", "extract=", "select=", "unselect=", "add=", "fix=", "display"]) 
    except getopt.GetoptError:
        usage()
        sys.exit()
  
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
        ### Action parameters validation
        elif opt in ("-g", "--generate", "-p", "--play"):
            myactioncnt=myactioncnt+1
            if myactioncnt>1:
                errormessage="You can't use more than one action"
                usage()
            if opt in ("-g", "-p"):
                myaction=opt[1:2]
            else:
                myaction=opt[2:3]
                      
        ### Action-Type parameters validation
        elif opt in ("-r", "--realtime", "-k", "--keeptimestamp", "-c", "--customtime", "-n", "--notimestamp"):
            myactiontypecnt=myactiontypecnt+1
            if myactiontypecnt>1:
                errormessage="You can't use more than one action-type"
                usage()
            if opt in ("-r", "--realtime"):             
                myactiontype="r"
                myeps=str(arg)
                myregex=re.match('\d+$',myeps)
                if myregex:
                    myeps=int(myeps)
                    if myeps>maxeps:
                        if not '-f' in argv and not '--force' in argv:
                            myanswer=raw_input("\nThe selected EPS is higher than "+str(maxeps)+" and high EPS can cause inconsistencies. Do you want to continue [y/n] ?")               
                            if myanswer  not in ( 'y' , 'Y'):
                                print("\nOperation cancelled\n")
                                exit()
                else:
                    errormessage="The Events Per Second value for the realtime parameter must be numerical and greater than 0"
                    usage()
                          
            elif opt in ("-k", "--keeptimestamp"):
                myactiontype="k"
                myeps=str(arg)
                myregex=re.match('\d+$',myeps)
                if myregex:
                    myeps=int(myeps)
                    if myeps>maxeps:
                        if not '-f' in argv and not '--force' in argv:
                            myanswer=raw_input("\nThe selected EPS is higher than "+str(maxeps)+" and high EPS can cause inconsistencies. Do you want to continue [y/n] ?")               
                            if myanswer  not in ( 'y' , 'Y'):
                                print("\nOperation cancelled\n")
                                exit()                                                
                else:
                    errormessage="The Events Per Second value for the keeptimestamp parameter must be numerical and greater than 0"
                    usage()
                    
            elif opt in ("-n", "--notimestamp"):
                myactiontype="n"
                myeps=str(arg)
                myregex=re.match('\d+$',myeps)
                if myregex:
                    myeps=int(myeps)
                    if myeps>maxeps:
                        if not '-f' in argv and not '--force' in argv:
                            myanswer=raw_input("\nThe selected EPS is higher than "+str(maxeps)+" and high EPS can cause inconsistencies. Do you want to continue [y/n] ?")               
                            if myanswer  not in ( 'y' , 'Y'):
                                print("\nOperation cancelled\n")
                                exit()                                                
                else:
                    errormessage="The Events Per Second value for the notimestamp parameter must be numerical and greater than 0"
                    usage()
            else:
                myactiontype="c"
                mytimeparam=arg.split(':')
                if (len(mytimeparam) != 3):
                    errormessage='Incorrect parameter for customtime. \n       Didn\'t you forget to double-quote time(s) containing space characters ?'
                    usage()
                mystarttime=mytimeparam[0]
                myendtime=mytimeparam[1]
                mycustomeventscnt=mytimeparam[2]
                myepochstarttime=epochconversion(mystarttime)
                print ("\nCustom StartTime = "+time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(float(myepochstarttime))))
                myepochendtime=epochconversion(myendtime)
                print ("Custom EndTime   = "+time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(float(myepochendtime))))
                if (int(myepochstarttime) >= int(myepochendtime)):
                    errormessage="The endtime must be posterior to starttime"
                    usage()
            
        ### Input parameters validation
        elif opt in ("-i", "--inputfile"):
            try:
                myinputfilelist=arg.split(',')
                for myfile in myinputfilelist:
                    with open(myfile): pass
                myinputcnt=myinputcnt+1
            except:
                errormessage='File '+myfile+' does not exist'
                usage()
                               
        ### Output parameters validation
        elif opt in ("-o", "--ceffile"):            # output cef file
            myoutputfile=arg            
            myoutputfilecnt=myoutputfilecnt+1
            myoutputcnt=myoutputcnt+1
            if os.path.exists(arg) :
                if '-f' in argv or '--force' in argv:
                    try:
                        os.remove(myoutputfile)
                    except:
                        print ("\nFile overwriting failed. Please check the file "+myoutputfile+" is not used by another program\n")
                        exit() 
                else:
                    answer=raw_input("\nThe file "+myoutputfile+" already exists. Do you want to overwrite it [y/n] ?")
                    if answer  not in ( 'y' , 'Y'):
                        print("\nOperation cancelled\n")
                        exit()
                    else:
                        try:
                            os.remove(myoutputfile)
                        except:
                            print ("\nFile overwriting failed. Please check the file "+myoutputfile+" is not used by another program\n")
                            exit()
                        

        elif opt in ("-v", "--csvfile"):            # output csv file
            mycsvfile=arg
            mynoheadercsvfile=mycsvfile+'.CAKetmp'
            mycsvfilecnt=mycsvfilecnt+1
            myoutputcnt=myoutputcnt+1
            if os.path.exists(arg) :
                if '-f' in argv or '--force' in argv:
                    try:
                        os.remove(mycsvfile)
                    except:
                        print ("\nFile overwriting failed. Please check the file "+mycsvfile+" is not used by another program\n")	
                        exit() 						
                else:
                    answer=raw_input("\nThe file "+mycsvfile+" already exists. Do you want to overwrite it [y/n] ?")
                    if answer  not in ( 'y' , 'Y'):
                        print("\nOperation cancelled\n")
                        exit()
                    else:
                        try:
                            os.remove(mycsvfile)
                        except: 
                            print ("\nFile overwriting failed. Please check the file "+mycsvfile+" is not used by another program\n")
                            exit()
            for myfield in mandatoryfieldlist:      # add the mandatory fields at the end of the csvheaderlist if they are not listed in csvheaderlist
                if myfield not in csvheaderlist:
                    csvheaderlist.append(myfield)
                    
            
        
        elif opt in ("-s", "--syslog"):             # output syslog
            mysyslog=arg
            myoutputsyscnt=myoutputsyscnt+1
            myoutputcnt=myoutputcnt+1
            mysysparam=mysyslog.split(':')
            # must contain 3 values separated by :
            if (len(mysysparam))==3:
                mysyshost=mysysparam[0]
                myregex=re.match('\d+$',mysysparam[1])
                if myregex :
                    if (int(mysysparam[1])>0) and (int(mysysparam[1])<65536):    
                        mysysport=mysysparam[1]
                    else:
                        errormessage="Incorrect port number for syslog option"
                        usage()
                else:
                    errormessage="Port must be numerical for syslog option"
                    usage()
                
                mysysproto=mysysparam[2]
                if mysysproto not in ('u', 't', 'ud'):
                    errormessage="Proto value must be u (udp), t (tcp) or ud (udp + 1msec delay between events) for syslog parameter"
                    usage()     
            else:
                errormessage="Incorrect parameters provided for syslog option"
                usage()
				
				
        elif opt in ("-d", "--display"):            # screen output
            myoutputcnt=myoutputcnt+1
            mydisplay="true"
		
        ### Options parameters validation
        elif opt in ("-f", "--force", "-t", "--timetype", "-l", "--limitoutputsize" ,"-b", "--blend", "-w", "--sanitize", "-e", "--extract", "-S", "--select", "-U", "--unselect", "-A", "--add", "-F" , "--fix"):
            if opt in ("-f", "--force"):
                myoptionslist.append('f')
            elif opt in ("-t", "--timetype"):
                mytimetype=arg
                mytimetypelist=mytimetype.split(',')                
                myoptionslist.append('t')
            elif opt in ("-l", "--limitsize" ):
                myoptionslist.append('l')
                myregex=re.match('\d+$',arg)
                if myregex and (int(arg)>0): # means rotation is required for output files
                    outputfilesize=int(arg)*1024*1024
                    currentoutputfile=myoutputfile+'.'+str(datetime.now().strftime("%Y%m%d-%H%M%S"))
                elif not myregex:
                    errormessage="The limitsize parameter must be an integer"
                    usage()
            elif opt in ("-b", "--blend" ):
                myoptionslist.append('b')
            elif opt in ("-w", "--sanitize" ):
                myoptionslist.append('w')
                myregex=re.match('[^:]+:[^:]+$',arg)
                if myregex:
                    mysanitizeopt=arg.split(':')
                    if mysanitizeopt[0].lower()=='ip' and mysanitizeopt[1].lower() not in ('rnd','rm'):
                        errormessage='Invalid option for -w IP, should be IP:rnd or IP:rm'
                        usage()						 
                    elif mysanitizeopt[0].lower() not in ('string','field','ip','value','header'):
                        errormessage="Valid options for -w are 'ip' 'field' 'string' 'value' or 'header'"
                        usage()
                else:
                    errormessage='Incorrect parameter for -w option'
                    usage()
            elif opt in ("-e", "--extract"):
                myoptionslist.append('e')
                myextractlist=arg.split(',')
                for myelement in myextractlist:                    
                    if myelement == "":     
                        errormessage="The extract option cannot contain empty value"
                        usage()
            elif opt in ("-S", "--select"):
                myoptionslist.append('S')
                myselectlist=arg.split(',')
                for myelement in myselectlist:                    
                    if myelement == "":     
                        errormessage="The select option cannot contain empty value"
                        usage()
            elif opt in ("-U", "--unselect"):
                myoptionslist.append('U')
                myunselectlist=arg.split(',')
                for myelement in myunselectlist:                    
                    if myelement == "":     
                        errormessage="The unselect option cannot contain empty value"
                        usage()
            elif opt in ("-A", "--add"):
                myoptionslist.append('A')
                myaddstring=arg
                if myaddstring[1]=='-' or myaddstring=='' :				
                    errormessage="The argument for the -A option cannot be empty"
                    usage()
            elif opt in ("-F", "--fix"):
                myoptionslist.append('F')
                myfixlist=arg.split(',')
                if len(myfixlist)!=2 :				
                    errormessage="2 arguments are required for the -F option"
                    usage()
    print""       
    ### check if mandatory switches are present
    if myactioncnt != 1 or myactiontypecnt != 1 or myinputcnt != 1 or myoutputcnt >4 or myoutputcnt <1 or myoutputfilecnt > 1 or mycsvfilecnt > 1 or myoutputsyscnt >1 :
        usage()
    elif myinputfilescnt>1 and myaction=='g':
        errormessage='You can only specify a single file as input when using the generate action'
        usage()
    else:
        return(myaction,myactiontype,myinputfilelist,myinputfilescnt,myinputfilelinescntlist,myoutputfile,mycsvfile,mynoheadercsvfile,mysyshost,mysysport,mysysproto,myeps,myepochstarttime,myepochendtime,mycustomeventscnt,myoptionslist,mytimetypelist,mysanitizeopt,myextractlist,myselectlist,myunselectlist,myaddstring,myfixlist,mydisplay)


### read 'generate' input file
### read and validate input file used with 'generate' action
def readgenerateinputfile():
    global errormessage
    mysection=0
    myCEFmandatorylist=[]
    myCEFoptionlist=[]
    # default separator value
    myseparator=','
    # list of compulsory fields which must be present in the section 2 of the file.  Order must be the same
    mymandatoryfields=['cefversion','devicevendor','deviceproduct','deviceversion','signatureid','name','severity']

    try:
        # NB : when -g option is selected, only one file can be used as input file so we need to specify that the file
        # to validate must be the first element of inputfile list
        myfile=open(inputfilelist[0], "r")
        mylines=myfile.readlines()
        myfile.close()
    except:
        errormessage="Couldn't access "+str(inputfilelist[0])
        usage()
        exit()
    for myline in mylines :
        if myline[0] not in ('#', ' ', '\n'):
            if myline [0:2]== '==':
                mysection=mysection+1
                continue
            if mysection==1:
                # section related to global parameters
                myregex=re.match ('^separator:(.*)$', myline)
                if myregex:
                    myseparator=myregex.group(1)
            elif mysection==2:
                # section related to compulsory CEF fields
                myregex=re.match ('^([a-zA-Z]+):(.*)$', myline)
                if myregex:
                    # the fieldname must be the first in the list.  If found, the first list
                    # entry is removed
                    if myregex.group(1) == mymandatoryfields[0]:
                        del mymandatoryfields[0]
                        mytmplist=[myregex.group(1)]
                        for myvalue in (myregex.group(2)).split(myseparator):
                            mytmplist.append(myvalue)
                        myCEFmandatorylist.append(mytmplist)
            elif mysection==3:
                # section related to optional CEF fields
                myregex=re.match ('^([a-zA-Z0-9]+):(.*)$', myline)
                if myregex:
                    mytmplist=[myregex.group(1)]
                    for myvalue in (myregex.group(2)).split(myseparator):
                        mytmplist.append(myvalue)
                    myCEFoptionlist.append(mytmplist)
    # check if all compulsory fields have been found                
    if len(mymandatoryfields)!=0:
        errormessage="Some compulsory CEF elements couldn't be found in the template file :\n"
        for mymissingfield in mymandatoryfields:
            errormessage=errormessage+mymissingfield+'\n'
        errormessage=errormessage+"\nPlease check "+str(inputfilelist[0])+" SECTION2\n"
        usage()
        exit()
    return(myCEFmandatorylist,myCEFoptionlist)
        

### Generate Random CEF
### for 'generate' action : generate a random CEF event
def generaterandomcef():
    
    myCEFevt='CEF:'
    # randomly choose mandatory values
    for mymandatoryfield in CEFmandatorylist:
        myCEFevt=myCEFevt+str(random.choice(mymandatoryfield[1:]))+'|'
    # randomly choose optional values
    for myoptionfield in CEFoptionlist:
        mytmprnd=str(random.choice(myoptionfield[1:]))
        myregexip=re.match(r'\[(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\]',mytmprnd)
        myregexint=re.match(r'\[(\d+):(\d+)\]',mytmprnd)
        if myregexint: # generate random value for this range
            mystart=int(myregexint.group(1))
            myend=int(myregexint.group(2))
            myend=myend+1 #randrange doesn't consider the last value as an option
            if (myend-mystart>0):
                mytmprnd=randrange(mystart,myend)
            else: #second number should be > than first number --> zeroing out the value
                mytmprnd=''
        elif myregexip: # generated random IP for this IP range
            try:
                mystartip=dottedquadtonum(myregexip.group(1))
                myendip=dottedquadtonum(myregexip.group(2))
                myendip=int(myendip)+1
            except:
                mytmprnd='' # incorrect IP
            if myendip>mystartip:
                mytmprnd=randrange(mystartip,myendip)
                mytmprnd=numtodottedquad(mytmprnd)
            else: #start ip smaller than end ip --> zeroing out the value
                mytmprnd=''
        if mytmprnd != '': #if value not empty, write the field
            myCEFevt=myCEFevt+str(myoptionfield[0])+'='+str(mytmprnd)+' '
        
                
    return(myCEFevt)

### Gencustom
### Generate CEF events, spread events across defined timerange and generate output
def gencustom():
    mytimewindow=(int(epochendtime)-int(epochstarttime))*1000
    mymillisecbetweenevents=mytimewindow/float(customeventscnt)
    myepoch=int(str(epochstarttime)+'000')
    myi=0
    while myi<int(customeventscnt):
        myj=0
        mylistofevt=[]
        while myj<maxCEFmem and myi<int(customeventscnt):
            myrandCEFevt=generaterandomcef()
            for mytimetoworkon in timelist:
                myrandCEFevt=re.sub(r' '+mytimetoworkon+'=\d{10,13}', "", myrandCEFevt)
                myrandCEFevt=myrandCEFevt+' '+mytimetoworkon+'='+str(int(myepoch))
            myepoch=myepoch+mymillisecbetweenevents   
            mylistofevt.append(myrandCEFevt)
            myi=myi+1
            myj=myj+1
        output(mylistofevt)

### Genkeeptimestamp
### Generate random CEF events from file(s) but don't modify the timestamp
def genkeeptimestamp():
    print("\nPress CTRL-C to stop\n")
    myi=0
    myprocessedevents=0
    try:
        #never ending loop
        while myi==myi:
            mystart=datetime.now()
            while myi<int(eps):
                myj=0
                mylistofevt=[]
                while myj<maxCEFmem and myi<int(eps):
                    myrandCEFevt=generaterandomcef()
                    # call change rt procedure
                    mylistofevt.append(myrandCEFevt)
                    myi=myi+1
                    myj=myj+1
                output(mylistofevt)
            myend=datetime.now()
            mydiff=myend-mystart
            mydiffmic=mydiff.microseconds
            if mydiffmic > 0:
                mysleeptime=(1000000-mydiffmic)/1000
                mysleeptime='0.'+str(mysleeptime)   
            elif mydiffmic == 0:
                mysleeptime=1
            else:
                mysleeptime=0
            time.sleep(float(mysleeptime))
            myprocessedevents=myprocessedevents+myi
            sys.stdout.write("Processed events at "+(str(datetime.now()))[:-3]+": "+str(myprocessedevents))
            sys.stdout.flush()
            restartline()
            myi=0
    except KeyboardInterrupt:
        # Get out of the loop with CTRL-C
        output(mylistofevt)

### Genrealtime
### Generate random CEF events and replace rt by current timestamp
def genrealtime():
    print("\nPress CTRL-C to stop\n")
    myi=0
    myprocessedevents=0
    mysecsincestart=0
    #measuring the timestamp diff between two consecutives events
    mymillisecbetweenevents=1000/float(eps)        
    myepoch=time.mktime(time.gmtime())
    # change epoch time in millisec
    myepoch=int(str(int(myepoch))+'000')
    try:
        #never ending loop
        while myi==myi:
            mystart=datetime.now()
            while myi<int(eps):
                myj=0
                mylistofevt=[]
                while myj<maxCEFmem and myi<int(eps):
                    myrandCEFevt=generaterandomcef()
                    for mytimetoworkon in timelist:
                        myrandCEFevt=re.sub(r' '+mytimetoworkon+'=\d{10,13}', "", myrandCEFevt)
                        myrandCEFevt=myrandCEFevt+' '+mytimetoworkon+'='+str(int(myepoch))
                    myepoch=myepoch+mymillisecbetweenevents   
                    mylistofevt.append(myrandCEFevt)
                    myi=myi+1
                    myj=myj+1
                output(mylistofevt)
            myend=datetime.now()
            mydiff=myend-mystart
            mydiffmic=mydiff.microseconds
            if mydiffmic > 0:
                mysleeptime=(1000000-mydiffmic)/1000
                mysleeptime='0.'+str(mysleeptime)   
            elif mydiffmic == 0:
                mysleeptime=1
            else:
                mysleeptime=0
            time.sleep(float(mysleeptime))
            myprocessedevents=myprocessedevents+myi
            sys.stdout.write("Processed events at "+(str(datetime.now()))[:-3]+": "+str(myprocessedevents))
            sys.stdout.flush()
            restartline()
            myi=0
            mysecsincestart=mysecsincestart+1
            # syncing the time with OS time every minute
            if mysecsincestart==60:
                mysecsincestart=0
                myepoch=time.mktime(time.gmtime())
                myepoch=int(str(int(myepoch))+'000')
            
    except KeyboardInterrupt:
        # Get out of the loop with CTRL-C
        output(mylistofevt)

### Gennotimestamp
### Generate random CEF events and remove rt
def gennotimestamp():
    print("\nPress CTRL-C to stop\n")
    myi=0
    myprocessedevents=0    
    myepoch=time.mktime(time.gmtime())
    try:
        #never ending loop
        while myi==myi:
            mystart=datetime.now()
            while myi<int(eps):
                myj=0
                mylistofevt=[]
                while myj<maxCEFmem and myi<int(eps):
                    myrandCEFevt=generaterandomcef()
                    for mytimetoworkon in timelist:
                        myrandCEFevt=re.sub(r' '+mytimetoworkon+'=\d{10,13}', "", myrandCEFevt)
                    mylistofevt.append(myrandCEFevt)
                    myi=myi+1
                    myj=myj+1
                output(mylistofevt)
            myend=datetime.now()
            mydiff=myend-mystart
            mydiffmic=mydiff.microseconds
            if mydiffmic > 0:
                mysleeptime=(1000000-mydiffmic)/1000
                mysleeptime='0.'+str(mysleeptime)   
            elif mydiffmic == 0:
                mysleeptime=1
            else:
                mysleeptime=0
            time.sleep(float(mysleeptime))
            myprocessedevents=myprocessedevents+myi
            sys.stdout.write("Processed events at "+(str(datetime.now()))[:-3]+": "+str(myprocessedevents))
            sys.stdout.flush()
            restartline()
            myi=0
            
    except KeyboardInterrupt:
        # Get out of the loop with CTRL-C
        output(mylistofevt)


### Playcustom
### Read CEF events from file(s), spread events across defined timerange and generate output
### fileinput used in order to be able handling huge file without loading them in memory
def playcustom():
    mycnt=0
    myi=1
    mylistofevts=[]
    mytimewindow=(epochendtime-epochstarttime)*1000
    mymillisecbetweenevents=mytimewindow/float(customeventscnt)
    myepoch=int(str(epochstarttime)+'000')
    while mycnt<int(customeventscnt):       
        for myline in fileinput.input(inputfilelist):
            myregex=re.match(validCEFevt,myline)
            if myregex:                
                mycnt=mycnt+1
                myline=myline.rstrip()
                for mytimetoworkon in timelist:
                        myline=re.sub(r' '+mytimetoworkon+'=\d{10,13}', "", myline)
                        myline=myline+' '+mytimetoworkon+'='+str(int(myepoch))
                myepoch=myepoch+mymillisecbetweenevents                   
                mylistofevts.append(myline)
                if myi==maxCEFmem:
                    myi=1
                    output(mylistofevts)
                    mylistofevts=[]
                myi=myi+1
                if mycnt==int(customeventscnt):
                    output(mylistofevts)
                    break

### Playkeeptimestamp
### Read CEF events from file(s) but don't modify the timestamp
### fileinput used in order to be able handling huge file without loading them in memory
def playkeeptimestamp():
    print("\nPress CTRL-C to stop\n")
    mycnt=0
    myi=1
    myprocessedevents=0
    mynumofsec=0
    mylistofevts=[]
    try:
        #never ending loop
        mystart=datetime.now()
        while myi==myi:
            
            for myline in fileinput.input(inputfilelist):
                myregex=re.match(validCEFevt,myline)
                if myregex:
                    mycnt=mycnt+1
                    myline=myline.rstrip()                  
                    mylistofevts.append(myline)
                    if myi==maxCEFmem:
                        myi=0
                        output(mylistofevts)
                        mylistofevts=[]
                    myi=myi+1
                    # when the max num of events to keep in memory is reached --> output
                    if mycnt==int(eps):
                        myend=datetime.now()
                        mydiff=myend-mystart
                        mydiffmic=mydiff.microseconds
                        if mydiffmic > 0:
                            mysleeptime=(1000000-mydiffmic)/1000
                            mysleeptime='0.'+str(mysleeptime)   
                        elif mydiffmic == 0:
                            mysleeptime=1
                        else:
                            mysleeptime=0
                        # every 5 sec, force the output to avoid having to wait for too long if eps is low
                        mynumofsec=mynumofsec+1
                        if mynumofsec==5:
                            output(mylistofevts)
                            mylistofevts=[]
                            myi=0
                            mynumofsec=0
                        time.sleep(float(mysleeptime))                        
                        mystart=datetime.now()
                        myprocessedevents=myprocessedevents+mycnt
                        sys.stdout.write("Processed events at "+(str(datetime.now()))[:-3]+": "+str(myprocessedevents))
                        sys.stdout.flush()
                        restartline()
                        mycnt=0
                        
    except KeyboardInterrupt:
        # Get out of the loop with CTRL-C
        output(mylistofevts)
        print('')
        
### Playrealtime
### Read CEF events from file(s) and replace rt by current timestamp
### fileinput used in order to be able handling huge file without loading them in memory
def playrealtime():
    print("\nPress CTRL-C to stop\n")
    mycnt=0
    myi=1
    myprocessedevents=0
    mynumofsec=0
    mylistofevts=[]
    mysecsincestart=0
    mymillisecbetweenevents=1000/float(eps)
    myepoch=time.mktime(time.gmtime())
    # change epoch time in millisec
    myepoch=int(str(int(myepoch))+'000')
    try:
        mystart=datetime.now()
        #never ending loop
        while myi==myi:
            
            for myline in fileinput.input(inputfilelist):
                myregex=re.match(validCEFevt,myline)
                if myregex:
                    mycnt=mycnt+1
                    myline=myline.rstrip()
                    for mytimetoworkon in timelist:
                        myline=re.sub(r' '+mytimetoworkon+'=\d{10,13}', "", myline)
                        myline=myline+' '+mytimetoworkon+'='+str(int(myepoch))
                    myepoch=myepoch+mymillisecbetweenevents                   
                    mylistofevts.append(myline)
                    if myi==maxCEFmem:
                        myi=0
                        output(mylistofevts)
                        mylistofevts=[]
                    myi=myi+1
                    # when the max num of events to keep in memory is reached --> output
                    if mycnt==int(eps):
                        myend=datetime.now()
                        mydiff=myend-mystart
                        mydiffmic=mydiff.microseconds
                        if mydiffmic > 0:
                            mysleeptime=(1000000-mydiffmic)/1000
                            mysleeptime='0.'+str(mysleeptime)   
                        elif mydiffmic == 0:
                            mysleeptime=1
                        else:
                            mysleeptime=0
                        # every 5 sec, force the output to avoid having to wait for too long if eps is low
                        mynumofsec=mynumofsec+1
                        if mynumofsec==5:
                            output(mylistofevts)
                            mylistofevts=[]
                            myi=0
                            mynumofsec=0
                        time.sleep(float(mysleeptime))                        
                        mystart=datetime.now()
                        myprocessedevents=myprocessedevents+mycnt
                        sys.stdout.write("Processed events at "+(str(datetime.now()))[:-3]+": "+str(myprocessedevents))
                        sys.stdout.flush()
                        restartline()
                        mycnt=0
                        # syncing the time with OS time every minute
                        if mysecsincestart==60:
                            mysecsincestart=0
                            myepoch=time.mktime(time.gmtime())
                            myepoch=int(str(int(epoch))+'000')
    except KeyboardInterrupt:
        # Get out of the loop with CTRL-C
        output(mylistofevts)
        print('')

### Playnotimestamp
### Read CEF events from file(s) and remove timestamp
### fileinput used in order to be able handling huge file without loading them in memory
def playnotimestamp():
    print("\nPress CTRL-C to stop\n")
    mycnt=0
    myi=1
    myprocessedevents=0
    mynumofsec=0
    mylistofevts=[]
    myepoch=time.mktime(time.gmtime())
    try:
        mystart=datetime.now()
        #never ending loop
        while myi==myi: 
            for myline in fileinput.input(inputfilelist):
                myregex=re.match(validCEFevt,myline)
				
                if myregex:
                    mycnt=mycnt+1
                    myline=myline.rstrip()
                    for mytimetoworkon in timelist:                   
                        myline=re.sub(r' '+mytimetoworkon+'=\d{10,13}', "", myline)                 
                    mylistofevts.append(myline)
                    
                    if myi==maxCEFmem:
                        myi=0
                        output(mylistofevts)
                        mylistofevts=[]
                    myi=myi+1
                    # when the max num of events to keep in memory is reached --> output
                    if mycnt==int(eps):
                        myend=datetime.now()
                        mydiff=myend-mystart
                        mydiffmic=mydiff.microseconds
                        if mydiffmic > 0:
                            mysleeptime=(1000000-mydiffmic)/1000
                            mysleeptime='0.'+str(mysleeptime)   
                        elif mydiffmic == 0:
                            mysleeptime=1
                        else:
                            mysleeptime=0
                        # every 5 sec, force the output to avoid having to wait for too long if eps is low
                        mynumofsec=mynumofsec+1
                        if mynumofsec==5:
                            output(mylistofevts)
                            mylistofevts=[]
                            myi=0
                            mynumofsec=0
                        time.sleep(float(mysleeptime))                        
                        mystart=datetime.now()
                        myprocessedevents=myprocessedevents+mycnt
                        sys.stdout.write("Processed events at "+(str(datetime.now()))[:-3]+": "+str(myprocessedevents))
                        sys.stdout.flush()
                        restartline()
                        mycnt=0
    except KeyboardInterrupt:
        # Get out of the loop with CTRL-C
        output(mylistofevts)
        print('')


# # output
# # printing a list of events passed as argument
def output(mylisttoprocess):
    global writtenlines
    global currentoutputfile
    global csvheader

    ### options
    if 'S' in optionslist: # Select only some events
        mylisttoprocess=select(mylisttoprocess)
    if 'U' in optionslist: # Unselect some events
        mylisttoprocess=unselect(mylisttoprocess)
    if 'e' in optionslist: # extract fields of interest
        mylisttoprocess=extract(mylisttoprocess)
    if 'F' in optionslist: # FIX optioni : search and replace a string
        mylisttoprocess=fix(mylisttoprocess)
    if 'A' in optionslist: # add some extra CEF fields
        mylisttoprocess=add(mylisttoprocess)
    if 'b' in optionslist: # blend events in list
        random.shuffle(mylisttoprocess)
    if 'w'in optionslist: # sanitization required
        mylisttoprocess=sanitize(mylisttoprocess)
        
    ### CEF file, syslog and csv file output
    if currentoutputfile=='': # if -l option not used but default parameter != 0 , assign the first file name
        currentoutputfile=outputfile+'.'+str(datetime.now().strftime("%Y%m%d-%H%M%S"))
        
    if outputfile and int(outputfilesize)>0 :                       # multiple CEF output files required
        myoutfile=open(currentoutputfile,'a')
        for myevent in mylisttoprocess:
            myoutfile.write(myevent+"\n")
            if writtenlines==100: # can be reduced to increase precision at the perf cost
                if (os.path.getsize(currentoutputfile) > outputfilesize):
                       #print (currentoutputfile+" "+str(writtenlines)+" filesize="+str(os.path.getsize(currentoutputfile)))
                       myoutfile.close()
                       time.sleep(1) # required to ensure a maximum of 1 file is created per sec. Also solving the issue when too many files created very quickly
                       currentoutputfile=outputfile+'.'+str(datetime.now().strftime("%Y%m%d-%H%M%S"))
                       myoutfile=open(currentoutputfile,'a')
                writtenlines=0
            writtenlines=writtenlines+1
        myoutfile.close()
        
    elif outputfile and int(outputfilesize)==0:                     # single CEF output file
        myoutfile=open(outputfile,'a')
        for myevent in mylisttoprocess:
            myoutfile.write(myevent+"\n")
        myoutfile.close()
        
    if syshost:                                                     # syslog output
        if sysproto=='t': # TCP
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((syshost,int(sysport)))
            for myevent in mylisttoprocess:
                sock.send(myevent+'\n')
            sock.close()
        elif sysproto=='u': # UDP
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            for myevent in mylisttoprocess:
                sock.sendto(myevent, (syshost, int(sysport)))
            sock.close()   
        elif sysproto=='ud': # UDP with a delay to reduce lost packets
            myi=1
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            for myevent in mylisttoprocess:
                if (myi==delaybatchsize):
                    time.sleep(udpdelay)
                    myi=0
                myi=myi+1
                sock.sendto(myevent, (syshost, int(sysport)))
            sock.close()
            
    if csvfile:                                                     # csv output file
        mynoheadercsvfile=open(noheadercsvfile,'a')
        for myevent in mylisttoprocess:
            (myevent)=csvconverter(myevent)
            mynoheadercsvfile.write(myevent+"\n")
        mynoheadercsvfile.close()
		
    if display=="true":														# screen output
        print("\n\n")
        for myevent in mylisttoprocess:
            print(myevent+"\n")
        print("\n")
## csvconverter
## converting a CEF event in .csv
def csvconverter(myCEFevent) :

    global csvheaderlist
    mydict={}
    mycsvevent=''
    
    myregex=re.search(r'(CEF:([^\|]*)\|([^\|]*)\|([^\|]*)\|([^\|]*)\|([^\|]*)\|([^\|]*)\|([^\|]*)\| *(.*))',myCEFevent) # extract header values 
    mydict['cefVersion']=myregex.group(2)                   # store header values in a dictionary
    mydict['deviceVendor']=myregex.group(3)
    mydict['deviceProduct']=myregex.group(4)
    mydict['deviceVersion']=myregex.group(5)
    mydict['signatureId']=myregex.group(6)
    mydict['name']=myregex.group(7)
    mydict['severity']=myregex.group(8)
    myCEFextension=myregex.group(9)                           
    
    myregex=re.findall(r'([_a-zA-Z0-9]+=[^((?<!\\)=)]+)(?:\s+|$)',myCEFextension)     # extract all optional fields-values pairs in CEFextension
    
    # for each optional field/value pair, extract the pair, stores it in a dictionary and, if the key is unknown, add it at the end of the csvheaderlist
    for myelement in myregex:
        mykey=(myelement.split('='))[0]         
        myvalue=(myelement.split('='))[1]
        mydict[mykey]=myvalue                               
        if mykey not in csvheaderlist:
            csvheaderlist.append(mykey)

    for myfield in csvheaderlist:
        try:
            myvalue=mydict[myfield]		
            if allowdelimiterinvalue=="false": # if you have decided it is not allowed to have the delimiter in the value of a CEF field it will be replaced
                myvalue=myvalue.replace(csvdelimiter,replacementcsvdelimiter)
            mycsvevent=(mycsvevent+csvdelimiter+csvqualifier+myvalue+csvqualifier)
        except: #if empty value
            mycsvevent=(mycsvevent+csvdelimiter+csvqualifier*2)
    mycsvevent=mycsvevent[1:]
    return(mycsvevent)

## finalizecsv
## finalizing the csv file by writing the header at the top of the csv file
## because we can't know the number of fields until the end of the first csv conversion pass, some empty values will probably be missing
## at the end of the line. We will add them during this second conversion pass.
## This requires creating a new file --> could cause disk space usage issue for big files

def finalizecsv():

    print "\nGenerating final csv file ... please wait"
    # creating a new file with csv header
    myheader=''
    myfieldscount=len(csvheaderlist)
    mycsvfile=open(csvfile,'w')
    mycsvfile.write('sep='+csvdelimiter+'\n')
    for myelement in csvheaderlist:
        myheader=myheader+csvdelimiter+csvqualifier+myelement+csvqualifier
    myheader=myheader[1:]+'\n'
    mycsvfile.write(myheader)
    
    #for each line, check the number of values = number of fields in the header. If not, add empty values at the end
    #then write the line in the final CSV file
    mynoheadercsvfile=open(noheadercsvfile,'r')
    for myline in mynoheadercsvfile:
        myline=myline.rstrip()
        myvaluescount=myline.count(csvqualifier+csvdelimiter+csvqualifier)+1
        while (myvaluescount<myfieldscount):
            myline=myline+csvdelimiter+csvqualifier+csvqualifier
            myvaluescount=myvaluescount+1        
        myline=myline+"\n"
        mycsvfile.write(myline)
    mycsvfile.close()
    mynoheadercsvfile.close()
    os.remove(noheadercsvfile)

## sanitize
## sanitizing IPs, fields or strings in CEF events
def sanitize(myoriginallist):
    mynewlist=[]
    if sanitizeopt[0].lower()=='ip' and sanitizeopt[1].lower()=='rm':
        for myevent in myoriginallist:
            myevent=re.sub(r'([^\s\|]+)=\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', r'\b', myevent) # remove IP fields         
            mynewlist.append(myevent)
    elif sanitizeopt[0].lower()=='ip' and sanitizeopt[1].lower()=='rnd':
        rndipmindotted=dottedquadtonum(rndipmin)
        rndipmaxdotted=1+int(dottedquadtonum(rndipmax))
        for myevent in myoriginallist:
            myiplist=re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})',myevent)
			
            for myip in myiplist:
                myevent=re.sub(myip, str(numtodottedquad(randrange(rndipmindotted,rndipmaxdotted))), myevent)
            mynewlist.append(myevent)            
			
    elif sanitizeopt[0].lower()=='field': # removes "field=value" if field contains a given pattern. IE:  -w field=foo,bar  will remove "foo=123" and  "bar=345" from the CEF event
        myfieldslist=sanitizeopt[1].split(',')
        for myevent in myoriginallist:
            for myfield in myfieldslist:
                myregex=re.search(r'('+myfield+'=[^=]+)($|\s[^\s]+=).*',myevent)
                if myregex:
                    myevent=re.sub(myregex.group(1),'',myevent)
            mynewlist.append(myevent)
			
    elif sanitizeopt[0].lower()=='string': # removes the string wherever it is found even in the header or fieldname --> could lead to incorrect CEF. IE -w string=pro --> proto=UDP become to=UDP
        mystringslist=sanitizeopt[1].split(',')
        for myevent in myoriginallist:
            for mystring in mystringslist:
                myevent=re.sub(mystring,"",myevent)
            mynewlist.append(myevent)

    elif sanitizeopt[0].lower()=='value': # removes "field=value" if value contains a given pattern. IE -w value=TCP,UDP --> will remove "proto=TCP" and "proto=UDP" from the CEF event
        myvalueslist=sanitizeopt[1].split(',')
        for myevent in myoriginallist:
            for myvalue in myvalueslist:
                found="true"
                while found=="true":
                    myregex=re.search(r'(\w+=([^=]*'+myvalue+'[^=]*))($|\s)',myevent)		
                    if myregex:
                        myevent=re.sub(myregex.group(1),'',myevent)
                    else:
                        found="false"               
            mynewlist.append(myevent)
			
    elif sanitizeopt[0].lower()=='header': # removes all occurences of a given pattern FROM the CEF header
        mystringslist=sanitizeopt[1].split(',')
        for myevent in myoriginallist:            
            for mystring in mystringslist:
                myregex=re.search(r'^(CEF:[^\|]*\|[^\|]*\|[^\|]*\|[^\|]*\|[^\|]*\|[^\|]*\|[^\|]*\|)(.*$)',myevent)
                if myregex:
                    myevent=re.sub(mystring,"",str(myregex.group(1)))+str(myregex.group(2))
			
            mynewlist.append(myevent)		
			
    return(mynewlist)
            
## extract
## extracting a selection of fields from the CEF event and sorting them out according to the user defined order

def extract(myoriginallist):
    mynewlist=[]
    for myevent in myoriginallist:
        mynewevent=''
        myregex=re.match(r'(CEF:[^\|]*\|[^\|]*\|[^\|]*\|[^\|]*\|[^\|]*\|[^\|]*\|[^\|]*\|)',myevent)
        if myregex:
            mynewevent=myregex.group(1)
            for myfield in extractlist:
                myregex=re.search(r'('+myfield+'=[^=]+)($|\s[^\s]+=).*',myevent)
                if myregex:
                    mynewevent=mynewevent+' '+str(myregex.group(1))
            mynewlist.append(mynewevent)
    return(mynewlist)

	
# only select events containing a given pattern --> if multiple patterns are selected, condition between patterns is an OR. If a AND is needed,, CAKE must be run once per pattern
# Because the select function is applied after the event reading or generation, the count of events does not reflect the number of events selected sent to the output but the count
# of events read or generated before the selection happens

def select(myoriginallist):
    mynewlist=[]
    for myevent in myoriginallist:
        for myfield in selectlist:
            myregex=re.search(myfield,myevent)
            if myregex:
                mynewlist.append(myevent)
                break
    return(mynewlist)


# only select events NOT containing a given pattern --> if multiple patterns are UNselected, condition between patterns is a AND NOT. This means all events containing any of the specified pattern will be discarded
# Because the unselect function is applied after the event reading or generation, the count of events does not reflect the number of events sent to the output but the count
# of events read or generated before the selection happens 

def unselect(myoriginallist):
    mynewlist=[]
    for myevent in myoriginallist:
        mymatchall="true"
        for myfield in unselectlist:
            myregex=re.search(myfield,myevent)
            if not myregex:
                mymatchall="false"			
        if mymatchall=="false":
            mynewlist.append(myevent)
    return(mynewlist)

# allows adding extra "field=value" information to a CEF event. 
def add(myoriginallist):
    mynewlist=[]           
    for myevent in myoriginallist:
        myevent=myevent+" "+addstring
        mynewlist.append(myevent)
    return(mynewlist)

def fix(myoriginallist):
    mynewlist=[]           
    for myevent in myoriginallist:
        #print myevent
        myevent=myevent.replace(fixlist[0],fixlist[1])
        mynewlist.append(myevent)
        #print (myevent+"\n")
    return(mynewlist)	
	
# ###############################################################################    
# ###      MAIN
# ###############################################################################


print("""

      ___    __    _  _   
     / __)  /__\  ( )/ ) ___
    ( (__  /(__)\ |   ( / -_)
     \___)(__)(__)(_)\_)\___|   
     
""")

## Input validation

(action,actiontype,inputfilelist,inputfilescnt,inputfilelinescntlist,outputfile,csvfile,noheadercsvfile,syshost,sysport,sysproto,eps,epochstarttime,epochendtime,customeventscnt,optionslist,timelist,sanitizeopt,extractlist,selectlist,unselectlist,addstring,fixlist,display)=inputvalidation(sys.argv[1:])
#print (action,actiontype,inputfilelist,inputfilescnt,inputfilelinescntlist,outputfile,syshost,sysport,sysproto,eps,epochstarttime,epochendtime,customeventscnt,optionslist)

print ("Task started at   "+str(datetime.now())[:-3])
      

## =================
## Action = generate
## =================

if action=='g':
    
    (CEFmandatorylist,CEFoptionlist)=readgenerateinputfile() # For generate action, validate input file content

    if actiontype=='c':     # Action Type = custom : events spread across the defined timerange
        gencustom()
            
    elif actiontype=='k':   # Action Type = keeptimestamp : no change made to timestamps
        genkeeptimestamp()
            
    elif actiontype=='r':   # Action Type = realtime : timestamp(s) replaced by current timestamp
        genrealtime()
            
    elif actiontype=='n':   # Action Type = notimestamp : timestamp(s) removed
        gennotimestamp()
        
    else:
        usage()
       
## =============
## Action = play
## =============
            
elif action=='p':

    if actiontype=='c':     # Action Type = custom : events spread across the defined timerange
        playcustom()

    elif actiontype=='k':   # Action Type = keeptimestamp : no change made to timestamps
        playkeeptimestamp()

    elif actiontype=='r':   # Action Type = realtime : timestamp(s) replaced by current timestamp
        playrealtime()

    elif actiontype=='n':   # Action Type = notimestamp : timestamp(s) removed
        playnotimestamp()

    else:
        usage()


if csvfile:
    finalizecsv()

print("\n\nTask completed at "+str(datetime.now())[:-3])


