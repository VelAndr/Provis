#!/usr/bin/python
# -*- coding:utf8 -*-
import web
import random, string, re

urls = (
'/prov/(.+)/(.+)/(.+)', 'prov',
'/profile', 'prof',
'/pedit/(.*)', 'pedit',
'/device', 'device',
'/dedit/(.+)', 'dedit',
'/exten', 'exten',
'/eedit/(.+)', 'eedit',
'/mobcall', 'mobcall',

'/', 'dummy'
    )

render = web.template.render('templates', base='base')

# Функция для генерации паролей
def genpasswd():
    return "".join(random.choice(string.letters + string.digits) for i in range(8))

class mobcall:
    def GET(self):
        return render.mobcall()

    def POST(self):
        raise web.seeother('/mobcall')

class dummy:
    def GET(self):
        return "Hello world"


class prof: # Отображает и редактирует список профилей
    def GET(self):
        a={}
        b=[]
        res=db1.query('SELECT qwe.id AS id, qwe.name as name, qwe.type as type, '
                      'count(distinct qwe.prof) as records, count(distinct qwe.dev) as devices '
                      'FROM (SELECT profile.id AS id, profile.name AS name, profile.type AS type, profdata.name AS prof, device.mac as dev '
                      'FROM profile LEFT JOIN profdata ON profile.id = profdata.prof_id '
                      'LEFT JOIN device ON profile.id=device.profile) AS qwe GROUP BY qwe.name')
        for i in res:
            a[i.id]=[i.name,i.type,i.records,i.devices]
        res=db1.query('SELECT DISTINCT type FROM device')
        for i in res:
            b.append(i.type)
        return render.profile_list(a,b)

    def POST(self):
        parm=web.input(delet=[])
        if parm.formname=="add":
            db1.insert('profile',name=parm.newprof,type=parm.device)
        elif parm.formname=="delete":
            for i in parm.delet:
                ii=int(i)
                db1.delete('profdata',where='prof_id="'+str(ii)+'"')
                db1.delete('profile',where='id="'+str(ii)+'"')
        elif parm.formname=="copy":
            #     Сначала определяем тип профиля по имени, затем создаем профиль в таблице, а затем копируем данные
            res=db1.query('select type from profile where id="'+parm.prof+'"')
            curtype=res[0].type
            seq=db1.insert('profile',name=parm.newprof, type=curtype)
            res=db1.select('profdata',where='prof_id="'+parm.prof+'"')
            for i in res:
                db1.insert('profdata',prof_id=seq, name=i.name, parm=i.parm, value=i.value)
        raise web.seeother('/profile')

class pedit:
    def GET(self,prof):
        parm=web.input()

        tailsql=""
        if 'fold' in parm:
            tailsql=' AND fold="{0}"'.format(int(parm.fold))
        res=db1.query('SELECT * FROM profdata WHERE prof_id={0}{1}'.format(prof,tailsql))
        a={}
        for i in res:
            a[i.id]=[i.name, i.parm, i.value]
        return render.profile_edit(prof,a)

    def POST(self,prof):
        parm=web.input(myfile={}, delet=[])
        patt = "\s*\<(\w+)\sua=\"(\w\w)\"(.*)$"
        patt2 = "\>(.*)\<\/"
        if parm.formname=="update":
            if parm.id=="":
                db1.insert('profdata',prof_id=prof,name=parm.name,parm=parm.parm,value=parm.value)
            else:
                ii=int(parm.id)
                db1.update('profdata', where='id="'+str(ii)+'"', name=parm.name.strip(), parm=parm.parm.strip(), value=parm.value.strip())

        elif parm.formname=="delete":
            if 'del' in parm:
                for i in parm.delet:
                    ii=int(i)
                    db1.query('delete from profdata where id="'+str(ii)+'"')
            elif 'move' in parm:
                for i in parm.delet:
                    ii=int(i)
                    db1.update('profdata',where='id="'+str(ii)+'"', fold=parm.foldr)

        elif parm.formname=="upload":
            for i in parm['myfile'].file:
                i.rstrip("\r\n")
                qwe = re.match(patt, i)
                if qwe:
                    pnam = qwe.group(1)
                    pdop = qwe.group(2)
                    qwe2 = re.match(patt2, qwe.group(3))
                    pval=qwe2.group(1)
                    if len(pnam)<48 and len(pdop)<8 and len(pval)<128:
                        db1.insert('profdata',prof_id=prof,name=pnam,parm=pdop,value=pval)
        raise web.seeother('/pedit/'+prof)

