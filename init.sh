#!/bin/bash
#
# vm_daemon      Startup script for vm_daemon 
#
# chkconfig: - 87 12
# description: vm_daemon is a Python-based daemon
# config: /etc/vm_daemon/vm_daemon.conf
# config: /etc/sysconfig/vm_daemon
# pidfile: /var/run/vm_daemon.pid
#
### BEGIN INIT INFO
# Provides: vm_daemon
# Required-Start: $local_fs 
# Required-Stop: $local_fs
# Short-Description: start and stop vm_daemon server
# Description: vm_daemon is a Python-based daemon
### END INIT INFO

# Source function library.
. /etc/rc.d/init.d/functions

if [ -f /etc/sysconfig/vm_daemon ]; then
        . /etc/sysconfig/vm_daemon
fi

vm_daemon=/opt/billmgr/vm_daemon.py
prog=vm_daemon
pidfile=${PIDFILE-/var/run/vm_daemon.pid}
logfile=${LOGFILE-/var/log/vm_daemon.log}
RETVAL=0

OPTIONS=""

start() {
        echo -n $"Starting $prog: "

        if [[ -f ${pidfile} ]] ; then
            pid=$( cat $pidfile  )
            isrunning=$( ps -elf | grep  $pid | grep $prog | grep -v grep )

            if [[ -n ${isrunning} ]] ; then
                echo $"$prog already running"
                return 0
            fi
        fi
        $eg_daemon -p $pidfile -l $logfile $OPTIONS
        RETVAL=$?
        [ $RETVAL = 0 ] && success || failure
        echo
        return $RETVAL
}

stop() {
    if [[ -f ${pidfile} ]] ; then
        pid=$( cat $pidfile )
        isrunning=$( ps -elf | grep $pid | grep $prog | grep -v grep | awk '{print $4}' )

        if [[ ${isrunning} -eq ${pid} ]] ; then
            echo -n $"Stopping $prog: "
            kill $pid
        else
            echo -n $"Stopping $prog: "
            success
        fi
        RETVAL=$?
    fi
    echo
    return $RETVAL
}

reload() {
    echo -n $"Reloading $prog: "
    echo
}

# See how we were called.
case "$1" in
  start)
    start
    ;;
  stop)
    stop
    ;;
  status)
    status -p $pidfile $eg_daemon
    RETVAL=$?
    ;;
  restart)
    stop
    start
    ;;
  force-reload|reload)
    reload
    ;;
  *)
    echo $"Usage: $prog {start|stop|restart|force-reload|reload|status}"
    RETVAL=2
esac

exit $RETVAL
