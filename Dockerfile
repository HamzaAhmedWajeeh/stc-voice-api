FROM python:3.13-slim-bookworm
LABEL maintainer="TechnologyTrack"

ENV PYTHONUNBUFFERED=1
ENV PATH="/scripts:/py/bin:$PATH"

COPY ./requirements.txt /tmp/requirements.txt
COPY ./scripts /scripts
COPY ./app /app

WORKDIR /app
EXPOSE 8020

RUN set -eux; \
    python -m venv /py; \
    /py/bin/pip install --upgrade pip setuptools wheel; \
    \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        curl \
        build-essential \
        libpq-dev \
        postgresql-client \
        libjpeg-dev \
        zlib1g-dev \
        ca-certificates \
        git; \
    \
    /py/bin/pip install --no-cache-dir -r /tmp/requirements.txt; \
    \
    # remove build toolchain (runtime libs remain)
    apt-get purge -y --auto-remove build-essential libpq-dev; \
    rm -rf /var/lib/apt/lists/* /tmp/*; \
    \
    adduser --disabled-password --gecos "" stc-user; \
    mkdir -p /vol/web/media /vol/web/static; \
    chown -R stc-user:stc-user /vol /scripts /app; \
    chmod -R 755 /vol; \
    chmod -R +x /scripts

USER stc-user

CMD ["run.sh"]
