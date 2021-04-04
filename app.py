import re
from types import MethodDescriptorType
from flask import Flask, render_template, request, redirect, url_for, session
import connect
import psycopg2
import uuid
import yagmail
import keyring
from datetime import date
from gymClass import gymClass
from trainer import trainer
from user import user
from booking import booking
from search import searchEngine
from payment import payment
from getGroupClassID import getGroupClassID
from finance import finance


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

def trainerAvailability():
    cur = getCursor()
    cur.execute('SELECT availabilitystarttime, availabilityendtime \
        FROM trainer WHERE leftdate IS NULL\
        GROUP BY availabilitystarttime, availabilityendtime;'
                )
    availability = cur.fetchall()
    return availability    


@app.route("/")
def home():
    print('test')
    if 'loggedin' in session:
        if session['role'] == 'member':
            return redirect('/profile')
        else:
            return redirect('/search?type=member')
    return render_template('home.html')


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
            session['username'] = account[1]
            session['role'] = account[3]
            # Direct user to a landing page after logging in
            if session['role'] == 'member':
                check_account = payment(memberid=session['id'], cur=cursor, role=session['role'])
                get_account_status = check_account.accountStatus()
                is_overdue = get_account_status[6]
                if is_overdue == 'Y':
                    return check_account.displayAccount()
                else:
                    return redirect('/profile')
            else:
                return redirect('/search?type=member')
        else:   
            msg = 'You have entered incorrect username/password!'
            return render_template('error.html', msg=msg)
    else:
        return redirect('/')
    


@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    session.pop('role', None)
    return redirect('/login')

# Tested - Display Trainer or Member Profile
@app.route("/profile", methods=["GET"])
def profile():
    if 'loggedin' in session:
        if request.method == 'GET':
            userid = request.args.get('userid')
            #role =request.form.get('role')
            if userid is None:
                userid = session['id']
        cur = getCursor()
        get_user = user(userid=userid, cur=cur)
        return get_user.generateProfile()
    else:
        return redirect('/login')


@app.route("/profile/update", methods=["POST", "GET"])
def updateProfile():
    if 'loggedin' in session:
        cur=getCursor()
        if request.method == "POST":
            userid = request.form.get('userid')
            #role = request.form.get('role')
            update_profile = user(userid, cur)
            return update_profile.updateProfile()
        else:
            userid = request.args.get('userid')
            usertype = request.args.get('usertype')
            get_profile = user(userid, cur)
            user_profile = get_profile.userDetails()
            return render_template('profile_update.html', user_details = user_profile[0], cols = user_profile[1], user_type=usertype, role = session['role'])
        
    else:
        return redirect('/login')    

@app.route("/profile/create", methods=["POST", "GET"])
def createProfile():
    if 'loggedin' in session:
        if request.method == "POST":
            username = request.form.get('username')
            cur = getCursor()
            # VALIDATION SCRIPT - NO DUPLICATE username allowed
            cur.execute(f"SELECT * FROM userlog WHERE username='{username}';")
            existing_username = cur.fetchone()
            if existing_username is not None:
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
                    paymentid = genID()
                    newsletter = request.form.get('newsletter')
                    paymentplan = request.form.get('payment')
                    #expirydate = request.form.get('expirydate')
                    cur.execute(f"SELECT cost FROM price WHERE paymentplan='{paymentplan}'")#Get the cost of plan for creating invoice
                    price = cur.fetchone()
                    cur.execute(f"INSERT INTO member(memberid, userid, firstname, lastname, email, dateofbirth, \
                            joineddate, newslettersubscription, membershipexpirydate, paymentplan) \
                            VALUES ({userid}, {userid}, '{firstname}', '{surname}', '{email}', '{dob}', '{joineddate}','{newsletter}', '{joineddate}', '{paymentplan}');\
                            INSERT INTO payment(paymentid, memberid, paymentstatus, paidprice, paymentduedate, paymentplan)\
                            VALUES ({paymentid}, {userid}, 'Not Paid', {price[0]}, '{joineddate}', '{paymentplan}')" # Create an invoice for membership payment
                    )
                #Add trainer profile
                else:
                    starttime = request.form.get('starttime')
                    endtime = request.form.get('endtime')
                    cur.execute(f"INSERT INTO trainer(trainerid, userid, firstname, lastname, email, dateofbirth, \
                        joineddate, availabilitystarttime, availabilityendtime) \
                            VALUES ({userid}, {userid}, '{firstname}', '{surname}', '{email}', '{dob}', '{joineddate}','{starttime}','{endtime}')"
                    )
                return redirect('/profile?userid={}'.format(userid)) # NEEDS TO BE MODIFIED TO DIRECT TO TRAINER PROFILE PAGE)
        else:
            profile_type = request.args.get('type')
            return render_template('profile_create.html', role=session['role'], profile_type=profile_type)
        
    else:
        return redirect('/login')  

