import re
from types import MethodDescriptorType
from flask import Flask, render_template, request, redirect, url_for, session
import connect
import psycopg2
import uuid
class trainer:
    def __init__(self, userid, cur):
        self.userid = userid
        self.cur = cur
        
    def individualTrainerGroup(self):
        self.cur.execute("WITH sessionbooking AS (\
                SELECT groupsessionid, count(*) AS bookings\
                FROM groupsessionbooking\
                GROUP BY groupsessionid)\
                SELECT a.userid, a.firstname, a.lastname, c.groupclassname, \
                CASE WHEN SUM(d.bookings)>0 THEN SUM(d.bookings)\
                ELSE 0 END AS Bookings\
                CASE WHEN SUM(d.bookings)>0 THEN SUM(d.bookings)/COUNT(DISTINCT b.groupsessionid)\
                ELSE 0 END AS [Avg Bookings Per Session]\
                FROM trainer a\
                LEFT JOIN groupsession b\
                ON a.trainerid = b.trainerid\
                LEFT JOIN groupexercise c\
                ON b.groupexerciseid = c.groupexerciseid\
                LEFT JOIN sessionbooking d\
                ON d.groupsessionid = b.groupsessionid\
                WHERE a.userid={}\
                GROUP BY a.userid, a.firstname, a.lastname, c.groupclassname\
                ORDER BY bookings;".format(self.userid))
        results = self.cur.fetchall()
        cols = [item[0] for item in self.cur.description]
        return results, cols

    def allTrainerGroup(self):
        self.cur.execute("WITH sessionbooking AS (\
                SELECT groupsessionid, count(*) AS bookings\
                FROM groupsessionbooking\
                GROUP BY groupsessionid)\
                SELECT a.userid, a.firstname, a.lastname, c.groupclassname, \
                CASE WHEN SUM(d.bookings)>0 THEN SUM(d.bookings)\
                ELSE 0 END AS Bookings\
                CASE WHEN SUM(d.bookings)>0 THEN SUM(d.bookings)/COUNT(DISTINCT b.groupsessionid)\
                ELSE 0 END AS [Avg Bookings Per Session]\
                FROM trainer a\
                LEFT JOIN groupsession b\
                ON a.trainerid = b.trainerid\
                LEFT JOIN groupexercise c\
                ON b.groupexerciseid = c.groupexerciseid\
                LEFT JOIN sessionbooking d\
                ON d.groupsessionid = b.groupsessionid\
                GROUP BY a.userid, a.firstname, a.lastname, c.groupclassname\
                ORDER BY bookings;")
        results = self.cur.fetchall()
        cols = [item[0] for item in self.cur.description]
        return results, cols

    def individualTrainerPrivate(self):
        self.cur.execute(f"SELECT trainerid, count(*)\
                FROM personalsessionbooking\
                GROUP BY trainerid\
                WHERE trainerid = {self.userid}")
        results = self.cur.fetchall()
        cols = [item[0] for item in self.cur.description]
        return results, cols

    def allTrainerPrivate(self):
        self.cur.execute("SELECT trainerid, count(*)\
                FROM personalsessionbooking\
                GROUP BY trainerid")
        results = self.cur.fetchall()
        cols = [item[0] for item in self.cur.description]
        return results, cols

    def TrainerGroupSummary(self):
        self.cur.execute(f"WITH sessionbooking AS (\
                    SELECT groupsessionid, count(*) AS bookings\
                    FROM groupsessionbooking\
                    GROUP BY groupsessionid)\
                    SELECT a.userid, a.firstname, a.lastname, COUNT(DISTINCT c.groupclassname), COUNT(DISTINCT b.groupsessionid),\
                    CASE WHEN SUM(d.bookings)>0 THEN SUM(d.bookings)/COUNT(DISTINCT b.groupsessionid)\
                    ELSE 0 END AS Avg_Bookings_Per_Session\
                    FROM trainer a\
                    LEFT JOIN groupsession b\
                    ON a.trainerid = b.trainerid\
                    LEFT JOIN groupexercise c\
                    ON b.groupexerciseid = c.groupexerciseid\
                    LEFT JOIN sessionbooking d\
                    ON d.groupsessionid = b.groupsessionid\
                    GROUP BY a.userid, a.firstname, a.lastname;")
        results = self.cur.fetchall()
        cols = [item[0] for item in self.cur.description]
        return results, cols

    def trainerGroupClass(self):
        self.cur.execute(
            f"SELECT a.groupexerciseid, a.groupclassname, a.description, count(c.groupsessionbookingid) AS total_bookings\
            FROM groupexercise AS a\
            LEFT JOIN groupsession AS b\
            ON a.groupexerciseid = b.groupexerciseid\
            LEFT JOIN groupsessionbooking AS c\
            ON c.groupsessionid = b.groupsessionid\
            WHERE b.trainerid = {self.userid}\
            GROUP BY a.groupexerciseid, a.groupclassname, a.description")
        class_details = self.cur.fetchall()
        cols = [item[0] for item in self.cur.description]
        return class_details, cols

    def trainerGroupSession(self, classid):
        self.cur.execute(f"select b.groupsessionid, a.groupclassname, b.groupsessionstartdate, \
                        b.groupsessionstarttime, b.groupsessionendtime \
                        , COUNT(CASE WHEN c.groupsessionbookingid is not null THEN 1 ELSE null END) \
                        from groupexercise a\
                        INNER JOIN groupsession b\
                        ON a.groupexerciseid = b.groupexerciseid\
                        LEFT JOIN groupsessionbooking c\
                        ON c.groupsessionid = b.groupsessionid\
                        WHERE b.trainerid = {self.userid} AND b.groupexerciseid = {classid}\
                        GROUP BY b.groupsessionid, a.groupclassname, b.groupsessionstartdate, \
                        b.groupsessionstarttime, b.groupsessionendtime\
                        ORDER BY b.groupsessionstartdate ASC")
        results = self.cur.fetchall()
        return render_template('session.html', results=results, role=session['role'])

