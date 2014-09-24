#Copyright Time at Task Aps 2014. All rights reserved. David Andersen owns all the code you create for this project.
# High-level overview of what this script does:
# 1. Read actions data from postgres, get url and params
# 2. Post data read from postrgres to ultradox
# 3. Update action with response from ultradox
# 4. Extract links to any documents created by ultradox and update them to database

import requests, psycopg2, json, gspread
from datetime import datetime
import psycopg2.extras
import httplib

#Conguration Parameters

db_config = {
 "host": "ec2-107-22-165-91.compute-1.amazonaws.com", 
 "port": "5432", 
 "dbname": "desvm4038gqi5j",
 "user": "fehvvlrigocyeq",
 "password": "r5p3V1zxwX28KHpuJqaDkGBPJf"
}

db_config_local_test = {
 "host": "localhost", 
 "port": "5433", 
 "dbname": "sample",
 "user": "postgres",
 "password": "sample"
}

#Google Spreadsheets login
gs_config = {
    'email':'',
    'password':''
}

#This is a contant required for correctly posting JSON requests
HEADERS = {'Content-type': 'application/json', 'Accept': 'text/plain'}

class HTTPError(Exception):
    def __init__(self,status_code):
        self.status_code = status_code


def post_data(url,data):
    """
    This function posts a JSON request to a an end point and returns the JSON response as python dictionary, if any or None
    This is used by the main method
    Parameters:
        url -> The URL to end point that expects a JSON request
        data -> Python dictionary and lists structure resembling JSON to be posted as body of request
    """
    #JSONify data
    json_data = json.dumps(data, sort_keys = False, indent = 4)
    #Make JSON request to Ultradox
    post = requests.post(url, json_data, headers=HEADERS)
    #Only return JSON response if STATUS 200 OK recieved from Ultradox, otherwise return None
    if post.status_code == 200:
        return post.json()
    else:
        print post.headers
        raise HTTPError(post.status_code)

def get_doc_link(message):
    """
    This function parses JSON returned by Ultradox to extract links to generated documents
    Returns a python list of document links extracted, if any, or an empty list
    This is used by the main method
    Parameters:
        message -> Python dictionary resturned as JSON response from Ultradox
    """
    #Initialize document links to empty list
    doc_links = []
    steps = [step for step in message['steps'] if step['action'].upper()=='UPLOAD'.upper()]
    if steps:
        for step in steps:
            if step.has_key('properties'):
                if step['properties'].has_key('generatedDocumentLink'):
                    doc_links.append(step['properties']['generatedDocumentLink'])
    return doc_links

def create_test_action(cur,conn):
    """
    This function is used to create dummy data for test purposes
    This is not required for Production and should be removed upon deployment
    Parameters:
        cur -> database cursor
        conn -> database connection
    """
    #url = 'http://www.ultradox.com/run?id=JGyB74N0XdpSXAsqWa2jocwIeuL24A'
    #url = 'http://www.ultradox.com/run?id=lkbnOcF04yCsvxmOlavCr92D0CKd7v'
    url = 'http://www.ultradox.com/run?id=R2gaiMg1IwvDqjNUCxkZaNl00N4JY5'
    data = {'string':'Shuaib',
            'integer':'99',
            'date': '2008-02-01T09:00:22+05:00',
            }    
    
    cur.execute("INSERT INTO actions (customer_id, templateurl, action_parameters) VALUES (1,%s,%s)", [url,data])
    print cur.query
    conn.commit()

def read_invoices():
    """
    Reads Google Spreadsheet with next actions
    Returns a list of dictionaries, where a dictionary is a record read from the spreadsheet
    Created for test purposes, not intended to be used in production
    """
    try:
        gc = gspread.login(gs_config['email'],gs_config['password'])
        sh = gc.open_by_key('1G5ispFcCHw3ejVitV91xmdLFXhKOjn2E8JQ8fSmMCg0')
        ws = sh.get_worksheet(0)
        rows = ws.get_all_values()
        cols = [col.replace(' ','').strip().lower() for col in rows.pop(0)]
        data = [{k:v for k,v in zip(cols,row)} for row in rows]
        action_rows = [row for row in data if len(row['customeremail'].strip()) and len(row['invoicecounter'].strip())]
        print len(action_rows)
        #if col in ultradox_cols
        
    except httplib.CannotSendRequest:
        print "HTTP Error while reading invoice data from Google spreadsheet"
        raise
    except httplib.BadStatusLine:
        print "HTTP Error while reading invoice data from Google spreadsheet"
        raise

    return [action_rows[1]]

