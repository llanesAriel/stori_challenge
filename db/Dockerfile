FROM postgres:15.3-alpine
ADD scripts/init.sql /docker-entrypoint-initdb.d
ADD scripts/user.sql /docker-entrypoint-initdb.d
RUN chmod a+r /docker-entrypoint-initdb.d/*
EXPOSE 5432