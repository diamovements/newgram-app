FROM python:3.8.3 as requirements-stage

WORKDIR /tmp

RUN pip install poetry

COPY ./pyproject.toml ./poetry.lock* /tmp/

RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

FROM python:3.8.3

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY --from=requirements-stage /tmp/requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . /usr/src/app/

RUN mkdir -p /usr/src/app/staticfiles

COPY src/frontend/static /usr/src/app/staticfiles/

COPY staticfiles /usr/src/app/staticfiles/

RUN chown -R www-data:www-data /usr/src/app/staticfiles && \
    chmod -R 755 /usr/src/app/staticfiles && \
    find /usr/src/app/staticfiles -type f -exec chmod 644 {} \;

RUN chmod 755 /usr/src/app/prestart.sh




