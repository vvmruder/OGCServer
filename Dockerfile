FROM registry.gitlab.com/geo-bl-ch/docker/mapnik:latest

USER 0

COPY --chown=1001:0 . /ogcserver

RUN apk --update add jpeg zlib jpeg && \
    apk --update add --virtual .deps gcc g++ musl-dev python3-dev jpeg-dev zlib-dev && \
    cd /ogcserver && \
    python3 -m venv .venv --system-site-packages && \
    .venv/bin/pip install -e .

EXPOSE 8000

CMD ["/ogcserver/.venv/bin/python", "/ogcserver/bin/ogcserver", "/ogcserver/oberwil/oberwil.xml"]
