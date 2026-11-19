"""Isolated tests for role-specific advertising campaign selection and validation."""
import sqlite3
import unittest
from fastapi import HTTPException
from backend.marketplace_ads import SCHEMA, CampaignIn, current, validate

class MarketplaceAdsTests(unittest.TestCase):
    def setUp(self):
        self.con=sqlite3.connect(':memory:')
        self.con.row_factory=sqlite3.Row
        self.con.executescript(SCHEMA)

    def tearDown(self):
        self.con.close()

    def insert(self,id,slot,enabled,start,end,title='Reklama'):
        self.con.execute('INSERT INTO marketplace_ad_campaigns VALUES(?,?,?,?,?,?,?)',
                         (id,slot,title,'Treść',enabled,start,end))

    def test_only_active_campaign_in_correct_slot(self):
        self.insert('a','login',1,100,200)
        self.insert('b','buyer',1,100,200)
        self.insert('c','login',0,100,200)
        self.assertEqual(current(self.con,'login',now=150)['id'],'a')
        self.assertEqual(current(self.con,'buyer',now=150)['id'],'b')
        self.assertIsNone(current(self.con,'seller',now=150))
        self.assertIsNone(current(self.con,'login',now=200))
        self.assertIsNone(current(self.con,'login',now=99))

    def test_invalid_slot_is_not_accepted(self):
        with self.assertRaises(HTTPException) as err:current(self.con,'admin',now=150)
        self.assertEqual(err.exception.status_code,404)

    def test_multiline_campaign_description_is_accepted(self):
        payload=CampaignIn(slot='login',title='Promocja',body='Linia pierwsza'+chr(10)+'Linia druga',starts_at=100,ends_at=200)
        validate(payload)

    def test_invalid_content_and_date_rejected(self):
        for title,body,start,end in [('  ','Treść',100,200),('Tytuł','  ',100,200),
                                      ('A'+chr(0)+'B','Treść',100,200),('Tytuł','Treść',200,100)]:
            payload=CampaignIn(slot='login',title=title,body=body,starts_at=start,ends_at=end)
            with self.assertRaises(HTTPException):validate(payload)

if __name__=='__main__':unittest.main()
