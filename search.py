import re
from types import MethodDescriptorType
from flask import Flask, render_template, request, redirect, url_for, session
import connect
import psycopg2
import uuid
from gymClass import gymClass
from trainer import trainer
from user import user

class searchEngine:

    def __init__(self, user_id, role, user_type, cur):
        self.user_id = user_id
        self.role = role
        self.user_type = user_type
        self.cur =cur

# List all members in a trainer's classes
    def memberByTrainer(self):
        self.cur.execute(f"WITH gb AS (SELECT a.trainerid, b.memberid \
                    FROM groupsession a\
                    RIGHT JOIN groupsessionbooking b\
                    ON a.groupsessionid = b.groupsessionid\
                    WHERE a.trainerid = {self.user_id})\
                    , pb AS (SELECT trainerid, memberid FROM personalsessionbooking WHERE trainerid = {self.user_id})\
                    , all_member AS (SELECT memberid FROM gb UNION  SELECT memberid FROM pb\
                    GROUP BY memberid)\
                    SELECT m.memberid, m.firstname, m.lastname, u.role\
                    FROM member m\
                    LEFT JOIN all_member x\
                    ON m.memberid = x.memberid\
                    LEFT JOIN userlog u\
                    ON u.userid = m.userid")
        results = self.cur.fetchall()
        cols = [item[0] for item in self.cur.description]
        return results, cols


# List of available trainer for private booking
    def privateAvailability(self, date, time):
        self.cur.execute(f"WITH excl_trainer AS(\
                    SELECT * FROM personalsessionbooking\
                    WHERE personalsessiondate = '{date}' AND personalsessionstarttime = '{time}'\
                    )\
                    SELECT b.trainerid, b.firstname, b.lastname, b.availabilitystarttime, b.availabilityendtime FROM excl_trainer a\
                    RIGHT JOIN trainer b\
                    ON a.trainerid = b.trainerid\
                    WHERE a.trainerid IS NULL AND ('{time}' BETWEEN b.availabilitystarttime AND b.availabilityendtime)\
                    AND b.leftdate IS NULL")
        results = self.cur.fetchall()
        cols = [item[0] for item in self.cur.description]
        return results, cols

# Generate a list of group classes for dropdown selection in search form
    def trainerGroupClasses(self):
        if self.role == 'manager':
            self.cur.execute("SELECT groupexerciseid, groupclassname FROM groupexercise")
        elif self.role == 'trainer':
            self.cur.execute(f"SELECT c.groupexerciseid, c.groupclassname \
                            FROM userlog a\
                            INNER JOIN trainer b\
                            ON a.userid = b.userid\
                            INNER JOIN groupsession d\
                            ON d.trainerid = b.userid\
                            INNER JOIN groupexercise c\
                            ON d.groupexerciseid = c.groupexerciseid \
                            WHERE a.userid = {self.user_id}\
                                GROUP BY c.groupexerciseid, c.groupclassname;"
                            )#Add else for member?
        classes = self.cur.fetchall()
        return classes

# Generate a list of private classes for dropdown selection in search form
    def trainerPrivateClasses(self):
        if self.role == 'manager':
            self.cur.execute("SELECT d.memberid, d.firstname, d.lastname, \
                            c.personalsessiondate, c.personalsessionstarttime, \
                            c.personalsessionendtime \
                            FROM personalsessionbooking c\
                            INNER JOIN member d\
                            ON c.memberid = d.memberid"
                        )
        elif self.role == 'trainer':
            self.cur.execute(f"SELECT d.memberid, d.firstname, d.lastname, c.personalsessiondate, \
                            c.personalsessionstarttime, c.personalsessionendtime \
                            FROM userlog a\
                            INNER JOIN trainer b\
                            ON a.userid = b.userid\
                            INNER JOIN personalsessionbooking c\
                            ON b.trainerid = c.trainerid\
                            INNER JOIN member d\
                            ON c.memberid = d.memberid\
                            WHERE a.userid = {self.user_id} AND d.leftdate IS NULL AND b.leftdate IS NULL;"
                            )
        classes = self.cur.fetchall()
        return classes

