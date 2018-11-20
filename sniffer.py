import projectlib
from projectlib import *
recorded=False
pipes=[[0x65,0x64,0x6f,0x4e,0x31],[0x65,0x64,0x6f,0x4e,0x32],[0x65,0x64,0x6f,0x4e,0x33],[0x65,0x64,0x6f,0x4e,0x34],[0x65,0x64,0x6f,0x4e,0x35],[0x65,0x64,0x6f,0x4e,0x36]]
radio=NRF24(GPIO,spidev.SpiDev())
radio.begin(0,17)
radio.setRetries(15,15)
radio.setPayloadSize(32)

radio.openReadingPipe(1,pipes[1])
radio.openReadingPipe(2,pipes[2])
radio.openReadingPipe(3,pipes[3])
radio.openReadingPipe(4,pipes[4])
radio.openReadingPipe(5,pipes[5])
radio.openWritingPipe(pipes[0])

radio.startListening()
#radio.printDetails()
packet=1
counter=0
packetlog=0
try:
    while True:
        while not radio.available():
            #print("sniffer said Waiting for data: ")
            time.sleep(1)
        #end while
        while radio.available():
            recorded=False
            packet=counter%4+1
            counter=counter+1
            packetlog=packetlog+1
            data=[]
            string=""
            radio.read(data,32)
            #radio.read(data,30)
            time.sleep(2)
            #print data
            for n in data:
                if (n>=32 and n<=126):
                    string+=chr(n)
                #end if
            #split up data segment
            print "Received row data: "+string
            print "packet is: " + str(packet)
            #print "counter is:"+ str(counter)
            sensor = int(string[2])
            temp=int(string[5:8])/10.0
            hum=int(string[10:13])/10.0
            moisture=101-round(int(string[15:19])*100.0/1023,1)
            light=round(int(string[21:25]),1)
            batt=round((int(string[27:31])*6.6/1023.0-0.9)*100/(2.7-0.9),1)
            #print "SENSOR: "+str(sensor)+"TEMP: "+ str(temp)+"Humidity: "+str(hum)+"Moisture: "+str(moisture)+"Light"+str(light)+"Battery"+str(batt)"
            #Now connect to db
        while recorded==False:
            #print "now connect to db"
            cnx=mysql.connector.connect(**dblogin)
            cursor=cnx.cursor()
            add_data=("INSERT INTO sensordata (sensor,tdatetime, batt, temp, humidity, moisture, sunlight, packet) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)")
            data_sensordata=(sensor,'NOW()',batt,temp,hum,moisture,light,packet)
            query=add_data % data_sensordata
            cursor.execute(query)
            add_data=("INSERT INTO sensordatalog (sensor,tdatetime, batt, temp, humidity, moisture, sunlight, packet) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)")
            data_sensordata=(sensor,'NOW()',batt,temp,hum,moisture,light,packetlog)
            query=add_data % data_sensordata
            cursor.execute(query)
            #disconnect from db
            cnx.commit()
            cursor.close()
            cnx.close()
            recorded=True
except:
    print""
    print " sniffer close"
    sys.exit()
       
