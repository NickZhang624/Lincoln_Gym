import re
from types import MethodDescriptorType
from flask import Flask, render_template, request, redirect, url_for, session
import connect
import psycopg2
import uuid
from gymClass import gymClass
from getGroupClassID import getGroupClassID

dbconn = None

app = Flask(__name__)

# Used for connecting to db
def getCursor():
    global dbconn
    if dbconn == None:
        conn = psycopg2.connect(dbname=connect.dbname, user=connect.dbuser, password=connect.dbpass, host=connect.dbhost, port=connect.dbport)
        conn.autocommit = True
        dbconn = conn.cursor()
        return dbconn
    else:
        return dbconn

def genID():
    return uuid.uuid4().fields[1]

app.secret_key = 'lincoln'

def trainerGroupClasses():
    cur = getCursor()
    if session['role'] == 'manager':
        cur.execute("SELECT groupexerciseid, groupclassname FROM groupexercise c")
    elif session['role'] == 'trainer':
        cur.execute("SELECT c.groupexerciseid, c.groupclassname \
                        FROM userlog a\
                        INNER JOIN trainer b\
                        ON a.userid = b.userid\
                        INNER JOIN groupexercise c\
                        ON b.trainerid = c.trainerid\
                        WHERE a.userid = {};".format(session['id'])
                        )#Add else for member?
    classes = cur.fetchall()
    return classes

def trainerPrivateClasses():
    cur = getCursor()
    if session['role'] == 'manager':
        cur.execute("SELECT d.memberid, d.firstname, d.lastname, \
                        c.personalsessiondate, c.personalsessionstarttime, \
                        c.personalsessionendtime \
                        FROM personalsessionbooking c\
                        INNER JOIN member d\
                        ON c.memberid = d.memberid"
                    )
    elif session['role'] == 'trainer':
        cur.execute("SELECT d.memberid, d.firstname, d.lastname, c.personalsessiondate, \
                        c.personalsessionstarttime, c.personalsessionendtime \
                        FROM userlog a\
                        INNER JOIN trainer b\
                        ON a.userid = b.userid\
                        INNER JOIN personalsessionbooking c\
                        ON b.trainerid = c.trainerid\
                        INNER JOIN member d\
                        ON c.memberid = d.memberid\
                        WHERE a.userid = {};".format(session['id'])
                        )#Add else for member?
    classes = cur.fetchall()
    return classes

def userGroupClass(first_name='%', surname='%', paymentplan='%', group_class_id='%', userid='%', user_type=None):
    cur = getCursor()
    if user_type == 'member':
        if userid == '%':
            print('run')
            cur.execute("SELECT a.userid, a.firstname, a.lastname FROM member a\
                INNER JOIN groupsessionbooking b\
                ON a.userid = b.memberid\
                INNER JOIN groupsession c\
                ON b.groupsessionid = c.groupsessionid\
                INNER JOIN groupexercise d\
                ON c.groupexerciseid = d.groupexerciseid\
                WHERE d.groupexerciseid = %s AND a.firstname LIKE %s \
                AND a.lastname LIKE %s AND a.paymentplan LIKE %s;", (str(group_class_id), first_name, surname, paymentplan)
                )
        else:
            cur.execute("SELECT a.userid, a.firstname, a.lastname FROM member a\
                INNER JOIN groupsessionbooking b\
                ON a.userid = b.memberid\
                INNER JOIN groupsession c\
                ON b.groupsessionid = c.groupsessionid\
                INNER JOIN groupexercise d\
                ON c.groupexerciseid = d.groupexerciseid\
                WHERE d.groupexerciseid = {} AND a.userid = {} AND a.firstname LIKE '{}' \
                AND a.lastname LIKE '{}' AND a.paymentplan LIKE '{}';".format(group_class_id, userid, first_name, surname, paymentplan)
                )
    else:
        if userid == '%':
            cur.execute("SELECT a.userid, a.firstname, a.lastname FROM trainer a\
                INNER JOIN groupsessionbooking b\
                ON a.userid = b.trainerid\
                INNER JOIN groupsession c\
                ON b.groupsessionid = c.groupsessionid\
                INNER JOIN groupexercise d\
                ON c.groupexerciseid = d.groupexerciseid\
                WHERE d.groupexerciseid = {} AND a.firstname LIKE'{}' \
                AND a.lastname LIKE '{}';".format(group_class_id, first_name, surname)
                )
        else:
            cur.execute("SELECT a.userid, a.firstname, a.lastname FROM trainer a\
                INNER JOIN groupsessionbooking b\
                ON a.userid = b.trainerid\
                INNER JOIN groupsession c\
                ON b.groupsessionid = c.groupsessionid\
                INNER JOIN groupexercise d\
                ON c.groupexerciseid = d.groupexerciseid\
                WHERE d.groupexerciseid = {} AND a.userid = {} AND a.firstname LIKE '{}' \
                AND a.lastname LIKE '{}';".format(group_class_id, userid, first_name, surname)
                )
    users = cur.fetchall()
    db_cols = [item[0] for item in cur.description]
    return users, db_cols