# Search members by group class
    def userGroupClass(self, first_name='%', surname='%', paymentplan='%', group_class_id='%', userid='%', user_type=None):
        #userid here is the id of the user you are searching for, not your own id aka self.user_id
        if user_type == 'member':
            if userid == '%':
                self.cur.execute("SELECT a.userid, a.firstname, a.lastname FROM member a\
                    INNER JOIN groupsessionbooking b\
                    ON a.userid = b.memberid\
                    INNER JOIN groupsession c\
                    ON b.groupsessionid = c.groupsessionid\
                    INNER JOIN groupexercise d\
                    ON c.groupexerciseid = d.groupexerciseid\
                    WHERE d.groupexerciseid = %s AND a.firstname LIKE %s \
                    AND a.lastname LIKE %s AND a.paymentplan LIKE %s\
                    AND a.leftdate IS NULL\
                    GROUP BY a.userid, a.firstname, a.lastname;", (str(group_class_id), first_name, surname, paymentplan)
                    )
            else:
                self.cur.execute(f"SELECT a.userid, a.firstname, a.lastname FROM member a\
                    INNER JOIN groupsessionbooking b\
                    ON a.userid = b.memberid\
                    INNER JOIN groupsession c\
                    ON b.groupsessionid = c.groupsessionid\
                    INNER JOIN groupexercise d\
                    ON c.groupexerciseid = d.groupexerciseid\
                    WHERE d.groupexerciseid = {group_class_id} AND a.userid = {userid} AND a.firstname LIKE '{first_name}' \
                    AND a.lastname LIKE '{surname}' AND a.paymentplan LIKE '{paymentplan}' AND a.leftdate IS NULL\
                    GROUP BY a.userid, a.firstname, a.lastname;"
                    )
        else:
            if userid == '%':
                print('dododo',first_name,surname,group_class_id)
                self.cur.execute(f"SELECT a.userid, a.firstname, a.lastname FROM trainer a\
                    INNER JOIN groupsession b\
                    ON a.userid = b.trainerid\
                    INNER JOIN groupexercise d\
                    ON b.groupexerciseid = d.groupexerciseid\
                    WHERE d.groupexerciseid = {group_class_id} AND a.firstname LIKE'{first_name}' \
                    AND a.lastname LIKE '{surname}' AND a.leftdate IS NULL\
                    GROUP BY a.userid, a.firstname, a.lastname;"
                    )
            else:
                self.cur.execute(f"SELECT a.userid, a.firstname, a.lastname FROM trainer a\
                    INNER JOIN groupsession c                               \
                    ON a.userid = c.trainerid\
                    INNER JOIN groupexercise d\
                    ON c.groupexerciseid = d.groupexerciseid\
                    WHERE d.groupexerciseid = {group_class_id} AND a.userid = {userid} AND a.firstname LIKE '{first_name}' \
                    AND a.lastname LIKE '{surname}' AND a.leftdate IS NULL\
                    GROUP BY a.userid, a.firstname, a.lastname;"
                    )
        users = self.cur.fetchall()
        db_cols = [item[0] for item in self.cur.description]
        return users, db_cols

# Search members by private class
    def userPrivateClass(self, classid='%', user_type='%'):
        if user_type=='member':
            self.cur.execute('SELECT a.userid, a.firstname, a.lastname FROM member a\
                        INNER JOIN personalsessionbooking b\
                        ON a.userid = b.memberid\
                        WHERE b.personalsessionbookingid = {} AND a.leftdate IS NULL;'.format(classid)
                        )
        else:
            self.cur.execute('SELECT a.userid, a.firstname, a.lastname FROM trainer a\
                INNER JOIN personalsessionbooking b\
                ON a.userid = b.memberid\
                WHERE b.personalsessionbookingid = {} AND a.leftdate IS NULL;'.format(classid)
                )
        users = self.cur.fetchall()
        db_cols = [item[0] for item in self.cur.description[2:]]
        return users, db_cols

