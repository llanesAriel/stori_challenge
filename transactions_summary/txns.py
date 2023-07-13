from os import getenv
from jinja2 import Environment, FileSystemLoader
from psycopg2.extras import NamedTupleCursor
import codecs
import boto3
import csv
import psycopg2
import calendar
import json


# rds settings
DB_HOST = getenv('RDS_HOST', "db")
DB_USERNAME = getenv('RDS_USER', "stori")
DB_PASSWORD = getenv('RDS_PASSWORD', "storichallenge")
DB_NAME = getenv('RDS_DB', "stori")


def render_template(data):
    env = Environment(loader=FileSystemLoader("templates/"))
    template = env.get_template("email.html")
    return template.render(**data)


def send_local_email(template):
    import smtplib
    from email.mime.text import MIMEText
    
    from_email = getenv("FROM_EMAIL")
    to_email = getenv("TO_EMAIL")

    if from_email:
        msg = MIMEText(template, 'html')
        msg['Subject'] = "test"
        msg['From'] = from_email
        msg['To'] = to_email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
            smtp_server.login(from_email, "ckdbfjsbgblfjgss")
            smtp_server.sendmail(from_email, to_email or from_email, msg.as_string())
        print("Message sent!")
    else:
        print("Configure the FROM_EMAIL email address on docker-compose.yml")


def send_email(s3_client, template, account):
    response = s3_client.send_email(
        Source=getenv("EMAIL_SENDER", None), 
        Destination={'ToAddresses':[account.get("email")]}, 
        Message={
            'Subject': {
                'Data': "Daily Account Balance - Transaction Summary"
            }, 
            'Html':{
                'Text':{
                    'Data': template 
                }
            }
        }
    )
    return response


def lambda_handler(event, context):
    s3_client = boto3.client("s3")
    csv_file = s3_client.get_object(Bucket=getenv("BUCKET"), Key="txns.csv")

    # Load data from file
    load_file_txns(codecs.getreader('utf-8')(csv_file[u'Body']))

    # Send email with summary per user in files
    responses = []
    for acoount in get_active_accounts():
        summary = build_summary(acoount)
        acoount_email_response = send_email(s3_client, render_template(summary), acoount)
        responses.append(acoount_email_response)
    return {'status': 200, 'body': json.dumps(responses)}


def get_active_accounts():

    conn = psycopg2.connect(
        database = DB_NAME,
        user = DB_USERNAME,
        password = DB_PASSWORD,
        host = DB_HOST,
    )
    cur = conn.cursor(cursor_factory=NamedTupleCursor)
    cur.execute("""
        SELECT
            DISTINCT account_id,
            email
        FROM accounts
        RIGHT JOIN transactions using (account_id)
        WHERE date_part('year', date) = date_part('year', CURRENT_DATE)
    """)
    users = cur.fetchall()
    cur.close()
    conn.close()
    return users


def load_file_txns(csv_file):

    conn = psycopg2.connect(
        database = DB_NAME,
        user = DB_USERNAME,
        password = DB_PASSWORD,
        host = DB_HOST,
    )
    for row in csv.DictReader(csv_file):
        cur = conn.cursor(cursor_factory=NamedTupleCursor)
        cur.execute(
            "INSERT INTO transactions (transaction_id, account_id, date, value) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (
                row.get('id'),
                row.get('account_id'),
                row.get('date'),
                row.get('transaction')
            ),
        )
        conn.commit()
        cur.close()
    conn.close()


def build_summary(account):

    summary = {
        "transactions_per_month": []
    }
    
    conn = psycopg2.connect(
        database = DB_NAME,
        user = DB_USERNAME,
        password = DB_PASSWORD,
        host = DB_HOST,
    )
    cur = conn.cursor(cursor_factory=NamedTupleCursor)
    cur.execute(f"""
        SELECT
            SUM(value) as total_balance,
            AVG(value) filter (where value > 0) as average_credit,
            AVG(value) filter (where value < 0) as average_debit
        FROM transactions
        WHERE date_part('year', date) = date_part('year', CURRENT_DATE)
        AND account_id = {account.account_id}
    """)
    balances = cur.fetchone()
    summary.update({
        "total_balance": balances.total_balance,
        "average_credit": balances.average_credit,
        "average_debit": balances.average_debit
    })

    cur.execute(f"""
            SELECT 
                date_part('month', date) as month,
                COUNT(value) as monthly_sum
            FROM transactions
            WHERE date_part('year', date) = date_part('year', CURRENT_DATE)
            AND account_id = {account.account_id}
            GROUP BY month
    """)
    for record in cur.fetchall():
        summary["transactions_per_month"].append(
            {
                "month": calendar.month_name[int(record.month)],
                "value": record.monthly_sum
            }
        )
    cur.close()
    conn.close()
    return summary


if __name__ == "__main__":
    load_file_txns(open("/transactions_files/example.csv"))
    for user in get_active_accounts():
        summary = build_summary(user)
        send_local_email(render_template(summary))
