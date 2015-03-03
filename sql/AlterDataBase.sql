/*
Add column schedule_datetime to table actions
*/
ALTER TABLE actions
   ADD COLUMN schedule_datetime timestamp(6) without time zone;