# Search member by member attributes, without class ids
    def userList(self, firstname='%', surname='%', userid='%', paymentplan='%', availabilitystarttime='%', usertype=None):
        # search with userid - but be separated because wildcard requires '' in the query
        if userid != '%':
            if usertype == 'member':
                self.cur.execute("SELECT a.userid, a.firstname, a.lastname FROM member a\
                    INNER JOIN userlog b\
                    ON a.userid = b.userid\
                    WHERE a.firstname LIKE '{}' AND a.lastname LIKE '{}' \
                    AND a.userid LIKE {} AND a.paymentplan LIKE '{}' AND a.leftdate IS NULL"
                    .format(firstname, surname, userid, paymentplan))
            else:
                if availabilitystarttime=='%':
                    self.cur.execute("SELECT a.userid, a.firstname, a.lastname FROM trainer a\
                        INNER JOIN userlog b\
                        ON a.userid = b.userid\
                        WHERE a.firstname  LIKE '{}' AND a.lastname  LIKE '{}' \
                        AND a.userid  LIKE {} AND a.leftdate IS NULL;"
                        .format(firstname, surname, userid))
                else:
                    self.cur.execute("SELECT a.userid, a.firstname, a.lastname FROM trainer a\
                    INNER JOIN userlog b\
                    ON a.userid = b.userid\
                    WHERE a.firstname  LIKE '{}' AND a.lastname  LIKE '{}' \
                    AND a.userid  LIKE {} AND a.availabilitystarttime = CAST('{}' AS TIME)\
                    AND a.leftdate IS NULL;"
                    .format(firstname, surname, userid, availabilitystarttime))

        # search without userid
        else:
            if usertype == 'member':
                self.cur.execute("SELECT a.userid, a.firstname, a.lastname FROM member a\
                    INNER JOIN userlog b\
                    ON a.userid = b.userid\
                    WHERE a.firstname LIKE '{}' AND a.lastname LIKE '{}' \
                    AND a.paymentplan LIKE '{}' AND a.leftdate IS NULL;".format(firstname, surname, paymentplan))
                print('winwinwinw')
            else:
                if availabilitystarttime == '%':
                    self.cur.execute("SELECT a.userid, a.firstname, a.lastname FROM trainer a\
                    INNER JOIN userlog b\
                    ON a.userid = b.userid\
                    WHERE a.firstname  LIKE '{}' AND a.lastname  LIKE '{}'\
                    AND a.leftdate IS NULL;"
                    .format(firstname, surname))

                else:
                    self.cur.execute(f"SELECT a.userid, a.firstname, a.lastname FROM trainer a\
                        INNER JOIN userlog b\
                        ON a.userid = b.userid\
                        WHERE a.firstname  LIKE '{firstname}' AND a.lastname  LIKE '{surname}' \
                        AND a.availabilitystarttime = CAST('{availabilitystarttime}' AS TIME)\
                        WHERE a.leftdate IS NULL;")

        users = self.cur.fetchall()
        db_cols = [item[0] for item in self.cur.description]
        return users, db_cols

    def userList(self, firstname='%', surname='%', userid='%', paymentplan='%', availabilitystarttime='%', usertype=None):
        # search with userid - but be separated because wildcard requires '' in the query
        if userid != '%':
            if usertype == 'member':
                self.cur.execute("SELECT a.userid, a.firstname, a.lastname FROM member a\
                    INNER JOIN userlog b\
                    ON a.userid = b.userid\
                    WHERE a.firstname  LIKE '{}' AND a.lastname  LIKE '{}' \
                    AND a.userid  LIKE {} AND a.paymentplan  LIKE '{}' AND a.leftdate IS NULL"
                    .format(firstname, surname, userid, paymentplan))
            else:
                if availabilitystarttime=='%':
                    self.cur.execute("SELECT a.userid, a.firstname, a.lastname FROM trainer a\
                        INNER JOIN userlog b\
                        ON a.userid = b.userid\
                        WHERE a.firstname  LIKE '{}' AND a.lastname  LIKE '{}' \
                        AND a.userid  LIKE {} AND a.leftdate IS NULL;"
                        .format(firstname, surname, userid))
                else:
                    self.cur.execute("SELECT a.userid, a.firstname, a.lastname FROM trainer a\
                    INNER JOIN userlog b\
                    ON a.userid = b.userid\
                    WHERE a.firstname  LIKE '{}' AND a.lastname  LIKE '{}' \
                    AND a.userid  LIKE {} AND a.availabilitystarttime = CAST('{}' AS TIME)\
                    AND a.leftdate IS NULL;"
                    .format(firstname, surname, userid, availabilitystarttime))

        # search without userid
        else:
            if usertype == 'member':
                print('shoo',firstname, surname, paymentplan)
                self.cur.execute("SELECT a.userid, a.firstname, a.lastname FROM member a\
                    INNER JOIN userlog b\
                    ON a.userid = b.userid\
                    WHERE a.firstname LIKE '{}' AND a.lastname LIKE '{}' \
                    AND a.paymentplan LIKE '{}' AND a.leftdate IS NULL;".format(firstname, surname, paymentplan))
            else:
                if availabilitystarttime == '%':
                    self.cur.execute("SELECT a.userid, a.firstname, a.lastname FROM trainer a\
                    INNER JOIN userlog b\
                    ON a.userid = b.userid\
                    WHERE a.firstname  LIKE '{}' AND a.lastname  LIKE '{}' AND a.leftdate IS NULL;"
                    .format(firstname, surname))

                else:
                    self.cur.execute(f"SELECT a.userid, a.firstname, a.lastname FROM trainer a\
                        INNER JOIN userlog b\
                        ON a.userid = b.userid\
                        WHERE a.firstname  LIKE '{firstname}' AND a.lastname  LIKE '{surname}' \
                        AND a.availabilitystarttime = CAST('{availabilitystarttime}' AS TIME)\
                        AND a.leftdate IS NULL;")

        users = self.cur.fetchall()
        db_cols = [item[0] for item in self.cur.description]
        return users, db_cols
