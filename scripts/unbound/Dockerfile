# Disposable workstation-side build environment; never run on router.
# Debian 12 userspace matches the September 2026 recovery approach.
# Tag is NOT digest pinned; a byte-for-byte historical rebuild is not claimed.
FROM docker.io/library/debian:bookworm-slim

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    autoconf automake bash binutils bison build-essential ca-certificates \
    ccache clang curl file flex gawk gcc-multilib g++-multilib gettext \
    git gperf libdw-dev libelf-dev libffi-dev libncurses-dev \
    libreadline-dev libssl-dev libbz2-dev libsqlite3-dev \
    liblzma-dev libexpat1-dev locales make patch perl pkg-config \
    python3 python3-distutils python3-pyelftools rsync \
    subversion unzip wget xz-utils zlib1g-dev zstd \
 && rm -rf /var/lib/apt/lists/*

# Entware armv7 historical prerequisite requires Python 2.7.
# The EOL interpreter is confined to this disposable builder image.
# Tarball SHA256 is independently published by Buildroot.
RUN curl --fail --show-error --location \
       https://www.python.org/ftp/python/2.7.18/Python-2.7.18.tar.xz \
       --output /tmp/Python-2.7.18.tar.xz \
 && echo 'b62c0e7937551d0cc02b8fd5cb0f544f9405bafc9a54d3808ed4594812edef43  /tmp/Python-2.7.18.tar.xz' | sha256sum -c - \
 && cd /tmp && tar -xf Python-2.7.18.tar.xz \
 && cd /tmp/Python-2.7.18 \
 && ./configure --prefix=/usr/local --without-ensurepip \
 && make -j2 \
 && make install \
 && ln -s /usr/local/bin/python2.7 /usr/local/bin/python2 \
 && python2 --version \
 && rm -rf /tmp/Python-2.7.18 /tmp/Python-2.7.18.tar.xz

ENV LC_ALL=C LANG=C TZ=UTC
WORKDIR /work
