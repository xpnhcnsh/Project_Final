import subprocess
import datetime
import time
import RPi.GPIO as GPIO
from lib_nrf24 import NRF24
import mysql.connector
import math
import ephem
import spidev
import sys
import os
import signal

#def gloable parameters
ETcritical=0.0000015
recorded=False
settime=18
calET=False
c_n=0.0
c_d_d=0.0
c_d_n=0.0
moisture_tol=0.0
moisture_ref=0.0
m_actual=0.0
Merror=[0.0,1000]#[now,lasthour]
ET=0.0
k=1
i=0
flag=0
accumET=0.0
ETindex=1
ETcritical=0.0
t=0
plantindex=0
#user defined data
userdata=['',0.0]#['plantname',pitchsize]
plantname="default"
pitchsize=0.0
elevation=0
#sensordata
packetmax=[1,2,3,4]
humidity=[0,0,0,0]
temp=[0,0,0,0]
sun=[0,0,0,0]
moisture=[0,0,0,0]
#GPIO pins setup
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
zone_01_pin=4
zone_02_pin=5
zone_03_pin=6
zone_04_pin=13
windsensor=19

#SQL login data
dblogin={
    'host':'localhost',
    'user':'root',
    'password':'459101071',
    'database':'capstone',
    }

#userdefdata
def userdefdata():
    '''cnx=mysql.connector.connect(**dblogin)
    cursor=cnx.cursor()
    query="SELECT * FROM plants;"
    cursor.execute(query)
    row=len(cursor.fetchall())'''
    #input plant type and check if it exists in db
    plantname=str(raw_input("Please input your plant name: "))
    print "You have choosen: "+plantname
    userdata[0]=plantname
    try:
        #try to connect db 
        cnx=mysql.connector.connect(**dblogin)
        cursor=cnx.cursor()
        cursor.execute("SELECT Name, Mo_ref,Torlerance,C_N,C_D_d,C_D_n FROM plants WHERE Name='%s'"%(plantname))
        output=cursor.fetchone()
        moisture_ref=output[1]
        moisture_tol=output[2]
        c_n=output[3]
        c_d_d=output[4]
        c_d_n=output[5]
        print "Lucky! Found in database: "
        print " "
        print "Reference moisture: "+str(moisture_ref)+'%'
        print "Moisture Torlerance: "+str(moisture_tol)+'%'
        print "c_n: "+str(c_n)
        print "c_d_day: "+str(c_d_d)
        print "c_d_night: "+str(c_d_n)
        cursor.execute("UPDATE userdata SET plantname='%s'"%(plantname))
        print "Data uploaded!"
        print " "
        #disconnect from db
        cnx.commit()
        cursor.close()
        cnx.close()
    except:
        print "Error: No such data found!"
 
    #input pich size and store in db
    pitchsize=int(raw_input("Please input your pitch size in meter square: "))
    print "Your pitch size is set to be: "+str(pitchsize)
    userdata[1]=pitchsize
    try:
        #try to connect to db 
        cnx=mysql.connector.connect(**dblogin)
        cursor=cnx.cursor()
        cursor.execute("UPDATE userdata SET pitch=%s"%(pitchsize))
        print "Data uploaded!"
        print " "
        #disconnect from db
        cnx.commit()
        cursor.close()
        cnx.close()
    except:
        print "Error: Data upload fail!"

    #input elevation and store in db
    elevation=float(raw_input("Please input your elevation: "))
    print "Your elevation is set to be: "+str(elevation)
    try:
        #try to connect to db 
        cnx=mysql.connector.connect(**dblogin)
        cursor=cnx.cursor()
        cursor.execute("UPDATE userdata SET elevation=%s"%(elevation))
        print "Data uploaded!"
        print " "
        #disconnect from db
        cnx.commit()
        cursor.close()
        cnx.close()
    except:
        print "Error: Data upload fail!"
    return userdata
#end userdefdata
    
#pipinsetup()
def rpipinsetup():
    GPIO.setmode(GPIO.BCM)  #use GPIO pins rather than board pins
    GPIO.setwarnings(False)
    GPIO.setup(zone_01_pin,GPIO.OUT)
    GPIO.setup(zone_02_pin,GPIO.OUT)
    GPIO.setup(zone_03_pin,GPIO.OUT)
    GPIO.setup(zone_04_pin,GPIO.OUT)
    GPIO.output(zone_01_pin,GPIO.LOW)
    GPIO.output(zone_02_pin,GPIO.LOW)
    GPIO.output(zone_03_pin,GPIO.LOW)
    GPIO.output(zone_04_pin,GPIO.LOW)
    GPIO.setup(windsensor,GPIO.IN)
#end rpipinsetup
#winspeed
def windspeed():
    edge=0
    start=time.time()
    while True:
        channel=GPIO.wait_for_edge(windsensor,GPIO.RISING,timeout=1)
        if channel is None:
            pass
        else:
            edge=edge+1
        if edge>=10:
            break
    stop=time.time()
    time.sleep(0.05)
    u=0.1+0.875*50/(stop-start)
    return u


