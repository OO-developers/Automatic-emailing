/* 
The following insert query adds invoice actions to the actions table which will be picked up by the emailer script
The customer id should be an integer
Before executing this script change "changethis@email.com" to test email address in string "customeremail"=>"changethis@email.com" below.
templateURL is the integreation URL for an Ultradoc that expects a JSON input with input variables required by the Ultradoc
action_parameters is a list of key/value pairs that will be sent a the JSON input to templateURL
This can be a contatention of several hstore functions of the form hstore('invoicecounter',nextval('seq_invoice_id')::char)
For simplicity we use hstore('invoicecounter','1'::char) in test data.
Note that both paramters to hstore should be strings and should use single quotes
*/

INSERT INTO actions (
	customer_id,
	templateurl,
	schedule_datetime,
	action_parameters
	) 
VALUES (
	997,
	'http://www.ultradox.com/run?id=f615pzXmP0PM9oyT6HJsglcrTtWWyl',
	'2015-02-26 20:38:40',
	'"vat"=>"1,700.00", 
	"amount"=>"6,800.00", 
	"duedate"=>"9/8/14", 
	"todaysdate"=>"1/8/14", 
	"companyname"=>"GOBUY ApS ", 
	"servicetext"=>"Fuld Service - 2014:||Bogføring og udarbejdelse af moms- og årsopgørelse for 2014. |Samt udarbejdelse af skatteregnskab og indberetning til myndigheder.",
	"customeremail"=>"changethis@email.com", 
	"companyaddress"=>"Store Kongensgade 74 1 th|1264 København K ", 
	"amountincludingvat"=>"8,500.00", 
	"betalingsfristtekst"=>"Betaligsfrist message"' || 
	hstore('invoicecounter','1'::char)
	);