def userPrivateClass(classid='%', user_type='%'):
    cur = getCursor()
    if user_type=='member':
        cur.execute('SELECT a.userid, a.firstname, a.lastname FROM member a\
                    INNER JOIN personalsessionbooking b\
                    ON a.userid = b.memberid\
                    WHERE b.personalsessionbookingid = {};'.format(classid)
                    )
    else:
        cur.execute('SELECT a.userid, a.firstname, a.lastname FROM trainer a\
            INNER JOIN personalsessionbooking b\
            ON a.userid = b.memberid\
            WHERE b.personalsessionbookingid = {};'.format(classid)
            )
    users = cur.fetchall()
    db_cols = [item[0] for item in cur.description[2:]]
    return users, db_cols

def trainerAvailability():
    cur = getCursor()
    cur.execute('SELECT availabilitystarttime, availabilityendtime \
        FROM trainer \
        GROUP BY availabilitystarttime, availabilityendtime;'
                )
    availability = cur.fetchall()
    return availability    


def userList(firstname='%', surname='%', userid='%', paymentplan='%', availabilitystarttime='%', usertype=None):
    cur = getCursor()
    # search with userid - but be separated because wildcard requires '' in the query
    if userid != '%':
        if usertype == 'member':
            cur.execute("SELECT a.userid, a.firstname, a.lastname FROM member a\
                INNER JOIN userlog b\
                ON a.userid = b.userid\
                WHERE a.firstname  LIKE '{}' AND a.lastname  LIKE '{}' \
                AND a.userid  LIKE {} AND a.paymentplan  LIKE '{}'".format(firstname, surname, userid, paymentplan))
        else:
            if availabilitystarttime=='%':
                cur.execute("SELECT a.userid, a.firstname, a.lastname FROM trainer a\
                    INNER JOIN userlog b\
                    ON a.userid = b.userid\
                    WHERE a.firstname  LIKE '{}' AND a.lastname  LIKE '{}' \
                    AND a.userid  LIKE {};"
                    .format(firstname, surname, userid))
            else:
                cur.execute("SELECT a.userid, a.firstname, a.lastname FROM trainer a\
                INNER JOIN userlog b\
                ON a.userid = b.userid\
                WHERE a.firstname  LIKE '{}' AND a.lastname  LIKE '{}' \
                AND a.userid  LIKE {} AND a.availabilitystarttime = CAST('{}' AS TIME);"
                .format(firstname, surname, userid, availabilitystarttime))

    # search without userid
    else:
        if usertype == 'member':
            cur.execute("SELECT a.userid, a.firstname, a.lastname FROM member a\
                INNER JOIN userlog b\
                ON a.userid = b.userid\
                WHERE a.firstname LIKE '{}' AND a.lastname LIKE '{}' \
                AND a.paymentplan LIKE '{}';".format(firstname, surname, paymentplan))
        else:
            if availabilitystarttime == '%':
                cur.execute("SELECT a.userid, a.firstname, a.lastname FROM trainer a\
                INNER JOIN userlog b\
                ON a.userid = b.userid\
                WHERE a.firstname  LIKE '{}' AND a.lastname  LIKE '{}';"
                .format(firstname, surname))

            else:
                cur.execute("SELECT a.userid, a.firstname, a.lastname FROM trainer a\
                    INNER JOIN userlog b\
                    ON a.userid = b.userid\
                    WHERE a.firstname  LIKE '{}' AND a.lastname  LIKE '{}' \
                    AND a.availabilitystarttime = CAST('{}' AS TIME);"
                    .format(firstname, surname, availabilitystarttime))

    users = cur.fetchall()
    db_cols = [item[0] for item in cur.description[2:]]
    return users, db_cols