@app.route('/profile/deactivate', methods=['GET'])
def deactivateProfile():
    if 'loggedin' in session:
        if request.method == 'GET':
            if session['role'] == 'manager':
                cur = getCursor()
                userid = request.args.get('userid')
                user_type = request.args.get('usertype')
                deactivate = user(userid, cur )
                return deactivate.deactivateUser()
            else:
                msg = 'Only the manager can deactivate users'
                return render_template('error.html', msg = msg, role=session['role'])

        else:
            msg = 'Invalid URL'
            return render_template('error.html', msg = msg, role=session['role'])
    else:
        return redirect('/login')  

# Search a member or trainer. Available to manager and trainers
@app.route("/search", methods=["POST", "GET"])
def search():
    if 'loggedin' in session:
        cur = getCursor()
        if request.method == "POST":
            values = {
                'first_name': request.form.get("firstname"),
                'surname': request.form.get("surname"),
                'userid': request.form.get("userid"),
                'group_class_id': request.form.get("groupclass"),
                'private_class_id': request.form.get("privateclass"),
                'user_type': request.form.get('usertype'),
                'paymentplan': request.form.get('paymentplan'),
                'availability': request.form.get('availability')
            }
            for key in values:
                if values[key] == '':
                    values[key] = '%'

            search_engine = searchEngine(user_id=session['id'], role=session['role'], user_type=values['user_type'], cur=cur)

            if values['user_type'] == 'member':
                #paymentplan = request.form.get('paymentplan')
                if values['private_class_id'] != '%': #need to work on this part
                    print('duh')
                    users = search_engine.userPrivateClass(values['private_class_id'], values['user_type'])
                elif values['group_class_id'] != '%':
                    print('doo')
                    users = search_engine.userGroupClass(values['first_name'], values['surname'], values['paymentplan'], values['group_class_id'], values['userid'], values['user_type'])
                else:
                    users = search_engine.userList(values['first_name'], values['surname'], values['userid'], values['paymentplan'], None, values['user_type']) # NEED to add username search

            else:
                #availability = request.form.get('availability')
                if values['private_class_id'] != '%': #need to work on this part
                    users = search_engine.userPrivateClass(values['private_class_id'], values['user_type'])
                elif values['group_class_id'] != '%':
                    print('testla')
                    users = search_engine.userGroupClass(values['first_name'], values['surname'], None, values['group_class_id'], values['userid'], values['user_type'])
                else:
                    users = search_engine.userList(values['first_name'], values['surname'], values['userid'], None, values['availability'], values['user_type']) # NEED to add username search
            if len(users[0]) == 0:
                msg = 'Could not find any users. Try again!'
                return render_template('error.html', msg=msg, role=session['role'])
            else:
                return render_template('/search_results.html', results=users[0], user_type=values['user_type'], cols = users[1], role=session['role'])


        else:
            user_type = request.args.get('type')
            search_engine = searchEngine(user_id=session['id'], role=session['role'], user_type=user_type, cur=cur)
            group_classes = search_engine.trainerGroupClasses()
            private_classes = search_engine.trainerPrivateClasses()
            availability = trainerAvailability()
            return render_template("search.html", role=session['role'], user_type=user_type,
            group_classes=group_classes, private_classes=private_classes, availability=availability)
    return render_template('login.html')

# Public view of classes offered by the gym
@app.route('/class', methods=['GET'])
def classTable():
    cur = getCursor()
    if request.method=='GET':
        if 'loggedin' in session:
            role = session['role']
        else:
            role = ''
        class_type = request.args.get('type')
        classes = gymClass(class_type=class_type, cur=cur)
        results = classes.classList()
        return render_template('class.html', classes=results[0], cols=results[1], classtype=class_type, role=role) # for logged in users add role=session['role']