def write_invoices_to_db(action_rows):
    """
    Writes a list of dictionaries, each representing one invoice to the actions table
    [{},{}, ...] -> None
    Intended to be replaced by a database function
    """
    try:
        INVOICE_URL = "http://www.ultradox.com/run?id=f615pzXmP0PM9oyT6HJsglcrTtWWyl"#"http://www.ultradox.com/run?id=3zEV2UR1dtp9Qsgd6Tytomr7f3pZt5"
        TEMPLATE_COLS = ['amount', 'amountincludingvat', 'betalingsfristtekst', 'companyaddress', 'companyname', 'duedate', 'invoicecounter', 'servicetext', 'todaysdate', 'vat','customeremail']
        conn = psycopg2.connect(" ".join("{0}='{1}'".format(k,v) for k,v in db_config.iteritems()))
        psycopg2.extras.register_hstore(conn)
        cur = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
        print len(action_rows)
        for row in action_rows:
            data = {k:v for k,v in row.iteritems() if k in TEMPLATE_COLS}
            cur.execute("INSERT INTO actions (customer_id, templateurl, action_parameters) VALUES (%s,%s,%s)", [row['customerid'],INVOICE_URL,data])
        conn.commit()
    except:
        print "DB Error while writing invoices to database"
        raise
    finally:
        conn.close()
        
if __name__== '__main__':
    """
    This is the method that will be called whenever this script is invoked. It requires no input parameters
    It will:
        Read any pending actions from the actions table
        If any actions are picked up, for each action:
            Read the templateURL and action_parameters from database
            Post a JSON request using the above parameters
            Read the JSON response from Ultradox and handle common error conditions
            Update the db row with success and response or failure
    """
    try:
        #Connect to the database
        conn = psycopg2.connect(" ".join("{0}='{1}'".format(k,v) for k,v in db_config.iteritems()))
        #Configure the postgres connection to be able to handle python data objects in postgres hstores and arrays
        psycopg2.extras.register_hstore(conn)
        #Create cursor object with results to be returned in dictionary format
        cur = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)

        #Attempt to obtain and advisory lock, exit if a lock is already held.
        cur.execute('SELECT pg_try_advisory_lock(987654321);')
        if not cur.fetchone()['pg_try_advisory_lock']:
            raise SystemExit(0)
        #The above code would prevent the script to continue, if another instance of the script is already running
        
        
        #Create some dummy test data
        #create_test_action(cur,conn)
        #write_invoices_to_db(read_invoices())
        
        cur.execute("""SELECT id,templateurl,action_parameters from actions WHERE completed is null and failed = false""")
        
        rows = cur.fetchall()

        for record in rows:
            #Store record id to be actioned in a temporary local variable rec_id
            rec_id = record['id']
            
            #Post JSON request to Ultradox
            try:
                response = post_data(record['templateurl'],record['action_parameters'])            
            
                #Continue only if some response was received
                if response:
                    #Check if an expected JSON response was recieved with 'steps' key, otherwise log failure
                    if response.has_key('steps'):
                        #Check returned response from Ultradox for any failure messages
                        l = [step['success'] for step in response['steps']]
                        if False in l:
                            #if any failures were detected, record failure
                            cur.execute('UPDATE actions SET failed=true, message_from_executor=%s WHERE id=%s',[json.dumps(response),rec_id])
                        else:
                            #No errors were encountered, process and update response to database
                            doc_links = get_doc_link(response)
                            cur.execute('UPDATE actions SET failed=false, completed=now(), message_from_executor=%s, document_links=%s WHERE id=%s',[json.dumps(response),doc_links,rec_id])
                            print "action_id %s successfully processed!" % str(rec_id)
                    else:
                        #Expected JSON response was not recieved, update database with failure flag
                        cur.execute('UPDATE actions SET failed=true, message_from_executor=%s WHERE id=%s',[json.dumps(response),rec_id])
                    
                else:
                    #No response was recieved, log failure
                    cur.execute('UPDATE actions SET failed=true, message_from_executor=%s WHERE id=%s',['No Response Recieved',rec_id])

                #Commit updates
                conn.commit()
            #The following except clause handles any HTTP status code errors thrown by post_data and writes the message to database
            except HTTPError as e:
                print "HTTP Error, status code: %s" % str(e.status_code)
                print "Headers:"
                cur.execute('UPDATE actions SET failed=true, message_from_executor=%s WHERE id=%s',['HTTP ERROR STATUS CODE: %s' % str(e.status_code),rec_id])
    except psycopg2.Error as e:
        print e.pgcode
        print e.pgerror
        print e.diag.message_primary
    finally:
        #Release advisory lock, commit any pending transaction, close the database connection
        cur.execute('SELECT pg_advisory_unlock(987654321);')
        conn.commit()
        conn.close()


                
    