def userDetails(user_id):
    if user_id is None:
        user_id = session['id']
    cur = getCursor()
    cur.execute("SELECT role FROM userlog WHERE userid={}".format(user_id))
    role = cur.fetchone()
    if role[0] == 'trainer':
        cur.execute("SELECT b.userid, b.firstname, b.lastname, b.email, b.dateofbirth, \
                    b.joineddate, b.availabilitystarttime, b.availabilityendtime, a.role\
                    FROM userlog a\
                    INNER JOIN trainer b\
                    ON a.userid = b.userid\
                    WHERE b.userid = {}".format(user_id))
    else:
        cur.execute("SELECT b.userid, b.firstname, b.lastname, b.email, b.dateofbirth, \
            b.joineddate, b.newslettersubscription, b.paymentplan, a.role\
            FROM userlog a\
            INNER JOIN member b\
            ON a.userid = b.userid\
            WHERE b.userid = {}".format(user_id))  
    user_details = cur.fetchone()
    db_cols = [item[0] for item in cur.description]
    return user_details, db_cols


@app.route("/")
def home():
    print('test')
    if 'loggedin' in session:
        return redirect('/profile') # NEEDS UPDATING - INVALID TEMPLATE
    return render_template('login.html')


@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        cursor = getCursor()
        cursor.execute('SELECT * FROM userlog\
            WHERE UserName=%s AND Password=%s', 
            (username, password))
        account = cursor.fetchone() #WILL NOT WORK IF THERE ARE DUPLICATE USERNAMES!
        if account:
            session['loggedin'] = True
            session['id'] = account[0]
            print (session['id'])
            session['username'] = account[1]
            session['role'] = account[3]
            trainer_group_classes = trainerGroupClasses()
            trainer_private_classes = trainerPrivateClasses()
            # Direct user to a landing page after logging in
            if session['role'] == 'member':
                return redirect('/profile')
            else:
                return redirect('/search?type=member')
        else:   
            msg = 'You have entered incorrect username/password!'
    return render_template('error.html', msg=msg)


@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('/login'))

# Tested - Display Trainer or Member Profile
@app.route("/profile", methods=["GET"])
def profile():
    if 'loggedin' in session:
        if request.method == 'GET':
            userid = request.args.get('userid')
            user_details = userDetails(userid)
            print('/profile', user_details)
            user_profile = user_details[0]
            print(user_profile)
            db_cols = user_details[1]
        return render_template('profile.html', user_details = user_profile, cols = db_cols, role=session['role'])
    else:
        return redirect('/login')


@app.route("/profile/update", methods=["POST", "GET"])
def updateProfile():
    if 'loggedin' in session:
        if request.method == "POST":
            firstname = request.form.get('firstname')
            surname = request.form.get('surname')
            dob = request.form.get('dob')
            email = request.form.get('email')
            joineddate = request.form.get('joineddate')
            newslettersubscription = request.form.get('newsletter')
            paymentplan = request.form.get('paymentplan')
            userid = request.form.get('userid')
            role = request.form.get('role')
            action = request.form.get('action')
            print(role)
            cur = getCursor()
            if action =='del':
                cur.execute("DELETE FROM userlog WHERE userid={}".format(userid))
                return redirect('/search')
            else:
                if role == 'member':
                    cur.execute("UPDATE member\
                        SET firstname=%s, lastname=%s, email=%s, dateofbirth=%s, joineddate=%s, newslettersubscription=%s, paymentplan=%s\
                            WHERE userid=%s", (firstname, surname, email, dob, joineddate, newslettersubscription, paymentplan, userid))
                    return redirect('/profile?userid={}'.format(userid))
                else:
                    cur.execute("UPDATE trainer\
                        SET firstname=%s, lastname=%s, email=%s, dateofbirth=%s, joineddate=%s, availabilitystarttime=%s, availabilityendtime=%s\
                            WHERE userid=%s", (firstname, surname, email, dob, joineddate, newslettersubscription, paymentplan, userid))#MUST BE REDONE
                    return redirect('/profile')
        else:
            userid = request.args.get('userid')
            trainer_info = userDetails(userid)
            return render_template('profile_update.html', user_details = trainer_info[0], cols = trainer_info[1], role = session['role'])
        
    else:
        return redirect('/login')    

