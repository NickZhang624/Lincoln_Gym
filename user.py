import re
from types import MethodDescriptorType
from flask import Flask, render_template, request, redirect, url_for, session
import connect
import psycopg2
import uuid
class user:
    def __init__(self, userid, cur):
        self.userid = userid
        self.cur = cur
        self.cur.execute("SELECT role FROM userlog WHERE userid={}".format(self.userid))
        self.role = self.cur.fetchone()
        self.role = self.role[0]


    def userDetails(self):
        #if self.userid is None:
         #   self.userid = session['id']
        #self.cur.execute("SELECT role FROM userlog WHERE userid={}".format(self.userid))
        #role = self.cur.fetchone()
        if self.role == 'trainer':
            self.cur.execute("SELECT b.userid, a.role, b.firstname, b.lastname, b.email, b.dateofbirth, \
                        b.joineddate, b.availabilitystarttime, b.availabilityendtime, b.description, b.leftdate \
                        FROM userlog a\
                        INNER JOIN trainer b\
                        ON a.userid = b.userid\
                        WHERE b.userid = {}".format(self.userid))
        else:
            self.cur.execute("SELECT b.userid, a.role, b.firstname, b.lastname, b.email, b.dateofbirth, \
                b.joineddate, b.newslettersubscription, b.paymentplan, b.leftdate, b.membershipexpirydate\
                FROM userlog a\
                INNER JOIN member b\
                ON a.userid = b.userid\
                WHERE b.userid = {}".format(self.userid))  
        user_details = self.cur.fetchone()
        db_cols = [item[0] for item in self.cur.description]
        return user_details, db_cols



    def allTrainerGroup():
        cur = getCursor()
        cur.execute("WITH sessionbooking AS (\
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
        results = cur.fetchall()
        cols = [item[0] for item in cur.description]
        return results, cols

    def allTrainerPrivate(self):
        cur = getCursor()
        cur.execute("SELECT trainerid, count(*)\
                FROM personalsessionbooking\
                GROUP BY trainerid")
        results = cur.fetchall()
        cols = [item[0] for item in cur.description]
        return results, cols

    def TrainerGroupSummary(self):
        cur = self.cur
        self.cur.execute(f"WITH sessionbooking AS (\
                    SELECT groupsessionid, count(*) AS bookings\
                    FROM groupsessionbooking\
                    GROUP BY groupsessionid)\
                    SELECT a.userid, a.firstname, a.lastname, \
                    COUNT(DISTINCT c.groupclassname) AS num_of_groupclasses, COUNT(DISTINCT b.groupsessionid) AS num_of_groupsessions,\
                    CASE WHEN SUM(d.bookings)>0 THEN ROUND(SUM(d.bookings)/COUNT(DISTINCT b.groupsessionid), 1)\
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
        cols = [item[0] for item in cur.description]
        return results, cols

    def updateProfile(self):
        firstname = request.form.get('firstname')
        surname = request.form.get('surname')
        dob = request.form.get('dob')
        email = request.form.get('email')
        userid = request.form.get('userid')
        role = request.form.get('role')
        if role == 'member':
            newslettersubscription = request.form.get('newsletter')
            paymentplan = request.form.get('paymentplan')
            self.cur.execute("UPDATE member\
                SET firstname=%s, lastname=%s, email=%s, dateofbirth=%s, newslettersubscription=%s, paymentplan=%s\
                    WHERE userid=%s", (firstname, surname, email, dob, newslettersubscription, paymentplan, userid))
            return redirect('/profile?userid={}'.format(userid))
            user_details = user_profile, cols = db_cols, role=session['role']
        else:
            starttime = request.form.get('starttime')
            endtime = request.form.get('endtime')
            description = request.form.get('description')
            description = description.replace("'", "''") #Need to make all single apostrophe double apostrophe to update sql
            self.cur.execute(f'''UPDATE trainer\
                SET firstname='{firstname}', lastname='{surname}', email='{email}', dateofbirth='{dob}',availabilitystarttime='{starttime}'\
                    , availabilityendtime='{endtime}', description='{description}'\
                    WHERE userid={userid}''')#MUST BE REDONE
            return redirect('/profile?userid={}'.format(userid))
    
    def deactivateUser(self):
        if self.role=='trainer':
            self.cur.execute(f"WITH groupclass AS (\
                            SELECT a.userid, b.groupsessionid FROM trainer a\
                            JOIN groupsession b\
                            ON a.trainerid = b.trainerid\
                            WHERE userid = {self.userid}\
                            )\
                            , privateclass As (\
                            SELECT a.userid, b.personalsessionbookingid FROM trainer a\
                            JOIN personalsessionbooking b\
                            ON a.trainerid = b.trainerid\
                            WHERE userid = {self.userid})\
                            SELECT * FROM groupclass\
                            UNION\
                            SELECT * FROM privateclass")
            results = self.cur.fetchall()
            if len(results) > 0:
                msg = 'You cannot deactivate the trainer as they are still assigned to a group or private class session'
                return render_template('error.html', msg = msg)
            else:
                self.cur.execute(f"UPDATE trainer SET leftdate = DATE(NOW()) WHERE trainerid = {self.userid}")
                return redirect('/profile/all?usertype=trainer')
        elif self.role == 'member':
            self.cur.execute(f"UPDATE member SET leftdate = DATE(NOW()) WHERE memberid = {self.userid}")
            return redirect('/profile/all?usertype=member')

# Summary of group classes a member is enrolled in
    def memberGroupClassSummary(self):
        print(self.userid)
        self.cur.execute(f"SELECT a.memberid, d.groupexerciseid, d.groupclassname\
                        , count(*) FILTER (WHERE e.attendancestatus='Attended') AS Attendance\
                        , count(*) AS Bookings\
                        , 100*(count(*) FILTER (WHERE e.attendancestatus='Attended')) / count(*) AS AttendacenRate\
                        FROM member a\
                        LEFT JOIN groupsessionbooking b\
                        ON a.memberid = b.memberid\
                        LEFT JOIN groupsession c\
                        ON c.groupsessionid = b.groupsessionid\
                        LEFT JOIN groupexercise d\
                        ON c.groupexerciseid = d.groupexerciseid\
                        LEFT JOIN groupsessionattendance e\
                        ON b.groupsessionid = e.groupsessionid AND e.memberid = a.memberid\
                        WHERE a.memberid = {self.userid}\
                        GROUP BY a.memberid, d.groupexerciseid, d.groupclassname")
        results = self.cur.fetchall()
        return results
    
    #Summary of all private classes a member is subscribed to
    def memberPrivateClassSummary(self):
        self.cur.execute(f"SELECT a.personalsessionbookingid AS bookingid, a.memberid, a.trainerid,\
                    c.firstname, c.lastname, d.firstname, d.lastname,\
                    a.personalsessiondate, a.personalsessionstarttime, a.personalsessionendtime,\
                    a.note, b.attendancestatus\
                    FROM personalsessionbooking a\
                    LEFT JOIN personalsessionattendance b\
                    ON a.personalsessionbookingid = b.personalsessionbookingid\
                    LEFT JOIN member c\
                    ON c.memberid = a.memberid\
                    LEFT JOIN trainer d\
                    ON d.trainerid = a.trainerid\
                    WHERE a.memberid = {self.userid} --AND personalsessiondate >= DATE(NOW())")
        results = self.cur.fetchall()
        return results

    def trainerGroupClassSummary(self):
        print(self.userid)
        self.cur.execute(f"SELECT a.trainerid, d.groupexerciseid, d.groupclassname\
                        , count(distinct b.groupsessionid) AS NumOfSessions\
                        ,100*(count(*) FILTER (WHERE e.attendancestatus='Attended')) / count(*) AS AttendacenRate\
                        FROM trainer a\
                        LEFT JOIN groupsession b\
                        ON a.trainerid = b.trainerid\
                        LEFT JOIN groupsessionbooking c\
                        ON c.groupsessionid = b.groupsessionid\
                        LEFT JOIN groupexercise d\
                        ON b.groupexerciseid = d.groupexerciseid\
                        LEFT JOIN groupsessionattendance e\
                        ON b.groupsessionid = e.groupsessionid\
                        WHERE a.trainerid = {self.userid}\
                        GROUP BY a.trainerid, d.groupexerciseid, d.groupclassname")
        
        results = self.cur.fetchall()
        print(results)
        return results

    def trainerPrivateClassSummary(self):
        self.cur.execute(f"SELECT to_char(a.personalsessiondate, 'YYYY-MM') AS Period, COUNT(*)\
                    FROM personalsessionbooking a\
                    LEFT JOIN trainer c\
                    ON c.trainerid = a.trainerid\
                    WHERE a.trainerid = {self.userid} \
                    GROUP BY to_char(a.personalsessiondate, 'YYYY-MM')\
                    ORDER BY Period DESC")
        results = self.cur.fetchall()
        return results

    def memberFutureGroupBookings (self):
        self.cur.execute(f"SELECT a.groupclassname, b.groupsessionstartdate, b.groupsessionstarttime, \
                        b.groupsessionendtime, b.location\
                        FROM groupexercise a\
                        LEFT JOIN groupsession b\
                        ON a.groupexerciseid = b.groupexerciseid\
                        LEFT JOIN groupsessionbooking c\
                        ON b.groupsessionid = c.groupsessionid\
                        WHERE c.memberid = {self.userid} --AND groupsessionstartdate >= DATE(NOW())")
        results = self.cur.fetchall()
        return results

    def memberFuturePrivateBookings (self):
        self.cur.execute(f"SELECT personalsessiondate, personalsessionstarttime, personalsessionendtime,\
                b.firstname, b.lastname, b.trainerid\
                FROM personalsessionbooking a\
                LEFT JOIN trainer b\
                ON a.trainerid = b.trainerid\
                WHERE memberid = {self.userid} --AND personalsessionstartdate >= DATE(NOW()) ")
        results = self.cur.fetchall()
        return results

    def trainerFutureGroupBookings (self):
        self.cur.execute(f"SELECT a.groupclassname, b.groupsessionstartdate, b.groupsessionstarttime, \
                        b.groupsessionendtime, b.location\
                        FROM groupexercise a\
                        LEFT JOIN groupsession b\
                        ON a.groupexerciseid = b.groupexerciseid\
                        LEFT JOIN groupsessionbooking c\
                        ON b.groupsessionid = c.groupsessionid\
                        WHERE b.trainerid = {self.userid} AND groupsessionstartdate >= DATE(NOW())")
        results = self.cur.fetchall()
        return results

    def trainerFuturePrivateBookings (self):
        self.cur.execute(f"SELECT personalsessiondate, personalsessionstarttime, personalsessionendtime,\
                b.firstname, b.lastname, b.memberid\
                FROM personalsessionbooking a\
                LEFT JOIN member b\
                ON a.memberid = b.memberid\
                WHERE a.trainerid = {self.userid} --AND personalsessionstartdate >= DATE(NOW()) ")
        results = self.cur.fetchall()
        return results


    def generateProfile(self):
        user_details = self.userDetails()
        user_profile = user_details[0]
        db_cols = user_details[1]
        if session['role'] == 'manager':
            if self.role == 'member':
                group_class_summary = self.memberGroupClassSummary()
                private_class_summary = self.memberPrivateClassSummary()
                return render_template('profile.html', user_details = user_profile, user_type = user_profile[1], cols = db_cols, 
                role=session['role'], groupclass=group_class_summary, privateclass=private_class_summary)
           
            elif self.role == 'trainer':
                group_class_summary = self.trainerGroupClassSummary()
                private_class_summary = self.trainerPrivateClassSummary()
                print(group_class_summary, private_class_summary)
                return render_template('profile.html', user_details = user_profile, user_type = user_profile[1], cols = db_cols, 
                role=session['role'], groupclass=group_class_summary, privateclass=private_class_summary)


        elif session['role'] == 'member':
            group_class_summary = self.memberFutureGroupBookings()
            private_class_summary = self.memberFuturePrivateBookings()
            return render_template('profile.html', user_details = user_profile, user_type = user_profile[1], cols = db_cols, 
            role=session['role'], groupclass=group_class_summary, privateclass=private_class_summary)

        elif session['role'] == 'trainer':
            group_class_summary = self.trainerFutureGroupBookings()
            private_class_summary = self.trainerFuturePrivateBookings()
            return render_template('profile.html', user_details = user_profile, user_type = user_profile[1], cols = db_cols, 
            role=session['role'], groupclass=group_class_summary, privateclass=private_class_summary)

        return render_template('profile.html', user_details = user_profile, user_type = user_profile[1], cols = db_cols, role=self.role)
