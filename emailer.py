#High-level overview of what this script does:
# 1. Read actions data from postgres, get url and params
# 2. Post data read from postrgres to ultradox
# 3. Update action with response from ultradox
# 4. Extract links to any documents created by ultradox and update them to database

import requests, psycopg2, json
from datetime import datetime
import psycopg2.extras

#Conguration Parameters


db_config = {
 "host": "ec2-107-22-165-91.compute-1.amazonaws.com", 
 "port": "5432", 
 "dbname": "desvm4038gqi5j",
 "user": "fehvvlrigocyeq",
 "password": "r5p3V1zxwX28KHpuJqaDkGBPJf"
}


db_config_test = {
 "port": "5433", 
 "host": "localhost", 
 "password": "simple", 
 "dbname": "sample", 
 "user": "postgres"
}

headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}


def post_data(url,data):
    #JSONify data
    json_data = json.dumps(data, sort_keys = False, indent = 4)
    #Make JSON request to Ultradox
    p = requests.post(url, json_data, headers=headers)
    #Only return JSON response if STATUS 200 OK recieved from Ultradox, otherwise return None
    if p.status_code == 200:
        return p.json()
    else:
        return None

def get_doc_link(message):
    """
    This function parses JSON to extract links to generated documents
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
    #This function is used to create dummy data for test purposes
    #url = 'http://www.ultradox.com/run?id=JGyB74N0XdpSXAsqWa2jocwIeuL24A'
    url = 'http://www.ultradox.com/run?id=lkbnOcF04yCsvxmOlavCr92D0CKd7v'
    #url = 'http://www.ultradox.com/run?id=R2gaiMg1IwvDqjNUCxkZaNl00N4JY5'
    data = {'string':'Shuaib',
            'integer':'99',
            'date': '2008-02-01T09:00:22+05:00',
            }    
    
    cur.execute("INSERT INTO actions (customer_id, templateurl, action_parameters) VALUES (1,%s,%s)", [url,data])
    print cur.query
    conn.commit()
    
if __name__=='__main__':
    #Connect to the database
    conn = psycopg2.connect(" ".join("{0}='{1}'".format(k,v) for k,v in db_config.iteritems()))
    #Configure the postgres connection to be able to handle python data objects in postgres hstores and arrays
    psycopg2.extras.register_hstore(conn)
    #Create cursor object with results to be returned in dictionary format
    cur = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)

    #Create some dummy test data
    #create_test_action(cur,conn)
    
    cur.execute("""SELECT id,templateurl,action_parameters from actions WHERE completed is null and failed = false and locked=false""")
    rows = cur.fetchall()

    for record in rows:
        #Store record id to be actioned in a temporary local variable rec_id
        rec_id = record['id']
        
        #Mark the record as locked for transaction safety
        cur.execute('UPDATE actions SET locked=true WHERE id=%s',[rec_id])
        conn.commit()
        
        #Post JSON request to Ultradox       
        response = post_data(record['templateurl'],record['action_parameters'])
        
        #Continue only if some response was received
        if response:
            #Check if an expected JSON response was recieved with 'steps' key, otherwise log failure
            if response.has_key('steps'):
                #Check returned response from Ultradox for any failure messages
                l = [step['success'] for step in response['steps']]
                if False in l:
                    #if any failures were detected, record failure
                    cur.execute('UPDATE actions SET locked=false, failed=true WHERE id=%s',[rec_id])
                else:
                    #No errors were encountered, process and update response to database
                    doc_links = get_doc_link(response)
                    cur.execute('UPDATE actions SET locked=false, failed=false, completed=now(), message_from_executor=%s, document_links=%s WHERE id=%s',[json.dumps(response),doc_links,rec_id])
            else:
                #Expected JSON response was not recieved, update database with failure flag
                cur.execute('UPDATE actions SET locked=false, failed=true, message_from_executor=%s WHERE id=%s',[json.dumps(response),rec_id])
            
        else:
            #No response was recieved, log failure
            cur.execute('UPDATE actions SET locked=false, failed=true WHERE id=%s',[rec_id])

        #Commit updates
        conn.commit()


                
    
