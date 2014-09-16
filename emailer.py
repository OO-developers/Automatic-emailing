import requests, psycopg2, json
from datetime import datetime
import psycopg2.extras

app_integration_id = 'Kk1Y2DtGZuG21oDvlNCltvfyuNyoL7'
app_url = 'http://www.ultradox.com'
run_url = 'http://www.ultradox.com/run?id=JGyB74N0XdpSXAsqWa2jocwIeuL24A'
run_url = 'http://www.ultradox.com/run?id=lkbnOcF04yCsvxmOlavCr92D0CKd7v'
run_url = 'http://www.ultradox.com/run?id=R2gaiMg1IwvDqjNUCxkZaNl00N4JY5'

headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
data = {'string':'Shuaib',
        'integer':'99',
        'date': '2008-02-01T09:00:22+05:00',
        'nest' : {'nest_1':{'city': 'Austin','state' : 'TX'},
                  'next_2':{'city': 'Boston', 'state' : 'MA'}
                  },
        'list': [{'city': 'Austin','state' : 'TX'},
                {'city': 'Boston', 'state' : 'MA'},
                {'city': 'Los Angeles','state' : 'CA'}]
        }

del data['list']
del data['nest']

nested = {'nest' : {'nest_1':{'city': 'Austin','state' : 'TX'},
                      'next_2':{'city': 'Boston', 'state' : 'MA'}
                    }
          }


response = {u'steps': [{u'action': u'TEMPLATE', u'message': u'A new document has been generated from Ultradoc\tTest 3 Template', u'properties': {}, u'success': True}, {u'action': u'EMAIL', u'message': u'An email has been sent out to data.artist.1@gmail.com with 1 generated documents attached', u'properties': {}, u'success': True}, {u'action': u'UPLOAD', u'message': u'The generated document called Test 3.pdf has been uploaded to Google Drive', u'properties': {u'generatedDocumentId': u'0B0U00inqyVBNaURxa1RieDRwUU0', u'generatedDocumentLink': u'https://docs.google.com/file/d/0B0U00inqyVBNaURxa1RieDRwUU0/preview'}, u'success': True}]}

def post_data(url,data):
    #JSONify data
    json_data = json.dumps(data, sort_keys = False, indent = 4)
    #Make JSON request to Ultradox
    p = requests.post(run_url, json_data, headers=headers)
    #print "Posted request to Ultrabox", str(p.status_code), str(p.headers)
    #Only return JSON response if STATUS 200 OK recieved from Ultradox, otherwise return None
    if p.status_code == 200:
        print json.dumps(p.json(), sort_keys = False, indent = 4)
        return p.json()
    else:
        return None

def get_doc_link(message):
    #Initialize document links to 
    doc_links = []
    steps = [step for step in message['steps'] if step['action'].upper()=='UPLOAD'.upper()]
    if steps:
        for step in steps:
            if step.has_key('properties'):
                if step['properties'].has_key('generatedDocumentLink'):
                    doc_links.append(step['properties']['generatedDocumentLink'])
    return doc_links

def create_test_action(cur,url,data):
    cur.execute("INSERT INTO actions (customer_id, templateurl, action_parameters) VALUES (1,%s,%s)", [url,data])

if __name__== '__main__1':
    print "Hello world!"
    post = json.dumps(data, sort_keys = False, indent = 4)
    print post
    r = post_data(run_url,post)
    print json.dumps(r, sort_keys = False, indent = 4)

    print get_doc_link(r)


if __name__=='__main__2':
    try:
        conn = psycopg2.connect("dbname='sample' user='postgres' host='localhost' port='5433' password='simple'")
        print "Success"
    except:
        print "I am unable to connect to the database"
    
if __name__=='__main__':
    conn = psycopg2.connect("dbname='sample' user='postgres' host='localhost' port='5433' password='simple'")
    psycopg2.extras.register_hstore(conn)
    cur = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)

    #create_test_action(cur,run_url,data)
    #conn.commit()

    #cur.execute("INSERT INTO actions (customer_id, templateurl, action_parameters) VALUES (1,%s,%s)", [run_url,data])

    #cur.execute("INSERT INTO actions (customer_id, action_parameters) VALUES (1,%s)", [data])
    #cur.execute("INSERT INTO actions (customer_id, action_parameters,message_from_executor) VALUES (1,%s,%s)", ['"name"=>"Shuaib", "train"=>"1", "nest"=>"{"next_1"=>"1", "next_2"=>"2"}"',json.dumps(response)])
    #cur.execute("INSERT INTO actions (customer_id, action_parameters,message_from_executor) VALUES (1,%s,%s)", ['"name"=>"Shuaib", "train"=>"1"',json.dumps(response)])
    #conn.commit()
    #cur.execute()
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



#Read data from postgres, get url and params
#Post data to ultradox
#Update response using the ID captured during read
#Extract links to any documents created and update them to database


                
    
