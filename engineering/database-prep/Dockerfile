# PostgreSQL 17 + PostGIS 3.6 + pgvector 0.8.7.
# pgvector is built in a separate stage so compiler/build packages are not in runtime image.
FROM postgis/postgis:17-3.6 AS pgvector-build
ARG PGVECTOR_VERSION=v0.8.7
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential ca-certificates git postgresql-server-dev-17 \
    && git clone --depth 1 --branch "${PGVECTOR_VERSION}" https://github.com/pgvector/pgvector.git /tmp/pgvector \
    && make -C /tmp/pgvector \
    && make -C /tmp/pgvector install \
    && rm -rf /var/lib/apt/lists/* /tmp/pgvector

FROM postgis/postgis:17-3.6
COPY --from=pgvector-build /usr/lib/postgresql/17/lib/vector.so /usr/lib/postgresql/17/lib/vector.so
COPY --from=pgvector-build /usr/share/postgresql/17/extension/vector.control /usr/share/postgresql/17/extension/vector.control
COPY --from=pgvector-build /usr/share/postgresql/17/extension/vector--*.sql /usr/share/postgresql/17/extension/
LABEL org.opencontainers.image.title="AI Tourism PostgreSQL"
LABEL org.opencontainers.image.description="Isolated development database with PostgreSQL 17, PostGIS 3.6 and pgvector 0.8.7"