@app.route("/groupexercise", methods=["POST", "GET"])
def GroupExercise():
    if 'loggedin' in session:
        if request.method == "GET":
            groupexerciseid = request.args.get('groupexerciseid')
            trainerid = request.args.get('trainerid')
            if groupexerciseid == '' or trainerid == '':
                return redirect("/class?type=group")
            else:
                cur = getCursor()
                get_class = gymClass('group', cur=cur, groupexerciseid=groupexerciseid, trainerid=trainerid)
                return get_class.groupClassByTrainer()
        else:
            return redirect("/class?type=group")
    else:
        return redirect('/login')

@app.route("/groupexercise/update", methods=["POST", "GET"])
def UpdateGroupExercise():
    if 'loggedin' in session:
        if request.method == "POST":
            groupsessionid = request.form.get('groupsessionid')
            trainerid = request.form.get('trainerid')
            cur = getCursor()
            get_class = gymClass('group', cur=cur, groupsessionid=groupsessionid, trainerid=trainerid)
            return get_class.updateGroupClass()
        else:
            groupsessionid = request.args.get('groupsessionid')
            trainerid = request.args.get('trainerid')
            if groupsessionid == '' or trainerid == '':
                return redirect("/class?type=group")
            else:
                cur = getCursor()
                get_class = gymClass('group', cur=cur, groupsessionid=groupsessionid, trainerid= trainerid)
                return get_class.getGroupClass()
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
            cur = getCursor()
            get_class = gymClass('group', cur=cur, groupsessionid=groupsessionid)
            return get_class.createGroupClass(groupclassname,groupclassstartdate,groupclasssenddate,description)
        else:
            return render_template('groupexercise_create.html')
    else:
        return redirect('/login')

#@app.route('/groupexercise/session', methods=['GET', 'POST'])
#def addSession():


@app.route('/profile/all', methods=['GET'])
def allTrainers():
    if 'loggedin' in session:
        if request.method == 'GET':
            cur = getCursor()
            user_type = request.args.get('usertype')
            #get_trainers = user(session['id'], session['role'], cur)
            get_trainers = user(userid=session['id'], cur=cur)
            if session['role'] == 'manager':
                if user_type == 'trainer':
                    #results = get_trainers.TrainerGroupSummary()
                    cur.execute("SELECT userid, firstname, lastname FROM trainer WHERE leftdate IS NULL")
                    results = cur.fetchall()
                    cols = [item[0] for item in cur.description]
                elif user_type == 'member':
                    cur.execute("SELECT userid, firstname, lastname FROM member WHERE leftdate IS NULL")
                    results = cur.fetchall()
                    cols = [item[0] for item in cur.description]
            elif session['role'] == 'trainer':
                get_members = searchEngine(user_id=session['id'], role=session['role'], user_type=user_type, cur=cur)
                list_members = get_members.memberByTrainer()
                results = list_members[0]
                cols = list_members[1]
            return render_template('search_results.html', results=results, cols=cols, role=session['role'], user_type=user_type)
        else:
            msg = 'Invalid URL'
            return render_template('error.html', msg = msg)
    else:
        return render_template('login.html')



@app.route('/trainer/groupclass', methods=['GET', 'POST'])
def DisplayGroupClass():
    if 'loggedin' in session:
        cur = getCursor()
        get_groupclass = trainer(userid=session['id'], cur=cur)
        results = get_groupclass.trainerGroupClass()
        return render_template ('class.html', role=session['role'], classes=results[0], cols=results[1])
    else:
        return render_template('login.html')

@app.route('/trainer/groupclass/session', methods=['GET', 'POST'])
def DisplayGroupSession():
    if 'loggedin' in session:
        if request.method == 'GET':
            cur = getCursor()
            classid = request.args.get('classid')
            get_groupsession = trainer(userid=session['id'], cur=cur)
            return get_groupsession.trainerGroupSession(classid)
    else:
        return render_template('login.html')
