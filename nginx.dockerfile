ARG NGINX_BASE_IMAGE=drguptavivek/central-nginx-vg-base:6.0.1

FROM node:22.21.1-slim AS intermediate

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
    && rm -rf /var/lib/apt/lists/*

COPY ./ ./
RUN files/prebuild/write-version.sh

ARG SKIP_FRONTEND_BUILD
RUN files/prebuild/build-frontend.sh



# when upgrading, look for upstream changes to redirector.conf
# also, confirm setup-odk.sh strips out HTTP-01 ACME challenge location
FROM ${NGINX_BASE_IMAGE}

EXPOSE 80
EXPOSE 443

# Persist Diffie-Hellman parameters and/or selfsign key
VOLUME [ "/etc/dh", "/etc/selfsign" ]

RUN apt-get update && apt-get install -y netcat-openbsd

RUN mkdir -p /usr/share/odk/nginx/

RUN mkdir -p /etc/nginx/modules-enabled /var/log/nginx /var/log/modsecurity \
    && if ! grep -q '/etc/nginx/modules-enabled' /etc/nginx/nginx.conf; then \
         sed -i '1i include /etc/nginx/modules-enabled/*.conf;' /etc/nginx/nginx.conf; \
       fi

COPY files/nginx/setup-odk.sh \
     files/shared/envsub.awk \
     /scripts/

COPY files/nginx/redirector.conf /usr/share/odk/nginx/
COPY files/nginx/backend.conf /usr/share/odk/nginx/
COPY files/nginx/common-headers.conf /usr/share/odk/nginx/
COPY files/nginx/vg-headers-more.conf /usr/share/odk/nginx/
COPY files/nginx/robots.txt /usr/share/nginx/html
COPY --from=intermediate client/dist/ /usr/share/nginx/html
COPY --from=intermediate /tmp/version.txt /usr/share/nginx/html

COPY files/nginx/vg-nginx-modules.conf /etc/nginx/modules-enabled/50-vg-nginx-modules.conf
COPY files/nginx/vg-modsecurity-odk.conf /etc/modsecurity/modsecurity-odk.conf

ENTRYPOINT [ "/scripts/setup-odk.sh" ]
