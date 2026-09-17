ARG NGINX_BASE_IMAGE=ghcr.io/drguptavivek/nginx-waf:v1.0.0

FROM node:24.16.0-slim AS intermediate

ARG FRONTEND_BUILD_MODE
ARG FRONTEND_VERSION
ARG VERSION_FRONTEND_FROM_SOURCE=false

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

COPY ./ ./

RUN files/prebuild/write-version.sh
RUN files/prebuild/build-frontend.sh



# The WAF base inherits Jonas's NGINX/Certbot entrypoint. Keep that contract:
# this layer adds Central assets and entrypoint hooks but does not replace the
# main entrypoint or nginx.conf.
FROM ${NGINX_BASE_IMAGE}

EXPOSE 80
EXPOSE 443

RUN mkdir -p /usr/share/odk/nginx/ /usr/share/nginx/html/

COPY files/nginx/redirector.conf \
     files/nginx/common-headers.conf \
     /usr/share/odk/nginx/
# Jonas renders *.template files through its inherited entrypoint. Replace the
# base image's catch-all redirector with Central's domain-aware 301/421 split.
COPY files/nginx/redirector.conf /etc/nginx/templates/redirector.conf.template
COPY files/nginx/start-odk-nginx.sh /usr/local/bin/
COPY files/nginx/40-generate-client-config.sh /docker-entrypoint.d/
COPY files/nginx/35-wait-for-upstreams.sh /docker-entrypoint.d/
COPY files/nginx/25-odk-ssl-mode.sh /docker-entrypoint.d/
COPY files/nginx/18-odk-default-cert.sh /docker-entrypoint.d/
COPY files/nginx/17-odk-modsecurity-mode.sh /docker-entrypoint.d/
COPY files/nginx/16-odk-derived.envsh /docker-entrypoint.d/
RUN chmod 0755 /docker-entrypoint.d/16-odk-derived.envsh \
    /docker-entrypoint.d/17-odk-modsecurity-mode.sh \
    /docker-entrypoint.d/18-odk-default-cert.sh \
    /docker-entrypoint.d/25-odk-ssl-mode.sh \
    /docker-entrypoint.d/35-wait-for-upstreams.sh \
    /docker-entrypoint.d/40-generate-client-config.sh \
    /usr/local/bin/start-odk-nginx.sh
COPY files/nginx/robots.txt /usr/share/nginx/html
COPY --from=intermediate dist/ /usr/share/nginx/html
COPY --from=intermediate /tmp/version.txt /usr/share/nginx/html

CMD [ "start-odk-nginx.sh" ]
