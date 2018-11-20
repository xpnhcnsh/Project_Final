#/Desktop/Project main.py
import projectlib
from projectlib import *
rpipinsetup()

#dbinitial()
userdata=userdefdata()
plantname=userdata[0]
pitchsize=userdata[1]
Merror=[0.0,1000]#[now,lasthour]
delsensordata()
delET()
proc=subprocess.Popen("python /home/pi/Desktop/Project/sniffer.py", shell=True)
try:
    while True:
        calET=checkpacket()
        if calET==True:
            print "Now has 4 packets, parparaing calculating ET..."
            ET=ETcalculate(plantname)
            print "ET= "+str(ET)
            Merror[0]=Merrornow(plantname)
            #print "Merror= "+str(Merror)
            #print "testmain said pitchsize: "+str(pitchsize)
            t=calt(ET,pitchsize)
            print "t= "+str(t)
            cnx=mysql.connector.connect(**dblogin)
            cursor=cnx.cursor()
            cursor.execute("SELECT Torlerance,Mo_ref FROM plants WHERE Name='%s'"%(plantname))
            output=cursor.fetchone()
            moisture_tol=output[0]
            moisture_ref=output[1]
            #print"moisture_tol: "+str(moisture_tol)
            #print "moisture_ref: "+str(moisture_ref)
            cnx.commit()
            cursor.close()
            cnx.close()
            if Merror[1]==1000.0:
                #print "This is first cycle!"
                k=1
                ET=k*ETcalculate(plantname)
                Merror[0]=Merrornow(plantname)
                t=calt(ET,pitchsize)
                if Merror[0]<0 or Merror[0]==0:
                    water_off()
                    ETindex=ETindex+1.0
                    accumET=ET+accumET
                    print " "
                    print "A"
                    print "water off"
                    print "ETindex: "+str(ETindex)
                    print "accumET: "+str(accumET)
                elif Merror[0]>moisture_tol*moisture_ref/100.0:
                    water_on(t)
                    accumET=0
                    ETindex=1
                    print " "
                    print "B"
                    print "water on for "+str(t)+" seconds"
                    print " "
                elif Merror[0]<moisture_tol*moisture_ref/100.0 or Merror[0]==moisture_tol*moisture_ref/100.0:
                    if (accumET/ETindex)>ETcritical or (accumET/ETindex)==ETcritical:
                        water_on(t)
                        accumET=0
                        ETindex=1
                        print""
                        print"C"
                        print "water on for "+str(t)+" second"
                        print" "
                    else:
                        water_off()
                        accumET=accumET+ET
                        ETindex=ETindex+1.0
                        print""
                        print"D"
                        print"water off"
                        print""
            if Merror[1]!=1000.0:
                Merror[0]=Merrornow(plantname)
                #print str(pitchsize)+"wedfs"
                #print "Now Merror is: "+str(Merror[0])
                #print "Last Merror is: "+str(Merror[1])
                #print" more than 1 cycle!!"
                if Merror[0]-Merror[1]>0 or Merror[0]-Merror[1]==0:
                    k=abs(Merror[0]-Merror[1])/Merror[1]+1
                if Merror[0]-Merror[1]<0:
                    k=1
                #print str(k)+"sdfsdf"
                ET=k*ETcalculate(plantname)
                #print str(ET)+"sdfsdf"
                Merror[1]=Merror[0]
                t=calt(ET,pitchsize)
                #print str(t)+"sdf"
                if Merror[1]<0 or Merror[1]==0:
                    water_off()
                    ETindex=ETindex+1.0
                    accumET=ET+accumET
                    print""
                    print"E"
                    print " water off"
                    print""
                elif Merror[1]>moisture_tol*moisture_ref/100.0:
                    water_on(t)
                    accumET=0
                    ETindex=1
                    print""
                    print"F"
                    print "water on for "+str(t)+" second"
                    print""
                elif Merror[1]<moisture_tol*moisture_ref/100.0 or Merror[1]==moisture_tol*moisture_ref/100.0:
                    if (accumET/ETindex)>ETcritical or (accumET/ETindex)==ETcritical:
                        water_on(t)
                        accumET=0
                        ETindex=1
                        print""
                        print "G"
                        print "water on for "+str(t)+" second"
                        print""
                    else:
                        water_off()
                        accumET=accumET+ET
                        ETindex=ETindex+1.0
                        print""
                        print"H"
                        print "water off"
                        print""
            delsensordata()
            Merror[1]=Merror[0]
except:
    os.killpg(os.getpgid(proc.pid),signal.SIGTERM)
