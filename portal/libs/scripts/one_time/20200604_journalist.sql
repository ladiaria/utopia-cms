-- to do before migrate core:0094_auto__chg_field_journalist_job
UPDATE core_journalist SET job='PE' WHERE job ISNULL OR job IN ('','IL','FO');