#@app.route('/trainer/groupclass/details', methods=['GET'])
#def DisplayGroupClass():
#    if 'loggedin' in session:
#        if request.method == 'GET':
#            class_id = request.args.get(classid)
#            cur = getCursor()
#            #CREATE a method in trainer.py
#            #Pass the method into here
#            #Create/modify a html template to display the data
#            #Add a return statement here
#            return render_template('/', role=session['role'], class_details=results[0], cols=result[1])
#    else:
#        return render_template('login.html')

# Search availability of personal training
@app.route('/member/private', methods = ['GET', 'POST'])
def privateTrainerSearch():
    if 'loggedin' in session:
        if session['role'] == 'member':
            cur = getCursor()
            cur.execute("SELECt availabilitystarttime, availabilityendtime \
                        FROM trainer WHERE leftdate IS NULL\
                        GROUP By availabilitystarttime, availabilityendtime")
            time_slots = cur.fetchall()
            if request.method == 'POST':
                booking_date = request.form.get('date')
                booking_time = request.form.get('time')
                get_trainers = searchEngine(session['id'], session['role'], session['role'], cur)
                results = get_trainers.privateAvailability(booking_date, booking_time)
                return render_template('private_booking.html', time_slots=time_slots, role=session['role'], results = results[0], date=booking_date, time=booking_time)
            else:
                return render_template('private_booking.html', time_slots=time_slots, results='', role=session['role'])
        else:
            msg = 'Only members can book a private training session'
            return render_template('error.html', msg = msg, role=session['role'])

    else:
        return render_template('login.html')

# Personal training booking & payment
@app.route('/member/private/booking', methods=['GET', 'POST'])
def privateBooking():
    if 'loggedin' in session:
        # Display booking details for member to confirm
        if session['role'] == 'member':
            if request.method == 'GET':
                time = request.args.get('starttime')
                date = request.args.get('date')
                trainerid = request.args.get('trainerid')
                memberid = session['id']
                cur = getCursor()
                booking_private = booking(memberid=memberid, trainerid=trainerid, time=time, date=date, cur=cur)
                return booking_private.privateBookingConfirm()
            else:
                # Update DB following confirmation
                sessionid = genID()
                paymentid = genID()
                trainerid = request.form.get('trainerid')
                memberid = request.form.get('memberid')
                date = request.form.get('date')
                time = request.form.get('time')
                price = request.form.get('price')
                notes = request.form.get('notes')
                cur = getCursor()
                confirm_booking = booking(memberid=memberid, trainerid=trainerid, sessionid=sessionid, time=time, date=date, cur=cur)
                return confirm_booking.addPrivateBooking(price, paymentid, notes)

        else:
            msg = 'Only members can book a private training session'
            return render_template('error.html', msg = msg, role=session['role'])

    else:
        return render_template('login.html')


@app.route('/member/group', methods = ['GET', 'POST'])
def GroupBookingSearch():
    if 'loggedin' in session:
        if session['role'] == 'member':
            cur = getCursor()
            cur.execute("select groupexerciseid, groupclassname from groupexercise")
            select_result = cur.fetchall()
            if request.method == 'GET':  
                return render_template('group_booking.html', select_result = select_result,role=session['role'])
            else:
                groupexerciseid = request.form.get('groupexerciseid')
                memberid = session['id']
                cur = getCursor()
                get_sessions = booking(memberid=memberid, cur=cur)
                return get_sessions.groupBookingOption(groupexerciseid=groupexerciseid, allgroupclasses = select_result)
        else:
            msg = 'Only members can book a group training session'
            return render_template('error.html', msg = msg)

    else:
        return render_template('login.html')


