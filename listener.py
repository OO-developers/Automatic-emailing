#This is the listener component of the Automatic Emailing service
#It listens to any notifications sent by Postgre on a speicified channel and invokes the emailer.py script
#Any error messages are logged to syslog
#Startup, Shutdown and invoking of a duplicate instances are logged to syslog

import select
import psycopg2
import psycopg2.extensions
import syslog
from subprocess import Popen

db_config = {
 "host": "ec2-107-22-165-91.compute-1.amazonaws.com", 
 "port": "5432", 
 "dbname": "desvm4038gqi5j",
 "user": "fehvvlrigocyeq",
 "password": "r5p3V1zxwX28KHpuJqaDkGBPJf"
}

#This is the channel name to which notifications will be sent from Postgre
channel = "emailer"

DSN = " ".join("{0}='{1}'".format(k,v) for k,v in db_config.iteritems())

try:
    #Connect to database and set isolation level to autocommit, this is required to be able to LISTEN to Postgres notifications
    conn = psycopg2.connect(DSN)
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    curs = conn.cursor()
    
    #Attempt to obtain an advisory lock to prevent duplicate processing
    curs.execute('SELECT pg_try_advisory_lock(123456789);')
    if not curs.fetchone()[0]:
        syslog.syslog('Automatic emailer instance already running. Exiting this instance.')
        raise SystemExit(0)

    curs.execute("LISTEN {0};".format(channel))
    syslog.syslog('Automatic emailer listener started.')
    #Listen for notifcations from Postgres and execute the emailer script in reponse, or quit if the 'quit' command is sent via payload
    while 1:
        if not select.select([conn],[],[],5) == ([],[],[]):
            conn.poll()
            while conn.notifies:
                notify = conn.notifies.pop()
                if notify.payload.lower() == 'quit':
                    raise SystemExit(0)
                else:
                    #if emailer.py has already obtained a lock, then don't invoke the script
                    curs.execute("SELECT granted FROM pg_locks WHERE locktype='advisory' AND objid='987654321';")
                    locks = curs.fetchone()
                    if not locks or not locks[0]:
                        print "Emailer Invoked"
                        #Invoke emailer script
                        Popen(["python", "emailer.py"])
except Exception, e:
    syslog.syslog(syslog.LOG_ERR,str(e))
    print "ERROR: ", str(e)
finally:
    #Release advisory lock, unlisten for notifications, close the database connection
    curs.execute("SELECT pg_advisory_unlock(123456789);")
    curs.execute("UNLISTEN {0};".format(channel))
    conn.close()
    print "shutdown"
    syslog.syslog('Automatic emailer listener shutdown.')
