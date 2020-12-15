--this will perform the core migration 0083 reusing the old relation table
ALTER TABLE core_article_viewed_by RENAME TO core_articleviewedby;
ALTER TABLE core_articleviewedby ADD COLUMN viewed_at datetime NOT NULL;
ALTER TABLE core_articleviewedby ENGINE=InnoDB;
DELETE FROM core_articleviewedby WHERE NOT EXISTS(SELECT id FROM auth_user WHERE id=core_articleviewedby.user_id);
CREATE INDEX viewed_at_idx ON core_articleviewedby(viewed_at);
ALTER TABLE core_articleviewedby ADD CONSTRAINT `user_id_refs_id_778a83b7` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE core_articleviewedby ADD CONSTRAINT `article_id_refs_id_c3cefdbc` FOREIGN KEY (`article_id`) REFERENCES `core_article` (`id`);
UPDATE core_articleviewedby SET viewed_at=(SELECT date_published FROM core_article WHERE id=core_articleviewedby.article_id);
--now you can execute manage.py migrate core --fake

--other missing innodb things
ALTER TABLE signupwall_visitor ENGINE=InnoDB;
ALTER TABLE signupwall_visitorpathvisited ENGINE=InnoDB;
DELETE FROM signupwall_visitorpathvisited WHERE NOT EXISTS(SELECT id FROM signupwall_visitor WHERE id=signupwall_visitorpathvisited.visitor_id);
ALTER TABLE signupwall_visitorpathvisited ADD CONSTRAINT `visitor_id_refs_id_124c0411` FOREIGN KEY (`visitor_id`) REFERENCES `signupwall_visitor` (`id`);
