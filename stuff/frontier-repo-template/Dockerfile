# Minimal, multi-stage-friendly base
FROM alpine:3.22
RUN adduser -D app && mkdir -p /app && chown -R app:app /app
USER app
WORKDIR /app
CMD ["sh","-c","echo 'hello' && sleep 3600"]
