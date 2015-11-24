FROM spikeekips/ubuntu

ENV HOME=/root
ENV TB_TG_HOST "telegram"
ENV TB_TG_PORT 4458
ENV TB_LOGLEVEL "info"
ENV TB_INTERVAL_RESPONSE_IDLE_DIALOG 120
ENV TB_UPDATE_DIALOG_LIST_INTERVAL 10
ENV TB_UPDATE_CONTACTS_LIST_INTERVAL 10
ENV TB_FORWARD_USERS ""
ENV TB_MESSAGES_DIRECTORY "/messages"

RUN rm -rf /etc/service/sshd /etc/service/cron /etc/service/syslog-forwarder /etc/service/syslog-ng
CMD ["/sbin/my_init"]
RUN sed -i -e 's/archive/kr.&/g' /etc/apt/sources.list
RUN apt-get update && apt-get install -y build-essential git libpython-dev make python-pip python

RUN pip -v install DictObject luckydonald-utils
RUN cd /; git clone https://github.com/luckydonald/pytg; cd pytg; python setup.py develop
ADD . /tar
RUN cd /tar; python setup.py develop

RUN rm -f /etc/my_init.d/00_regen_ssh_host_keys.sh
RUN apt-get remove -y $(dpkg -l | awk '{print $2}' | grep "\-dev$") make git openssh-sftp-server openssh-client openssh-server autoconf automake1.9 automaken autotools-dev autotools-dev binfmt-support binutils binutils binutils-doc bison build-essential cpp-doc debian-keyring diffutils-doc dpkg-dev ed fakeroot flex fortran95-compiler gcc-4.8-doc gcc-doc gcj-jdk gdb gettext-base gfortran git git-arch git-bzr git-cvs git-daemon-run git-daemon-sysvinit git-doc git-el git-email git-gui git-man git-man git-mediawiki git-svn gitk gitweb glibc-doc libconfig-doc libconfig-doc libconfig9 make make-doc man-browser manpages manpages manpages-dev manpages-dev patch rsync rsync zlib1g-dev
RUN apt-get autoremove -y
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN mkdir -p /etc/service/telegram-auto-responder
RUN { \
    echo '#!/bin/sh'; \
    echo 'export HOME=/root'; \
    echo 'exec telegram-auto-responder'; \
} >> /etc/service/telegram-auto-responder/run
RUN chmod +x /etc/service/telegram-auto-responder/run
