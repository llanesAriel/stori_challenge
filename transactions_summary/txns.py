from os import getenv
from jinja2 import Environment, FileSystemLoader
from psycopg.rows import dict_row
import csv
import psycopg
import calendar


CSV_DIR = "/transactions_files"

env = Environment(
    loader=FileSystemLoader("templates/")
)


def render_template(data):
    template = env.get_template("email.html")
    return template.render(**data)


def send_email(template):
    pass


def main():

    summary = {
        "transactions_per_month": {}
    }

    with ( 
        psycopg.connect(getenv("DATABASE_URL")) as conn,
        conn.cursor(row_factory=dict_row) as cur,
        open(CSV_DIR + "/example.csv") as csv_file
    ):
        for row in csv.DictReader(csv_file):
            cur.execute(
                "INSERT INTO transactions (id, date, value) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                (row.get('id'), row.get('date'), row.get('transaction')),
            )

        cur.execute("""
            SELECT
            SUM(value) as total_balance,
            AVG(value) filter (where value > 0) as average_credit,
            AVG(value) filter (where value < 0) as average_debit
            from transactions
            WHERE date_part('year', date) = date_part('year', CURRENT_DATE)
        """)
        summary.update(cur.fetchone())

        cur.execute("""
            SELECT 
                date_part('month', date) as month,
                COUNT(value) as monthly_sum
            FROM transactions
            WHERE date_part('year', date) = date_part('year', CURRENT_DATE)
            GROUP BY month
        """)
        for record in cur:
            summary["transactions_per_month"].update(
                {
                    "month": calendar.month_name[int(record.get("month"))],
                    "value": record.get("monthly_sum")
                }
            )

    print(summary)
    html = render_template(summary)
    print(html)


if __name__ == "__main__":
    main()