#edgedetect
def edgedetect():
    while True:
        GPIO.setup(26,GPIO.IN)
        channel=GPIO.wait_for_edge(26,GPIO.RISING,timeout=50)
        if channel is None:
            edge=edge+1
        return edge
    
#time setup
def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")

def now_date():
    return datetime.datetime.now().strftime("%Y-%m-%d")

def now_time():
    return datetime.datetime.now().strftime("%H-%M-%S")

def now_SQL():
    return "ADDTIME("+now_date()+","+now_time()+")"

def watering_on_all():
    GPIO.output(zone_01_pin,GPIO.LOW)
    print now()+" Zone 1 ON ..."
    GPIO.output(zone_02_pin,GPIO.LOW)
    print now()+" Zone 2 ON ..."
    GPIO.output(zone_03_pin,GPIO.LOW)
    print now()+" Zone 3 ON ..."
    GPIO.output(zone_04_pin,GPIO.LOW)
    print now()+" Zone 4 ON ..."
    query="UPDATE routinelog SET executed='1' WHERE executed='0' 
	AND tdatetime<NOW() and event='water on';"
    recorded=False
    attempt=1
    while recorded==False:
        try:
            ##connect to db
            cnx=mysql.connector.connect(**dblogin)
            cursor=cnx.cursor()
            print now()+"mySQL connected"
            print (now()+"mySQL: "+ query),
            cursor.execute(query)
            print "executed"
            cnx.commit()
            cursor.close()
            cnx.close()
            time.sleep(1)
            recorded=True
            print now()+"mySQL: connection closed"
        except:
            print now()+" Data rejected, retrying connection, No."+str(attemp)
            attempt+=1
            if i==3:
                print now()+"ERROR: Unalble warite to Database"
                break
#end watering_on()


#delsensordata
def delsensordata():
    cnx=mysql.connector.connect(**dblogin)
    cursor=cnx.cursor()
    cursor.execute("SELECT * FROM sensordata;")
    row=len(cursor.fetchall())
    if row!=0:
        print "Deleting the existing sensordata..."
        print " "
        cursor.execute("DELETE FROM sensordata;")
        cnx.commit()
        time.sleep(1)
    else:
        pass
    cursor.execute("SELECT * FROM sensordata;")
    row=len(cursor.fetchall())
    if row==0:
        print "Sensordata is empyt now!"
        print " "
        time.sleep(1)
    cnx.commit()
    cursor.close()
    cnx.close()
#end delsensordata
#delete et
def delET():
    cnx=mysql.connector.connect(**dblogin)
    cursor=cnx.cursor()
    cursor.execute("SELECT * FROM et;")
    row=len(cursor.fetchall())
    if row!=0:
        print "Deleting the existing ETs..."
        print " "
        cursor.execute("DELETE FROM et;")
        cnx.commit()
        time.sleep(1)
    else:
        pass
    cursor.execute("SELECT * FROM et;")
    row=len(cursor.fetchall())
    if row==0:
        print "ET is empyt now!"
        print " "
        time.sleep(1)
    cnx.commit()
    cursor.close()
    cnx.close()
#end delET

    
#checkpacket
def checkpacket():
    cnx=mysql.connector.connect(**dblogin)
    cursor=cnx.cursor()
    query="SELECT * FROM sensordata"
    cursor.execute(query)
    row=len(cursor.fetchall())
    calET=False
    if row==4:
        calET=True
    if row<4:
        time.sleep(3)
        calET=False
    return calET


#calculate moisture error
def Merrornow(name):
    #connect to db
    cnx=mysql.connector.connect(**dblogin)
    cursor=cnx.cursor()
    #fetch moisture data and calculate average moisture
    for value in packetmax:
        cursor.execute("SELECT moisture FROM sensordata WHERE packet =%s"%(value))
        output=cursor.fetchone()
        moisture[value-1]=output[0]
    m_actual=(moisture[0]+moisture[1]+moisture[2]+moisture[3])/4.0
    #fetch moisture_ref
    cursor.execute("SELECT Mo_ref FROM plants WHERE Name='%s'"%(name))
    output=cursor.fetchone()
    moisture_ref=output[0]
    Merror=(-m_actual+moisture_ref)
    cnx.commit()
    cursor.close()
    cnx.close()
    return Merror
    

