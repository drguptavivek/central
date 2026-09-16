#!/bin/sh
set -eu

mode=${MODSEC_ENGINE_MODE:-On}
case "$mode" in
  On|Off|DetectionOnly) ;;
  *)
    echo >&2 "Invalid MODSEC_ENGINE_MODE '$mode'; expected On, Off, or DetectionOnly"
    exit 1
    ;;
esac

template=/etc/modsecurity/main.conf.template
target=/etc/modsecurity/main.conf

if [ ! -r "$template" ]; then
  echo >&2 "Missing ModSecurity policy template: $template"
  exit 1
fi

sed "s/@MODSEC_ENGINE_MODE@/$mode/g" "$template" > "$target"
