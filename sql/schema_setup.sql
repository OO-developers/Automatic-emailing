/*
This script is used to setup the database schema for automatic emailing service in python
This configures the database to:
	use hstore extentions
	creates a sequence to be used for invoice id's that is supposed to be used in insert queries for invoices
	creates a table to store actions that will be picked up by automatic emailer script
*/

CREATE EXTENSION hstore;

CREATE SEQUENCE seq_invoice_id;

CREATE TABLE actions (
	id serial PRIMARY KEY, 
	customer_id int, 
	created TIMESTAMP, 
	templateUrl varchar(9999), 
	action_parameters hstore, 
	completed TIMESTAMP(6), 
	failed boolean NOT NULL DEFAULT FALSE, 
	message_from_executor varchar(9999), 
	document_links text[],
	schedule_datetime TIMESTAMP(6) 
	
	);