@app.route("/profile/create", methods=["POST", "GET"])
def createProfile():
    if 'loggedin' in session:
        if request.method == "POST":
            username = request.form.get('username')
            cur = getCursor()
            # VALIDATION SCRIPT - NO DUPLICATE username allowed
            cur.execute("SELECT * FROM userlog WHERE username=%s", (username))
            existing_username = cur.fetchone()
            if len(existing_username) > 0:
                msg = 'The username you have entered already exists!'
                return render_template('error.html', msg=msg, role=session['role'])
            # Validation ends
            else:
                #Get values for userlog
                userid = genID()
                password = request.form.get('password')
                role = request.form.get('user_role')
                #Populate userlog
                cur.execute("INSERT INTO userlog VALUES ({},'{}',{},'{}');".format(userid, username, password, role))
                #Get values common to member and trainer tables
                email = request.form.get('email')
                joineddate = request.form.get('joineddate')
                firstname = request.form.get('firstname')
                surname = request.form.get('surname')
                dob = request.form.get('dob')

                #Add member profile
                if role == 'member':
                    #Member table specific data
                    newsletter = request.form.get('newsletter')
                    paymentplan = request.form.get('payment')
                    expirydate = request.form.get('expirydate')
                    cur.execute("INSERT INTO member(memberid, userid, firstname, lastname, email, dateofbirth, \
                        joineddate, newslettersubscription, membershipexpirydate, paymentplan) \
                            VALUES ({}, {}, '{}', '{}', '{}', '{}', '{}','{}', '{}', '{}');"
                        .format(userid, userid, firstname, surname, email, dob, joineddate, newsletter, expirydate, paymentplan))
                #Add trainer profile
                else:
                    starttime = request.form.get()
                    endtime = request.form.get()
                    cur.execute("INSERT INTO trainer(trainerid, userid, firstname, lastname, email, dateofbirth, \
                        joineddate, availabilitystarttime, availabilityendtime) \
                            VALUES ({}, {}, '{}', '{}', '{}', '{}', '{}','{}','{}')"
                        .format(userid, userid, firstname, surname, email, dob, joineddate, starttime, endtime))
                return redirect('/profile?userid={}'.format(userid)) # NEEDS TO BE MODIFIED TO DIRECT TO TRAINER PROFILE PAGE)
        else:
            profile_type = request.args.get('type')
            return render_template('profile_create.html', role=session['role'], profile_type=profile_type)
        
    else:
        return redirect('/login')  


@app.route("/search", methods=["POST", "GET"])
def search():
    if 'loggedin' in session:
        if request.method == "POST":
            first_name = request.form.get("firstname")
            surname = request.form.get("surname")
            userid = request.form.get("userid")
            group_class_id = request.form.get("groupclass")
            private_class_id = request.form.get("privateclass")
            user_type = request.form.get('usertype')

            if user_type == 'member':
                paymentplan = request.form.get('paymentplan')
                if len(private_class_id) > 0: #need to work on this part
                    users = userPrivateClass(private_class_id, user_type)
                elif len(group_class_id) > 0:
                    users = userGroupClass(first_name, surname, paymentplan, group_class_id, userid, user_type)
                else:
                    users = userList(first_name, surname, userid, paymentplan, None, user_type) # NEED to add username search

            else:
                availability = request.form.get('availability')
                print(availability)
                if len(private_class_id) > 0: #need to work on this part
                    users = userPrivateClass(private_class_id, user_type)
                elif len(group_class_id) > 0:
                    users = userGroupClass(first_name, surname, None, group_class_id, userid, user_type)
                else:
                    users = userList(first_name, surname, userid, None, availability, user_type) # NEED to add username search
            return render_template('/search_results.html', results=users[0], cols = users[1], role=session['role'])


        else:
            user_type = request.args.get('type')
            group_classes = trainerGroupClasses()
            private_classes = trainerPrivateClasses()
            availability = trainerAvailability()
            return render_template("search.html", role=session['role'], user_type=user_type,
            group_classes=group_classes, private_classes=private_classes, availability=availability)
    return render_template('login.html')

