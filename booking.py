import re
from types import MethodDescriptorType
from flask import Flask, render_template, request, redirect, url_for, session
import connect
import psycopg2
import uuid
class booking:
    def __init__(self, memberid='', trainerid='', cur = '', sessionid='', time='', date=''
    , groupsessionbookingid='', groupsessionid='',starttime='',endtime='',
    classname='',firstname='',lastname=''):
        self.memberid = memberid
        self.trainerid = trainerid
        self.sessionid = sessionid
        self.time = time
        self.date = date
        self.cur = cur
        self.groupsessionid = groupsessionid
        self.starttime = starttime
        self.endtime = endtime
        self.classname = classname
        self.firstname = firstname
        self.lastname = lastname
        self.groupsessionbookingid = groupsessionbookingid


    # Display the private booking details for members to confirm and pay
    def privateBookingConfirm(self):
        paymentplan = 'Hourly' #All private sessions are 1 hour long with fixed rate
        self.cur.execute(f"SELECT cost FROM price WHERE paymentplan='{paymentplan}'")
        price = self.cur.fetchone()
        self.cur.execute(f"SELECT firstname, lastname FROM trainer WHERE trainerid={self.trainerid};")
        trainer_name = self.cur.fetchone()
        return render_template("booking_confirm.html", price = price[0], memberid=self.memberid, trainerid=self.trainerid, 
        trainerfirstname=trainer_name[0], trainerlastname=trainer_name[1], time=self.time, date=self.date, role=session['role'])
        
    def addPrivateBooking(self, price, paymentid, notes):
        self.cur.execute(f"INSERT INTO payment (paymentid, memberid, paymentstatus, paidprice, paymentduedate, paymentdate, paymentplan)\
            VALUES ({paymentid}, {self.memberid}, 'Paid', {price}, DATE(NOW()), DATE(NOW()), 'Hourly');\
            INSERT INTO personalsessionbooking(personalsessionbookingid, memberid, trainerid, personalsessiondate, \
                    personalsessionstarttime, personalsessionendtime, price, bookingdate, bookingtime, paymentid, note)\
                    VALUES ( {self.sessionid}, {self.memberid}, {self.trainerid}, '{self.date}', '{self.time}', \
                        '{self.time}' + INTERVAL '1 hour', {price}, DATE(NOW()), CURRENT_TIME, {paymentid}, '{notes}');\
                    INSERT INTO personalsessionattendance VALUES ({self.sessionid}, {self.memberid}, {self.sessionid}, '')")
        msg = 'Booking Successful. Thank you for your payment.'
        return render_template('error.html', msg=msg, role=session['role'])

    def groupBookingOption(self, groupexerciseid, allgroupclasses):
        self.cur.execute("WITH booked_session AS (SELECT b.*\
                    FROM groupsessionbooking a\
                    RIGHT JOIN groupsession b\
                    ON a.groupsessionid = b.groupsessionid\
                    WHERE a.memberid = {})\
                    , all_session AS(SELECT b.groupsessionstartdate, b.groupsessionstarttime, b.groupsessionendtime,\
                    c.groupclassname, d.firstname, d.lastname, b.groupsessionid, \
                    SUM(CASE WHEN a.groupsessionbookingid is null THEN 0 ELSE 1 END),\
                    CASE WHEN e.groupsessionid IS NOT NULL THEN 'Booked'\
                    ELSE 'Not Booked'\
                    END AS bookingstatus\
                    FROM groupsessionbooking a\
                    RIGHT JOIN groupsession b\
                    ON a.groupsessionid = b.groupsessionid\
                    RIGHT JOIN groupexercise c\
                    ON b.groupexerciseid = c.groupexerciseid\
                    INNER JOIN trainer d\
                    ON b.trainerid = d.trainerid\
                    LEFT JOIN booked_session e\
                    ON b.groupsessionid = e.groupsessionid\
                    WHERE b.groupexerciseid = {} \
                    GROUP BY b.groupsessionstartdate, b.groupsessionstarttime, b.groupsessionendtime,\
                    c.groupclassname, d.firstname, d.lastname, b.groupsessionid, bookingstatus)\
                    SELECT groupsessionstartdate, groupsessionstarttime, groupsessionendtime\
                    ,groupclassname, firstname, lastname, groupsessionid, sum\
                    , CASE WHEN sum >= 30 THEN 'Full'\
                    ELSE bookingstatus\
                    END AS bookingstatus\
                    FROM all_session".format(self.memberid, groupexerciseid))
        classlist = self.cur.fetchall()
        return render_template('group_booking.html',role=session['role'],classlist=classlist, select_result= allgroupclasses)

    
    def groupBookingConfirm(self):
        return render_template("group_booking_confirm.html", groupsessionid=self.groupsessionid, memberid=self.memberid, date=self.date,
        starttime=self.starttime, endtime = self.endtime, classname= self.classname,firstname= self.firstname,
        lastname= self.lastname,role=session['role'])

    def addGroupBooking(self,note):
        self.cur.execute(f"INSERT INTO groupsessionbooking(groupsessionbookingid,memberid,groupsessionid,bookingdate,bookingtime,note) \
            VALUES ({self.groupsessionbookingid},{self.memberid},{self.groupsessionid},DATE(NOW()),CURRENT_TIME,'{note}');\
                INSERT INTO groupsessionattendance(groupsessionattendanceid, memberid, groupsessionid) VALUES({self.groupsessionbookingid},{self.memberid},{self.groupsessionid})")
        msg = 'Booking Successful!'
        return render_template('error.html', msg=msg, role=session['role'])

    def memberAttendanceList(self):
        self.cur.execute(f"SELECT a.groupsessionattendanceid, d.groupclassname, b.groupsessionstartdate, \
                        b.groupsessionstarttime, b.groupsessionendtime, a.attendancestatus, c.memberid\
                        FROM groupsessionattendance a\
                        LEFT JOIN groupsession b\
                        ON a.groupsessionid = b.groupsessionid\
                        INNER JOIN member c\
                        ON a.memberid = c.memberid\
                        INNER JOIN groupexercise d\
                        ON b.groupexerciseid = d.groupexerciseid\
                        WHERE c.memberid = {self.memberid}")
        results = self.cur.fetchall()
        return render_template('attendance.html', results=results, role=session['role'])

    def trainerAttendanceList(self, sessionid):
        self.cur.execute(f"SELECT a.groupsessionattendanceid, d.groupclassname, b.groupsessionstartdate, \
                        b.groupsessionstarttime, b.groupsessionendtime, a.attendancestatus, e.memberid, e.firstname, e.lastname\
                        FROM groupsessionattendance a\
                        LEFT JOIN groupsession b\
                        ON a.groupsessionid = b.groupsessionid\
                        INNER JOIN trainer c\
                        ON b.trainerid = c.trainerid\
                        INNER JOIN groupexercise d\
                        ON b.groupexerciseid = d.groupexerciseid\
                        INNER JOIN member e\
                        ON e.memberid = a.memberid\
                        WHERE c.trainerid = {self.trainerid} AND b.groupsessionid = {sessionid}")
        results = self.cur.fetchall()
        return render_template('attendance.html', results=results, role=session['role'], sessionid = sessionid)


    def memberAttendanceUpdate(self, status, sessionid, role, groupsession=''):
        self.cur.execute(f"UPDATE groupsessionattendance\
            SET attendancestatus = '{status}'\
                        WHERE groupsessionattendanceid = {sessionid}")
        if role == 'member':
            return self.memberAttendanceList()
        else:
            return self.trainerAttendanceList(groupsession)