#calET
def ETcalculate(plantname):
    cnx=mysql.connector.connect(**dblogin)
    cursor=cnx.cursor()
    cursor.execute("SELECT Name, Mo_ref,Torlerance,C_N,C_D_d,C_D_n FROM plants WHERE Name='%s'"%(plantname))
    output=cursor.fetchone()
    c_n=output[3]
    c_d_d=output[4]
    c_d_n=output[5]
    #print "calculating ET..."
    #fetch temp data and calculate T_actual
    for value in packetmax:
        cursor.execute("SELECT temp FROM sensordata WHERE packet =%s"%(value))
        output=cursor.fetchone()
        temp[value-1]=output[0]
    T_actual=(temp[0]+temp[1]+temp[2]+temp[3])/4.0
    #print "T_actual: "+str(T_actual)
    #humidity
    for value in packetmax:
        cursor.execute("SELECT humidity FROM sensordata WHERE packet =%s"%(value))
        output=cursor.fetchone()
        humidity[value-1]=output[0]
    H_actual=(humidity[0]+humidity[1]+humidity[2]+humidity[3])/4.0
    #print "H_actual: "+str(H_actual)
    #moisture
    for value in packetmax:
        cursor.execute("SELECT moisture FROM sensordata WHERE packet =%s"%(value))
        output=cursor.fetchone()
        moisture[value-1]=output[0]
    M_actual=(moisture[0]+moisture[1]+moisture[2]+moisture[3])/4.0
    #print "M_actual"+str(M_actual)
    #sunlight
    for value in packetmax:
        cursor.execute("SELECT sunlight FROM sensordata WHERE packet =%s"%(value))
        output=cursor.fetchone()
        sun[value-1]=output[0]
    L_sensor=(sun[0]+sun[1]+sun[2]+sun[3])/4.0
    L_parameter=(10230-10.0*L_sensor)/L_sensor
    L_actual=math.pow(L_parameter,1.33)
    #print"L_actual: "+str(L_actual)
    #delta
    numerator=math.exp((17.27*T_actual)/(T_actual+237.3))*4098*0.6108
    denominator=math.pow(T_actual+237.3,2)
    delta=numerator/denominator
    #print"delta: "+str(delta)
    #p
    p=math.pow((293-0.0065*elevation)/293,5.26)*101.3
    #print"p"+str(p)
    #gamma
    gamma=0.000665*p
    #print"gmma: "+str(gamma)
    #es
    e_Tmax=0.6108*math.exp(17.27*max(temp)/(max(temp)+237.3))
    e_Tmin=0.6108*math.exp(17.27*min(temp)/(min(temp)+237.3))
    es=(e_Tmax+e_Tmin)/2.0
    #print"es: "+str(es)
    #ea
    H_max=max(humidity)
    H_min=min(humidity)
    ea1=e_Tmin*H_max/100.0
    ea2=e_Tmax*H_min/100.0
    ea=(ea1+ea2)/2.0
    #print"ea: "+str(ea)
    #Rs
    Rs=L_actual*0.0000288
    #print"Rs"+str(Rs)
    #Rn
    Rn=(1-0.23)*Rs
    #print"Rn: "+str(Rn)
    #u=windspeed(m/s)
    u=windspeed()
    #calculat ET
    user=ephem.Observer()
    next_sunrise_datetime=user.next_rising(ephem.Sun()).datetime()
    next_sunset_datetime=user.next_setting(ephem.Sun()).datetime()
    it_is_night=next_sunset_datetime<next_sunrise_datetime
    it_is_day=next_sunrise_datetime<next_sunset_datetime
    test=gamma*c_n/(T_actual+273.0)*u*(es-ea)
    #print str(test)+"sfsdfsfwefwef"
    numerator1=0.408*delta*Rn+gamma*c_n/(T_actual+273.0)*u*(es-ea)
    #print "numer: "+str(numerator1)
    if it_is_day:
        denominator1=delta+gamma*(1+c_d_d*u/100.0)
        #print "deno: "+str(denominator1)
    if it_is_night:
        denominator1=delta+gamma*(1+c_d_n*u/100.0)
        #print "deno: "+str(denominator1)
    ET=numerator1/denominator1
    #store ET onto db
    cursor.execute("SELECT * FROM et;")
    row=len(cursor.fetchall())
    cursor.execute("INSERT INTO et (et,cycle) VALUES (%s,%s)"%(ET,row+1))
    cnx.commit()
    cursor.close()
    cnx.close()
    calET=False
    return ET

#calculate valve open druation(second)
def calt(ET,pitchsize):
    #print "Now calculating ET..."
    #print "lib said pitchsize is: "+str(pitchsize)
    #print "lib said ET is: "+str(ET)
    time=ET*pitchsize*4.0
    return time
#water_on
def water_on(value):
    GPIO.output(zone_01_pin,GPIO.HIGH)
    time.sleep(value)
    GPIO.output(zone_01_pin,GPIO.LOW)

#end water_on
#water_off
def water_off():
    GPIO.output(zone_01_pin,GPIO.LOW)
#deletesensordata
def deletesensordata():
    cnx=mysql.connector.connect(**dblogin)
    cursor=cnx.cursor()
    print "Deleting the existing sensordata..."
    print " "
    cursor.execute("DELETE FROM sensordata;")
    cnx.commit()
    query="SELECT * FROM sensordata"
    cursor.execute(query)
    row=len(cursor.fetchall())
    if row==0:
        print "Sensordata is empyt now!"
    cnx.commit()
    cursor.close()
    cnx.close()
#end deletesensordata


def updateetstatus(value):
    cnx=mysql.connector.connect(**dblogin)
    cursor=cnx.cursor
    cursor.execute("SELECT * FROM et;")
    row=len(cursor.fetchall())
    cursor.execute("UPDATE et SET status='%s' WHERE cycle=row"%(value))
    cnx.commit()
    cursor.close()
    cnx.close()












    
