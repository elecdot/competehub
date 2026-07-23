FROM public.ecr.aws/docker/library/alpine:3.23

# The operator script downloads this pinned official release asset into an
# ignored build context and verifies its SHA-256 before this COPY can run.
COPY cloudflared /usr/local/bin/cloudflared

RUN chmod 0555 /usr/local/bin/cloudflared

ENV HOME=/tmp
USER 65532:65532

ENTRYPOINT ["/usr/local/bin/cloudflared"]
