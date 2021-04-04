import re
from types import MethodDescriptorType
from flask import Flask, render_template, request, redirect, url_for, session
import connect
import psycopg2
import uuid
class finance:
    def __init__(self, startdate='', enddate='', report='', cur=''):
        self.startdate = startdate
        self.enddate = enddate
        self.report = report
        self.cur = cur
    
    def reportTool(self):
        if self.report == 'revenue':
            return self.revenue()
        elif self.report == 'usage':
            return self.gymUsage()
        elif self.report == 'popular':
            return self.popularClass()

    def revenue(self):
        self.cur.execute(f'''SELECT b.paymentplan AS "Payment Plan", SUM(a.paidprice) AS "Revenue", COUNT(DISTINCT a.memberid) AS "Number of Members"\
                        FROM payment a\
                        LEFT JOIN member b\
                        ON a.memberid = b.memberid\
                        WHERE paymentdate >= '{self.startdate}' AND paymentdate <= '{self.enddate}' AND paymentstatus = 'Paid'\
                        GROUP BY b.paymentplan''')
        results = self.cur.fetchall()
        title = 'Revenue by Payment Type'
        values = [item[1] for item in results]
        labels = [item[0] for item in results]
        colors = [
            "#F7464A", "#46BFBD", "#FDB45C", "#FEDCBA",
            "#C71585", "#FF4500", "#FEDCBA",
            "#ABCDEF", "#DDDDDD", "#ABCABC", "#4169E1"]
        self.cur.execute(f'''SELECT b.paymentplan AS "Payment Plan", EXTRACT (YEAR FROM paymentdate) AS "Year", \
                EXTRACT (MONTH FROM paymentdate) AS "Month", SUM(a.paidprice) AS "Revenue", \
                COUNT(DISTINCT a.memberid) AS "Number of Members"\
                FROM payment a\
                LEFT JOIN member b\
                ON a.memberid = b.memberid\
                WHERE paymentdate >= '{self.startdate}' AND paymentdate <= '{self.enddate}' AND paymentstatus = 'Paid'\
                GROUP BY b.paymentplan, EXTRACT (YEAR FROM paymentdate), EXTRACT (MONTH FROM paymentdate)\
                ORDER BY EXTRACT (YEAR FROM paymentdate), EXTRACT (MONTH FROM paymentdate) DESC''')
        results = self.cur.fetchall()
        cols = [item[0] for item in self.cur.description]
        return render_template('finance.html', set=zip(values, labels, colors), role = session['role'], 
        startdate = self.startdate, enddate = self.enddate, report = self.report, max=17000, title = title, results = results, cols = cols,)
    
    def gymUsage(self):
        self.cur.execute(f"WITH groupclass AS (\
                        SELECT COUNT(*)\
                        FROM groupsessionattendance a\
                        LEFT JOIN groupsession b\
                        ON a.groupsessionid = b.groupsessionid\
                        WHERE a.attendancestatus = 'Attended' AND b.groupsessionstartdate BETWEEN '{self.startdate}' AND '{self.enddate}')\
                        , privateclass AS (\
                        SELECT COUNT(*)\
                        FROM personalsessionbooking\
                        WHERE personalsessiondate BETWEEN '{self.startdate}' AND '{self.enddate}')\
                        , gymVisit AS (\
                        SELECT COUNT(*)\
                        FROM gymVisit\
                        WHERE gymvisitdate BETWEEN '{self.startdate}' AND '{self.enddate}')\
                        SELECT * FROM gymVisit\
                        UNION\
                        SELECT * FROM groupclass\
                        UNION\
                        SELECT * FROM privateclass\
                        ")
        values = [item[0] for item in self.cur.fetchall()]
        labels = ['Gym Visit', 'Group Class Attendance', 'Private Training Booking']
        title = 'Gym Usage by Type of Visits'
        return render_template('finance.html', values=values, labels=labels, set=zip(labels, values), role = session['role'], 
        startdate = self.startdate, enddate = self.enddate, report = self.report, max=max(values)+20, title = title)

    def popularClass (self):
        self.cur.execute(f'''SELECT c.groupexerciseid, c.groupclassname AS "Class Name", count(*) AS "Total Bookings"\
                    FROM groupsessionbooking a\
                    LEFT JOIN groupsession b\
                    ON a.groupsessionid = b.groupsessionid \
                    LEFT JOIN groupexercise c\
                    ON b.groupexerciseid = c.groupexerciseid\
                    WHERE b.groupsessionstartdate BETWEEN '{self.startdate}' AND '{self.enddate}'\
                    GROUP BY c.groupexerciseid, c.groupclassname\
                        ORDER BY count(*) DESC
                    ''')
        results = self.cur.fetchall()
        labels = [item[1] for item in results]
        values = [item[2] for item in results]
        title = 'Popular Group Classes'
        return render_template('finance.html', values=values, labels=labels, results=results, role = session['role'], 
        startdate = self.startdate, enddate = self.enddate, report = self.report, max=max(values)+20, title = title)

        
        