@app.route('/member/group/booking', methods=['GET', 'POST'])
def GroupBooking():
    if 'loggedin' in session:
        if session['role'] == 'member':
            if request.method == 'GET':
                groupsessionid = request.args.get('groupsessionid')
                date = request.args.get('startdate')
                starttime = request.args.get('starttime')
                endtime = request.args.get('endtime')
                memberid = session['id']
                classname = request.args.get('classname')
                firstname = request.args.get('firstname')
                lastname = request.args.get('lastname')
                cur = getCursor()
                booking_group = booking(groupsessionid=groupsessionid, date=date, starttime=starttime, endtime=endtime, memberid=memberid, cur=cur, 
                classname=classname,firstname=firstname,lastname=lastname)
                return booking_group.groupBookingConfirm()
            else:
                groupsessionbookingid = genID()
                groupsessionid = request.form.get('groupsessionid')
                memberid = request.form.get('memberid')
                date = request.form.get('date')
                time = request.form.get('time')
                note = request.form.get('note')
                cur = getCursor()
                confirm_group_booking = booking(memberid=memberid, groupsessionbookingid=groupsessionbookingid, groupsessionid=groupsessionid, time=time, date=date, cur=cur)
                return confirm_group_booking.addGroupBooking(note)

        else:
            msg = 'Only members can book a group training session'
            return render_template('error.html', msg = msg)

    else:
        return render_template('login.html')


# Process subscription payments. Available to manager and members. 
# #Excludes Private training payments
@app.route('/member/pay', methods=['GET', 'POST'])
def paySubscription():
    if 'loggedin' in session:
        cur = getCursor()
        # Display payment status & payment options
        if request.method == 'GET':
            if session['role'] == 'manager':
                memberid = request.args.get('memberid')
            elif session['role'] == 'member':
                memberid = session['id']
            display_payment = payment(memberid=memberid, cur=cur, role=session['role'])
            return display_payment.displayAccount()
        else:
            # Updates db
            paymentid = request.form.get('paymentid')
            paid_price = float(request.form.get('paymentprice'))
            duedate = request.form.get('duedate')
            memberid = request.form.get('memberid')
            plan = request.form.get('plan')
            print(plan)
            unit_price = float(request.form.get('price'))
            unit = int(request.form.get('unit'))
            overdue = request.form.get('overdue')
            new_paymentid = genID()
            make_payment = payment(paymentid=paymentid, memberid=memberid, overdue=overdue, 
            paidprice=paid_price, paymentduedate=duedate, paymentplan=plan, cur=cur)
        return make_payment.makePayment(new_id=new_paymentid, unit_price=unit_price, unit=unit)
    else:
        return render_template('login.html')

@app.route('/member/attendance', methods=['GET', 'POST'])
def attendance():
    if 'loggedin' in session:
        cur = getCursor()
        if request.method == 'POST':
            memberid = request.form.get('memberid')
            sessionid = request.form.get('sessionid')
            status = request.form.get('status')
            if session['role'] == 'member':
                get_attendance = booking(memberid = memberid, cur = cur)
                return get_attendance.memberAttendanceUpdate(sessionid = sessionid, status=status, role = session['role'])

            else:
                groupsession = request.form.get('groupsession')
                get_attendance = booking(trainerid=session['id'], cur = cur)
                return get_attendance.memberAttendanceUpdate(groupsession=groupsession, sessionid = sessionid, status=status, role = session['role'])

        else:
            if session['role'] == 'member':
                get_attendance = booking(memberid = session['id'], cur = cur)
                return get_attendance.memberAttendanceList()
            elif session['role'] == 'trainer': #display session table
                sessionid = request.args.get('sessionid')
                get_attendance = booking(trainerid = session['id'], cur = cur)
                return get_attendance.trainerAttendanceList(sessionid)
              
    else:
        return render_template('login.html')

@app.route('/finance', methods=['GET', 'POST'])
def financeReport():
    if 'loggedin' in session:
        if request.method == 'POST':
            if session['role'] == 'manager':
                startdate = request.form.get('startdate')
                enddate = request.form.get('enddate')
                print(startdate, enddate)
                report = request.form.get('report')
                cur = getCursor()
                produce_report = finance(startdate = startdate, enddate = enddate, report = report, cur = cur)
                return produce_report.reportTool()
            else:
                msg = 'You do not have permission to view this page'
                return render_template('error.html', msg = msg)
        else:
            return render_template('finance.html', role = session['role'])
    else:
        return render_template('login.html')


