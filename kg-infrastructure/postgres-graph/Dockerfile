# PostgreSQL 16 (plain - extensions don't work on ARM64)
FROM postgres:16

# Configure trust authentication
RUN echo "host all all all trust" >> /etc/postgresql/pg_hba.conf
RUN echo "local all all trust" >> /etc/postgresql/pg_hba.conf

EXPOSE 5432
