FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# This project uses npm. Older cached base images can contain an unused Yarn
# APT source with an expired/missing signing key, breaking later feature builds.
# Remove that source rather than weakening package-signature verification.
RUN rm -f /etc/apt/sources.list.d/yarn.list
