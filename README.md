
# Stori Challenge

For this challenge you must create a system that processes a file from a mounted directory. The file
will contain a list of debit and credit transactions on an account. Your function should process the file
and send summary information to a user in the form of an email.

An example file is shown below; but create your own file for the challenge. Credit transactions are
indicated with a plus sign like +60.5. Debit transactions are indicated by a minus sign like -20.46


![image](https://github.com/llanesAriel/stori_challenge/assets/91704220/811ceeb6-5e53-489a-829a-4528c7dd437c)


#### Bonus points
1. Save transaction and account info to a database
2. Style the email and include Stori’s logo
3. Package and run code on a cloud platform like AWS. Use AWS Lambda and S3 in lieu of Docker.


# Proyect

Running this module locally will send an email to the configured email with the details of this year's transactions according to the .csv file.
The csv file can be edited to add more transactions

## Requirements:

### Local requirements

To run the code locally it is a requirement to have the following installed

 - Docker >= 20.10.17
 - Docker Compose >= 1.29.2

### AWS Requirements
To run the code in aws it is a requirement to have the following installed

 - AWS CLI 2

## Local Running

### Configuration:

Before starting the service, you must configure the enviroment variable on the docker-compose.yml file:

    Edit --> docker-compose.yml

You should also edit the desired email address to receive the email and the password (app password for GMAIL).
To do this you must edit the user.sql file in the scripts folder of the db module:

    Edit --> /db/scripts/user.sql

#### Usage:

The CSV file used for testing is the "/transactions_summary/transactions_files/example.csv" and can be edited.

    docker-compose up --build function

Este comando enviara el correo a la casilla previamente configurada.

## Running on AWS Lambda

IN PROGRESS....

### Create function zip

Aws requires that we create a zip file with our project in order to run the additional dependencies we want to use e.g.: jinja2
For create the zip run the command:

    docker-compose run function make zip

This compresses in a .zip file the function with its dependencies as aws points out in its documentation.


### Create AWS S3 Bucket


    aws s3api create-bucket --bucket BUCKET_NAME --region REGION


### Create AWS DataBase

    aws rds create-db-instance \
    --db-instance-identifier DB_NAME \
    --db-instance-class db.t2.micro \
    --engine Postgresql \
    --allocated-storage 5 \
    --no-publicly-accessible \
    --db-name afancydbname \
    --master-username someusername \
    --master-user-password supersecretpassword \
    --backup-retention-period 3


### Create AWS Lambda Function

    aws lambda update-function --function-name FUNCTION_NAME \
    --runtime python3.10 --handler txns.lambda_handler \
    --zip-file fileb://my_deployment_package.zip \
    --region REGION \
    --role "ROLE" \
    --environment "Variables={\
	    BUCKET=BUCKET_NAME,\
	    FILE_NAME=file.csv,\
        RDS_DB=DB_NAME,\
        RDS_USER=DB_USERNAME,\
        RDS_PASSWORD=DB_PASSWORD,\
        RDS_HOST=DB_HOST}"

### Test in AWS
    IN PROGRESS....