############   DEVICE - управление списком устройств
class device:
    def GET(self):
        parm=web.input()
        det=1
        sqltail=''
        if 'list' in parm:
            if parm['list']=='U':
                det=0
                sqltail='WHERE exten.user IS NULL'
            elif parm['list']=='L':
                sqltail='WHERE exten.user IS NOT NULL'
        a={}
        ind={}
        res = db1.query('SELECT device.id AS id, device.type AS type, device.mac AS mac, device.serial AS sernum, device.place AS place, '
                        'device.comment AS comment, profile.name AS profile, exten.user AS user, exten.callerid AS callerid, link.line AS line '
                        'FROM device LEFT JOIN link ON device.id=link.dev_id '
                        'LEFT JOIN exten ON exten.id=link.ext_id '
                        'LEFT JOIN profile ON device.profile=profile.id '+sqltail)
        for i in res:
            devmac=i.mac
            if type(i.user)==unicode:
                str1="{0}: {1} ({2})".format(i.line,i.user,i.callerid)
            else:
                str1 = ""
            if not devmac in a: # Такого девайса нет - подготавливаем массивы и прочее
                devtyp=i.type
                a[devmac]=['','','','','','']
                a[devmac][0]=i.id
                if not i.type in ind:
                    ind[devtyp]=[]
                ind[devtyp].append(i.mac)
                a[devmac][1]=i.sernum            # Серийный номер устройства
                if type(i.profile)==unicode:
                    a[devmac][2]=i.profile            # Профиль
                else:
                    a[devmac][2]="- не определен -"            # Профиль
                a[devmac][4]=i.place                      # Местоположение
                a[devmac][5]=i.comment                      # Местоположение
                a[devmac][3]=[]               # Массив пользователей
            a[devmac][3].append(str1)
            b=ind.keys() # Получаем типы устройств
            b.sort()     # и сортируем их
            for j in b:
                ind[j].sort()
        return render.device_list(det,a,b,ind)

    def POST(self):
        parm=web.input(delet=[])
        strstr=""
        if parm.formname=='delete':
            for i in parm.delet:
                ii=int(i)
                db1.query('delete from link where dev_id="'+str(ii)+'"')
                db1.query('delete from device where id="'+str(ii)+'"')
        raise web.seeother('/device')

############   DEDIT - редактирование устройства
class dedit:
    def GET(self,device):
        res = db1.query('SELECT device.mac AS mac, device.type AS type, device.serial AS serial, '
                        'device.place AS place, device.comment AS comment, device.profile AS profile '
                        'FROM device WHERE device.id='+device)
#        l=() # [mac,type,serial,place,comment,prof_id,device_id]
        b={} # для списка профилей
        c={} # для списка подключенных линий
        qwe=res[0]
        a=[qwe.mac, qwe.type, qwe.serial, qwe.place, qwe.comment, qwe.profile,device]
        res=db1.query('SELECT id,name FROM profile WHERE type="'+qwe.type+'"')
        for i in res:
            sel=""
            if a[5]==i.id:
                sel='selected=""'
            b[i.id]=[i.name,sel]
        res=db1.query('SELECT link.line AS line, exten.user AS user FROM link,exten '
                      'WHERE link.dev_id='+device+' and link.ext_id=exten.id')
        for i in res:
            c[i.line]=i.user
        return render.device_edit(a,b,c)

    def POST(self,device):
        parm=web.input()
        if parm.formname=="change":
            db1.update('device',where='id="'+device+'"', place=parm.place, comment=parm.comment, profile=parm.profile)
        elif parm.formname=="unlink":
            db1.delete('link',where='dev_id="'+device+'"')
        raise web.seeother('/device')

############   EXTEN - управление списком пользователей
class exten: # Ввод и редактирование екстеншенов
    def GET(self):
        parm=web.input()
        det=1
        sqltail=''
        if 'list' in parm:
            if parm['list']=='U':
                det=0
                sqltail=' WHERE device.mac IS NULL'
            elif parm['list']=='L':
                sqltail=' WHERE device.mac IS NOT NULL'
        a={}
        res = db1.query('SELECT exten.id AS id, exten.user AS user, exten.password AS password , exten.callerid AS callerid, '
                        'device.type AS type , device.mac AS mac, link.line AS line '
                        'FROM exten '
                        'LEFT JOIN link ON exten.id = link.ext_id '
                        'LEFT JOIN device ON device.id = link.dev_id'+sqltail)
        count=len(res)
        for i in res:
            user=i.user
            if type(i.type)==unicode:
                temp='{0} / {1} / {2}'.format(i.type,i.mac,i.line)
            else:
                temp="- Не подключено -"
            a[user]=[i.id, i.password, i.callerid, temp]
            b=a.keys()
            b.sort()
        return render.exten_list(det,a,b)

    def POST(self):
        parm=web.input(delet=[])
        if parm.formname=='addgroup':
            st=int(parm.startnum)
            en=int(parm.endnum)
            if (en>st) and (len(str(st))==len(str(en))) and ((en-st)<1000):
                for i in range(st,en):
                    db1.insert('exten',user=str(i),password=genpasswd(),callerid='user_'+str(i))
        elif parm.formname=='add':
            db1.insert('exten',user=parm.user,password=parm.password,callerid=parm.callerid)
        elif parm.formname=='delete':
            for i in parm.delet:
                ii=int(i)
                db1.query('delete from link where ext_id="'+str(ii)+'"')
                db1.query('delete from exten where id="'+str(ii)+'"')
        raise web.seeother('/exten')