#@app.route("/personaltraining", methods=["GET"])
#def personalTraining():
#    if 'loggedin' in session:
#        if request.method == "GET":
#            trainerid = request.args.get('trainerid')
#            if trainerid == '':
#                return redirect("/class?type=private")
#            else:
#                cur = getCursor()
#                cur.execute("select a.MemberID, b.firstname, b.lastname, a.price, a. personalsessiondate, a.personalsessionstarttime, \
#                a.personalsessionendtime, a.note \
#                from personalsessionbooking a, member b \
#                where a.TrainerID ={} and a.MemberID = b.MemberID;".format(trainerid))
#                select_result = cur.fetchall()
#                print(select_result)
#                return render_template('personalsession_view.html',personalsessiondetails = select_result, role = session['role'])
#        else:
#            return redirect("/class?type=private")
#    else:
#        return redirect('/login')

#MSUT INSTALL THE FOLLOWING MODULES
#!!!!!!   pip install yagmail
#!!!!!!   pip install keyring

@app.route("/newsletter", methods=["POST", "GET"])
def SendingNewsletter():
    if 'loggedin' in session:
        if request.method == "POST":
            cur = getCursor()
            cur.execute("select email from member where newslettersubscription = true")
            select_result_emails = cur.fetchall()
            email_list=[]
            for i in select_result_emails:
                str =  ''.join(i)
                email_list.append(str)
            content = request.form.get('content')
            subject = request.form.get('subject')
            yagmail.register('comp639group5@gmail.com','lincolnuni2021')
            yag = yagmail.SMTP('comp639group5@gmail.com')
            yag.send(to = email_list, subject= subject, contents= content)
            msg = 'Newsletter sent successfully!'
            return render_template('error.html', msg=msg, role = session['role'])
        else:
            cur = getCursor()
            cur.execute("select count(*) from member where newslettersubscription = true")
            select_result = cur.fetchall()
            return render_template('newsletter.html',select_result=select_result, role = session['role'])
    else:
        return redirect('/login')

@app.route("/profile/reminder", methods=["POST","GET"])
def MembershipReminder():
    if 'loggedin' in session:
        if request.method == "POST":
            if 'loggedin' in session:
                duedate = request.form.get('date')
                today = date.today()
                print(today,duedate)
                cur = getCursor()
                cur.execute("select * from member where membershipexpirydate between %s and %s;",(today,duedate))
                result = cur.fetchall()
                print(result)
                if result == []:
                    msg = 'Sorry, no records shows that membership is due by the end of {}'.format(duedate)
                    return render_template('error.html',msg=msg)
                else:
                    return render_template('membership_reminder_list.html', result=result, duedate=duedate, role=session['role'])
        else:
            return render_template('membership_reminder.html', role=session['role'])
    else:
        return  redirect('/login')

# Send a reminder by email to all members with overdue payment within a given period
@app.route("/profile/reminder/list", methods=["POST", "GET"])
def MembershipReminderList():
    if 'loggedin' in session:
        if request.method == "POST":
            content = 'Dear, \
                \
                    Your Lincoln membership is expiring soon, and we sincerely hope that you will join us for another outstanding year of great programs and professional development.\
                    Good news! There’s still time to renew, and it’s as easy as ever with these options: \
                        \
                    1. Make the online payment from your profile page. \
                    2. Make the payment at GYM recepution. \
                        \
                    More good news! This year we have an extra incentive for you to renew your membership. If your renewal payment are received before expiry date, you will be entered into a drawing for a free Lincoln GYM bag! \
                    Please let us know if you have questions or concerns. \
                        \
                    Sincerely,\
                    Pat \
                    Lincoln GYM'
            subject = 'Membership renewal reminder - Lincoln GYM'
            duedate = request.form.get('duedate')
            today = date.today()
            cur = getCursor()
            # Can look up all overdue memberships between now and a future date
            cur.execute("select email from member where membershipexpirydate between %s and %s;",(today,duedate))
            result = cur.fetchall()
            email_list=[]
            for i in result:
                str =  ''.join(i)
                email_list.append(str)
            print(duedate,email_list)
            # yagmail.register('comp639group5@gmail.com','lincolnuni2021')
            # yag = yagmail.SMTP('comp639group5@gmail.com')
            # yag.send(to = email_list, subject= subject, contents= content)
            msg = 'Membership renewal reminder sent successfully!'
            return render_template('error.html', msg=msg,role=session['role'])
        else:
            return render_template('membership_reminder_list.html',role=session['role'])
    else:
        return redirect('/login')