@app.route('/class', methods=['GET'])
def classTable():
    cur = getCursor()
    if request.method=='GET':
        class_type = request.args.get('type')
        classes = gymClass(class_type)
        return classes.classList(cur)
    

@app.route("/groupexercise/update", methods=["POST", "GET"])
def updateGroupExercise():
    if 'loggedin' in session:
        if request.method == "POST":
            groupsessionid = request.form.get('groupsessionid')
            trainerid = request.form.get('trainerid')
            groupsessionstartdate = request.form.get('groupsessionstartdate')
            cur = getCursor()
            print(groupsessionid,trainerid,groupsessionstartdate)
            # leave update function now, recheck this later
            # cur.execute("UPDATE groupsession SET trainerid=%s where groupsessionid=%s and groupsessionstartdate=%s",(str(trainerid),str(groupsessionid),groupsessionstartdate))
            return redirect("/class?type=group")
        else:
            groupexerciseid = request.args.get('groupexerciseid')
            trainerid = request.args.get('trainerid')
            if groupexerciseid == '' or trainerid == '':
                return redirect("/class?type=group")
            else:
                cur = getCursor()
                cur.execute("select a.groupexerciseid, c.trainerid, b.groupsessionid, \
                            a.groupclassname,c.firstname, c.lastname, \
                            a.groupclassstartdate,a.groupclassenddate, \
                            b.groupsessionstartdate,b.groupsessionstarttime,b.groupsessionendtime,b.location, a.description \
                            from\
                            groupexercise a, groupsession b, trainer c\
                            where a.groupexerciseid = b.groupexerciseid\
                            and b.trainerid = c.trainerid\
                            and a.groupexerciseid =%s and b.trainerid =%s \
                            order by a.groupclassname;",(str(groupexerciseid),str(trainerid)))
                select_result = cur.fetchall()
                cur.execute("select userid, concat(firstname, ' ', lastname) as name from trainer")
                trainer_result = cur.fetchall()
                return render_template('groupexercise_update.html',groupexercisedetails = select_result, trainer_result = trainer_result)
    else:
        return redirect('/login')

@app.route("/groupexercise/create", methods=["POST", "GET"])
def createGroupExercise():
    if 'loggedin' in session:
        if request.method == "POST":
            groupclassid = getGroupClassID()
            groupclassname = request.form.get('groupclassname')
            groupclassstartdate = request.form.get('groupclassstartdate')
            groupclasssenddate = request.form.get('groupclasssenddate')
            description = request.form.get('description')
            print(groupclassid,groupclassname,groupclassstartdate,groupclasssenddate,description)
            cur = getCursor()
            cur.execute("INSERT INTO GroupExercise (GroupExerciseID, GroupClassName, GroupClassStartDate, GroupClassEndDate, Description) VALUES (%s,%s,%s,%s,%s);",
            (str(groupclassid),groupclassname,groupclassstartdate,groupclasssenddate,description))
            return redirect("/class?type=group")
        else:
            return render_template('groupexercise_create.html')
    else:
        return redirect('/login')  


@app.route("/personaltraining", methods=["GET"])
def personalTraining():
    if 'loggedin' in session:
        if request.method == "GET":
            trainerid = request.args.get('trainerid')
            if trainerid == '':
                return redirect("/class?type=private")
            else:
                cur = getCursor()
                cur.execute("select a.MemberID, b.firstname, b.lastname, a.price, a. personalsessiondate, a.personalsessionstarttime, \
                a.personalsessionendtime, a.note \
                from personalsessionbooking a, member b \
                where a.TrainerID ={} and a.MemberID = b.MemberID;".format(trainerid))
                select_result = cur.fetchall()
                print(select_result)
                return render_template('personalsession_view.html',personalsessiondetails = select_result)
        else:
            return redirect("/class?type=private")
    else:
        return redirect('/login')

