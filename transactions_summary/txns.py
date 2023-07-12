from os import getenv
from jinja2 import Environment, FileSystemLoader
from psycopg.rows import dict_row
import email
import boto3
import csv
import psycopg
import calendar
import json


S3_BUCKET = getenv('BUCKET_NAME', None)
S3_PREFIX = getenv('BUCKET_PREFIX', None)


def render_template(data):
    env = Environment(loader=FileSystemLoader("templates/"))
    template = env.get_template("email.html")
    return template.render(**data)


def send_email(s3_client, template, account):
    response = s3_client.send_email(
        Source=getenv("EMAIL_SENDER", "llanes.ariel.enrique@gmail.com"), 
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
    s3_files = s3_client.list_objects_v2(
        Bucket=S3_BUCKET,
        Prefix=S3_PREFIX,
        StartAfter=S3_PREFIX
    )

    # Load data from files
    for s3_file in s3_files["Contents"]:
        load_file_txns(s3_file)

    # Send email with summary per user in files
    responses = []
    for acoount in get_active_accounts():
        summary = build_summary(acoount)
        acoount_email_response = send_email(s3_client, render_template(summary), acoount)
        responses.append(acoount_email_response)
    return {'status': 200, 'body': json.dumps(responses)}


def get_active_accounts():
    with ( 
        psycopg.connect(getenv("DATABASE_URL")) as conn,
        conn.cursor(row_factory=dict_row) as cur
    ):
        cur.execute("""
            SELECT
                account_id,
                email
            FROM accounts
            RIGHT JOIN transactions using (account_id)
            WHERE date_part('year', date) = date_part('year', CURRENT_DATE)
        """)
        return cur.fetchall()


def load_file_txns(file):
    with ( 
        psycopg.connect(getenv("DATABASE_URL")) as conn,
        conn.cursor(row_factory=dict_row) as cur,
        open(file) as csv_file
    ):
        for row in csv.DictReader(csv_file):
            cur.execute(
                "INSERT INTO transactions (transaction_id, account_id, date, value) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (
                    row.get('id'),
                    row.get('account_id'),
                    row.get('date'),
                    row.get('transaction')
                ),
            )


def build_summary(account):
    summary = {
        "transactions_per_month": {}
    }
    
    with ( 
        psycopg.connect(getenv("DATABASE_URL")) as conn,
        conn.cursor(row_factory=dict_row) as cur
    ):
        cur.execute(f"""
            SELECT
                SUM(value) as total_balance,
                AVG(value) filter (where value > 0) as average_credit,
                AVG(value) filter (where value < 0) as average_debit
            FROM transactions
            WHERE date_part('year', date) = date_part('year', CURRENT_DATE)
            AND transaction_id = {account.get("account_id")}
        """)
        summary.update(cur.fetchone())
    
        cur.execute(f"""
                SELECT 
                    date_part('month', date) as month,
                    COUNT(value) as monthly_sum
                FROM transactions
                WHERE date_part('year', date) = date_part('year', CURRENT_DATE)
                AND transaction_id = {account.get("account_id")}
                GROUP BY month
        """)
        for record in cur:
            summary["transactions_per_month"].update(
                {
                    "month": calendar.month_name[int(record.get("month"))],
                    "value": record.get("monthly_sum")
                }
            )
        return summary


if __name__ == "__main__":
    load_file_txns("/transactions_files/example.csv")
    for user in get_active_accounts():
        summary = build_summary(user)
        print(render_template(summary))
