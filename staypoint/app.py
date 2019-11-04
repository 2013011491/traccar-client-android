from flask import Flask, render_template, redirect, request
import psycopg2 as pg
import psycopg2.extras
import datetime
import time
from math import radians, cos, sin, asin, sqrt, atan2

app = Flask(__name__)

rows=[[]]
cleanrows=[]
stayPointRows=[]

iternum=0
devicenum=0

@app.route("/")
def index():
    return render_template("index.html",iternum=iternum,datalist=cleanrows,staypoint=stayPointRows,devicenum=1)
    #return render_template("index1.html")

def getDistance(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a)) 
    m = 6371000 * c  #지구평균반지름 6371000km
    return m

def getduration(pointi,pointj):
    t_i = time.mktime(pointi[-1].timetuple())+pointi[-1].microsecond/1E6
    t_j = time.mktime(pointj[-1].timetuple())+pointj[-1].microsecond/1E6
    return t_j - t_i


def computMeanCoord(gpsPoints):
    lon = 0.0
    lat = 0.0
    for point in gpsPoints:
        lon += float(point[1])
        lat += float(point[2])
    return (lon/len(gpsPoints), lat/len(gpsPoints))

# default values of distThres and timeThres are 200 m and 30 min respectively, according to [1]
def stayPointExtraction(distThres = 0.02, timeThres = 20*60, iternum=0, device_id=0,trows=[]):
    stayPointList = []
    i = 0
    while i < iternum-1: 
        j = i+1
        while j < iternum:
            field_pointi = [trows[i][1],trows[i][2]]
            field_pointj = [trows[j][1],trows[j][2]]
            dist = getDistance(float(field_pointi[0]),float(field_pointi[1]),
                               float(field_pointj[0]),float(field_pointj[1]))
            
            if dist > distThres:
                t_i = time.mktime(trows[i][-1].timetuple())+trows[i][-1].microsecond/1E6
                t_j = time.mktime(trows[j][-1].timetuple())+trows[j][-1].microsecond/1E6
                deltaT = t_j - t_i
                #print(dist,deltaT)
                if deltaT > timeThres:
                    sp = [0,0,0,0,0]
                    sp[0], sp[1] = computMeanCoord(trows[i:j])
                    sp[2], sp[3] = int(t_i), int(t_j)
                    sp[4] = device_id
                    stayPointList.append(sp)
                break
            j += 1
        # Algorithm in [1] lacks following line
        i = j
    return stayPointList

def removenoise(spedThres=0.1,distThres=0.1):
    global rows
    cleanData=[rows[0]]
    prevPoint=rows[0]
    for i in range(1,len(rows)-1):
        deltaT = getduration(prevPoint,rows[i])
        if deltaT ==0 :
            continue
        #print(i,' ',deltaT,' ', prevPoint[-1], rows[i][-1])
        velo = getDistance(float(prevPoint[1]),float(prevPoint[2]),float(rows[i][1]),float(rows[i][2]))/deltaT
        if velo<spedThres:
            cleanData.append(rows[i])
            prevPoint=rows[i]
        else:
            if getDistance(float(rows[i][1]),float(rows[i][2]),float(rows[i+1][1]),float(rows[i+1][2]))<distThres:
                prevPoint=rows[i]
    return cleanData

          
def main():
    global rows,iternum,stayPointRows,devicenum
    db_connect = {
        'host': '211.195.121.179', #for client
        #'host': '127.0.0.1', #for server
        'port': '5432',
        'user': 'postgres',
        'dbname': 'postgres',
        'password':'0000'
    }

    connect_string = "host={host} user={user} dbname={dbname} password={password} port={port}".format(**db_connect)
    print(connect_string)

    conn = pg.connect(connect_string) #연결,예외처리 생략
    cur=conn.cursor(cursor_factory=psycopg2.extras.DictCursor) #cursor 지정
    cur.itersize = 100000
    
    sql = "SELECT id FROM tc_devices;"
    cur.execute(sql)
    devicenum = cur.fetchall()
    devicenum = len(devicenum)
    for index in range(1,2):
        cur.execute("SELECT deviceid,latitude,longitude from tc_positions where deviceid=%s and devicetime between to_timestamp('2019-09-24 00:00:00', 'YYYY-MM-DD HH24:MI:SS') and to_timestamp('2019-09-24 23:59:00','YYYY-MM-DD HH24:MI:SS') ORDER BY fixtime;",[index])
        rows=cur.fetchall()
        #print(len(rows))
        #cleanrows.append(removenoise(1000))
        #print(len(cleanrows[index-3]))
        #in here, insert stay point algorithm
        #stayPointRows.append(stayPointExtraction(20, 60*60, len(cleanrows[index-3]),index,cleanrows[index-3]))
    '''print(len(stayPointRows[0]))
    for i in range(0,len(cleanrows)):
        for j in range(0,len(cleanrows[i])):
            cleanrows[i][j]=cleanrows[i][j][0:-1]
    #print(cleanrows)'''
    '''for index in range(3,devicenum+3):
        cur.execute("SELECT deviceid,latitude,longitude,altitude from tc_positions where deviceid=%s and devicetime between to_timestamp('2019-06-20 00:00:00', 'YYYY-MM-DD HH24:MI:SS') and to_timestamp('2019-06-20 23:59:00','YYYY-MM-DD HH24:MI:SS');",[index])
        rows.append(cur.fetchall())'''  
    #iternum=len(rows[0])+len(rows[1])
    cur.execute("SELECT deviceid,latitude,longitude,altitude,fixtime from tc_positions where deviceid=1 and devicetime between to_timestamp('2019-06-04 00:00:00', 'YYYY-MM-DD HH24:MI:SS') and to_timestamp('2019-06-04 23:59:00','YYYY-MM-DD HH24:MI:SS');")
    temp=cur.fetchall()
    #print(getduration(temp[0],temp[1]))
    #print(getDistance(cleanrows[0][0][1],cleanrows[0][0][2],cleanrows[0][1][1],cleanrows[0][1][2]))
    
if __name__=='__main__' :
    main()
    #app.run(host='169.254.137.212')
    app.run(debug=True)
    