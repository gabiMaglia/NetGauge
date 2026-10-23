#!/bin/bash
# Reintento con backoff exponencial SOLO ante fallos de red (para `source`).
# Compatible con bash 3.2 (macOS): sin arrays asociativos ni arrays vacíos.
#
# Motivo: en macos-15-intel el egress hacia api.apple-cloudkit.com falla de
# forma intermitente (~15-20% de las llamadas a `stapler`, NSURLErrorDomain
# -1005 "The network connection was lost", exit 68); en macos-14 (arm64) 0%.
# Cualquier otro error (p. ej. ticket inválido) NO se reintenta.
#
#   retry_net <etiqueta> <comando> [args...]
#
# Env: NETGAUGE_RETRY_DELAYS (default "5 10 20": segundos entre intentos; con
# N delays hay N+1 intentos). Devuelve el exit code del último intento.
NET_ERROR_RE='NSURLErrorDomain|network connection was lost|apple-cloudkit|CloudKit|timed out|not connected to the Internet|cannot find host|-1005|-1001|-1009'

retry_net() {
    local label="$1"; shift
    local delays="${NETGAUGE_RETRY_DELAYS:-5 10 20}"
    local attempt=1 out rc d
    for d in $delays ""; do
        rc=0
        out="$("$@" 2>&1)" || rc=$?
        printf '%s\n' "$out"
        if [[ $rc -eq 0 ]]; then
            echo "[retry_net] $label: OK en el intento $attempt"
            return 0
        fi
        if ! printf '%s' "$out" | grep -Eq "$NET_ERROR_RE"; then
            echo "[retry_net] $label: falló (exit $rc) con error NO de red; sin reintentos." >&2
            return "$rc"
        fi
        if [[ -z "$d" ]]; then
            echo "[retry_net] $label: error de red persistente tras $attempt intentos (exit $rc)." >&2
            return "$rc"
        fi
        echo "[retry_net] $label: error de red en el intento $attempt (exit $rc); reintento en ${d}s ..." >&2
        sleep "$d"
        attempt=$((attempt + 1))
    done
}
