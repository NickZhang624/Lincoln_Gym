import re
from types import MethodDescriptorType
from flask import Flask, render_template, request, redirect, url_for, session
import connect
import psycopg2
import uuid
class gymClass:
    def __init__(self, class_type='', cur='', groupsessionid='', trainerid='', groupexerciseid=''):
        self.class_type = class_type
        self.cur = cur
        self.groupsessionid = groupsessionid
        self.trainerid = trainerid
        self.groupexerciseid = groupexerciseid

    # List all group/private classes    
    def classList(self):
        if self.class_type == 'group':
            self.cur.execute("with bookings AS (SELECT groupsessionID, count(*) AS numofbookings \
                        FROM groupsessionbooking GROUP BY groupsessionID)\
                        SELECT c.groupclassname, d.firstname, d.lastname, c.description, SUM(a.numofbookings) AS bookings, c.groupexerciseID, d.trainerID\
                        FROM groupexercise c\
                        LEFT JOIN groupsession b\
                        ON b.groupexerciseID = c.groupexerciseID\
                        LEFT JOIN bookings a   \
                        ON a.groupsessionID = b.groupsessionID\
                        LEFT JOIN trainer d\
                        ON b.trainerID = d.trainerID\
                        GROUP BY c.groupclassname, d.firstname, d.lastname, c.description, c.groupexerciseID, d.trainerID\
                        ORDER BY bookings DESC;")
        else:
            self.cur.execute("SELECT a.personalsessiondate, a.personalsessionstarttime, a.personalsessionendtime, \
                        d.firstname as trainerfirstname, d.lastname as trainerlastname,\
                        e.firstname as memberfirstname, e.lastname as memberlastname\
                        FROM personalsessionbooking a\
                        JOIN trainer d\
                        ON a.trainerid = d.trainerid\
                        JOIN member e\
                        ON a.memberid = e.memberid;")
        results = self.cur.fetchall()
        cols = [item[0] for item in self.cur.description]
        print(results)
        return results, cols

    def getGroupClass(self):
        self.cur.execute("select b.groupsessionid, \
                        a.groupclassname,c.firstname, c.lastname, \
                        b.groupsessionstartdate,b.groupsessionstarttime,b.groupsessionendtime, b.trainerid\
                        from\
                        groupexercise a, groupsession b, trainer c\
                        where a.groupexerciseid = b.groupexerciseid\
                        and b.trainerid = c.trainerid\
                        and b.groupsessionid =%s and b.trainerid =%s;",(str(self.groupsessionid),str(self.trainerid)))
        select_result = self.cur.fetchall()
        self.cur.execute("select userid, concat(firstname, ' ', lastname) as name from trainer")
        trainer_result = self.cur.fetchall()
        return render_template('groupexercise_update.html',groupexercisedetails = select_result,trainer_result = trainer_result)

    def updateGroupClass(self):
        self.cur.execute("UPDATE groupsession SET trainerid=%s where groupsessionid=%s;",(str(self.trainerid),str(self.groupsessionid)))
        return redirect("/class?type=group")
    
    def groupClassByTrainer(self):
        self.cur.execute("select a.groupexerciseid, c.trainerid, b.groupsessionid, \
            a.groupclassname,c.firstname, c.lastname, \
            a.groupclassstartdate,a.groupclassenddate, \
            b.groupsessionstartdate,b.groupsessionstarttime,b.groupsessionendtime,b.location, a.description from \
            groupexercise a, groupsession b, trainer c \
            where a.groupexerciseid = b.groupexerciseid \
            and b.trainerid = c.trainerid \
            and a.groupexerciseid =%s and b.trainerid =%s \
            order by a.groupclassname;",(str(self.groupexerciseid),str(self.trainerid)))
        select_result = self.cur.fetchall()
        return render_template('groupexercise_view.html',groupexercisedetails = select_result)

    def createGroupClass(self,groupclassname,groupclassstartdate,groupclasssenddate,description):
        self.cur.execute("INSERT INTO GroupExercise (GroupExerciseID, GroupClassName, GroupClassStartDate, GroupClassEndDate, Description) VALUES (%s,%s,%s,%s,%s);",
        (str(self.groupclassid),groupclassname,groupclassstartdate,groupclasssenddate,description))
        return redirect("/class?type=group")