############   EEDIT - редактирование конкретного пользователя
class eedit:
    def GET(self,exten):
        res = db1.query('SELECT exten.user AS user, exten.password AS passwd, exten.callerid AS callerid, '
                        'device.type AS type , device.mac AS mac, device.place AS place, link.line AS line '
                        'FROM exten '
                        'LEFT JOIN link ON exten.id = link.ext_id '
                        'LEFT JOIN device ON device.id = link.dev_id '
                        'WHERE exten.id='+exten)
        if(len(res)==1):
            a={}
            b={}
            qwe=res[0]
            a[0]=qwe.user            # 0
            a[1]=qwe.passwd        # 1
            a[2]=qwe.callerid        # 2
            if type(qwe.type)==unicode:
                a[3]=qwe.type
                a[4]=qwe.place
                if a[4]=="":
                    a[4]='место не определено'
                a[5]=qwe.mac
                a[6]=qwe.line
            else:
                a[3]="!"
                res = db1.query('SELECT device.id AS id, device.type AS type, device.mac AS mac, '
                        'device.place AS place, link.line AS line '
                        'FROM device LEFT JOIN link ON device.id=link.dev_id')
                for i in res:
                    if not i.mac in b:
                        b[i.mac]=[i.id,i.type,i.place,[]]
                    if(type(i.line)==long):
                        b[i.mac][3].append(i.line)
            return render.exten_edit(a,b)
        else:
            return "Error in database data!!!"

    def POST(self,exten):
        parm=web.input()
        if parm.formname=="change":
            db1.update('exten',where='id="'+exten+'"', password=parm.passw, callerid=parm.callerid)
        elif parm.formname=="link":
            db1.insert('link',dev_id=parm.device, line=parm.line,ext_id=exten)
            pass;
        elif parm.formname=="unlink":
            db1.delete('link',where='ext_id="'+exten+'"')
        raise web.seeother('/exten')

############   PROV - собственно сам провиженинг - вывод XML
class prov:
    def GET(self, devmac, devtype, devserial):
        a={}
        outstr=''
        patt='(.*)#([UPC])#(\d+)#(.*)'  # Начало(1), затем юзер/пароль(2) и линия(3), и конец строки(4)
        if len(devmac)<13 and len(devtype)<10 and len(devserial)<15: # Базовая проверка от инжектинга
            res = db1.select('device', where='mac=\"' + devmac + '\"')
            if not len(res): # new device
                db1.insert('device', mac=devmac, type=devtype, serial=devserial)
                outstr=' A new device.'
            else: # Такой девайс существует
                qq=res[0]
                cudev=qq.id
                curprof=qq.profile
                res=db1.query('SELECT exten.user AS user, exten.callerid as callerid, exten.password AS password, link.line AS line FROM link,exten '
                              'where link.dev_id={0} AND link.ext_id=exten.id'.format(cudev))
                if len(res)==0:
                    return "Device is not attached..."
                for i in res: # Заполняем этот хеш для каждого пользователя
                    a[i.line]=[i.user, i.callerid, i.password]
                outstr="""<?xml version="1.0" encoding="ISO-8859-1"?>
<flat-profile>
"""
                res=db1.query('SELECT name,parm,value FROM profdata WHERE prof_id={0}'.format(curprof))
                if len(res)==0:
                    return "Device profile is empty!"
                for i in res:
                    if i.value=="":
                        tmpl='<{0} ua="{1}"/>\r\n'
                    else:
                        vale=i.value
                        qwe=re.match(patt,vale)
                        if qwe:
                            lin=int(qwe.group(3))
                            if lin in a:
                                if qwe.group(2)=="U":
                                    vale=a[lin][0]
                                elif qwe.group(2)=="C":
                                    vale=a[lin][1]
                                else:
                                    vale=a[lin][2]
                            else:
                                vale=''
                            vale=qwe.group(1)+vale+qwe.group(4)
                        tmpl='<{0} ua="{1}">{2}</{0}>\r\n'
                    outstr=outstr+tmpl.format(i.name,i.parm,vale)
                outstr=outstr+"""</flat-profile>
                       """
                db1.query('REPLACE INTO active (dev_id) VALUES ({0})'.format(cudev))
        return outstr


# web.internalerror = web.debugerror
db1 = web.database(dbn='mysql', db='provis', user='provis', pw='qwert')

if __name__ == "__main__":
    app = web.application(urls, globals())
#    app.internalerror = web.debugerror
    app.run()

