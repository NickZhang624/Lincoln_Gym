import re
from types import MethodDescriptorType
from flask import Flask, render_template, request, redirect, url_for, session
import connect
import psycopg2
import uuid
from datetime import date

class payment:
    def __init__(self, paymentid='', memberid='', paymentstatus='', overdue='', unit='', paidprice='', paymentduedate='', paymentdate='', paymentplan='', cur='', role=''):
        self.paymentid = paymentid
        self.memberid = memberid
        self.paymentstatus = paymentstatus
        self.paidprice = paidprice
        self.paymentduedate = paymentduedate
        self.paymentdate = paymentdate
        self.paymentplan = paymentplan
        self.overdue = overdue
        self.unit = unit
        self.cur = cur
        self.role = role

# Display account status based on the lastest invoice status
    def accountStatus(self):
        self.cur.execute(f"SELECT * FROM\
                    (SELECT p.paymentid, p.paymentstatus, p.paidprice, p.paymentduedate, m.paymentplan,\
                    ROW_NUMBER () OVER (PARTITION BY p.memberid ORDER BY p.paymentdate DESC) AS RN,\
                    CASE WHEN p.paymentduedate <= DATE(NOW()) THEN 'Y'\
                    ELSE 'N' END AS overdue\
                    FROM payment p\
                    LEFT JOIN member m\
                    ON m.memberid = p.memberid\
                    WHERE p.memberid = {self.memberid} AND (m.paymentplan != 'Hourly') ) AS a\
                    WHERE RN = 1")
        result = self.cur.fetchone()
        return result

        
    def displayAccount(self):
        result = self.accountStatus()
        paymentid = result[0]
        status = result[1]
        price = result[2]
        duedate = result[3]
        plan = result[4]
        overdue = result[6]    
        return render_template('pay_subscription.html', memberid=self.memberid, paymentid=paymentid, status=status, price=price,
        duedate=duedate, overdue=overdue, plan=plan, role=self.role)
    
    def makePayment(self, new_id, unit_price, unit):
        days = {'Weekly':7, 'Monthly':30, 'Yearly':365}
        print(self.paymentplan)
        add_days = days[self.paymentplan] * unit # num of days to extend the membership by
        if self.overdue == 'N':
            self.cur.execute(f"SELECT membershipexpirydate FROM member WHERE memberid={self.memberid}")
            member_expiry = self.cur.fetchone()
            self.cur.execute(f"UPDATE member SET membershipexpirydate = CAST('{member_expiry[0]}' AS DATE)+ INTERVAl '{add_days} days' \
                    WHERE memberid={self.memberid};\
                    UPDATE payment SET paymentstatus='Paid', paidprice={self.paidprice},  paymentdate=DATE(NOW())\
                    WHERE paymentid={self.paymentid};\
                    INSERT INTO payment VALUES({new_id}, {self.memberid},'Not Paid', {unit_price}, \
                    CAST('{member_expiry[0]}' AS DATE) + INTERVAl '{add_days} days', null, '{self.paymentplan}')")
        elif self.overdue == 'Y':
            self.cur.execute(f"UPDATE payment SET paymentstatus='Paid', paidprice={self.paidprice},  paymentdate=DATE(NOW())\
                    WHERE paymentid={self.paymentid};\
                    INSERT INTO payment VALUES({new_id}, {self.memberid},'Not Paid', {unit_price}, \
                    DATE(NOW()) + INTERVAl '{add_days} days', null, '{self.paymentplan}');\
                    UPDATE member SET membershipexpirydate = DATE(NOW()) + INTERVAl '{add_days} days' WHERE memberid = {self.memberid};")
        self.cur.execute(f"SELECT membershipexpirydate FROM member WHERE memberid={self.memberid}")
        new_expiry_date = self.cur.fetchone()
        msg = f"Payment Successful. Your membership has been extended to {new_expiry_date[0]}"
        return render_template('error.html', msg = msg, purpose='success')
    
    def overduePayment(self):
        self.cur.execute("SELECT b.memberid, b.firstname, b.lastname, b.membershipexpirydate, a.paymentduedate, a.paidprice,\
                        CASE WHEN a.paymentplan IN ('Weekly', 'Monthly', 'Yearly') THEN 'Memberhsip'\
                        ELSE 'Private Training'\
                        END AS category\
                        FROM payment a\
                        INNER JOIN member b\
                        ON a.memberid = b.memberid\
                        WHERE a.paymentstatus = 'Not Paid' AND a.paymentduedate <= DATE(NOW())")
        results = self.cur.fetchall()
            
        return results