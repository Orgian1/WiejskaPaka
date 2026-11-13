"""Small private account summary for badges; no product/contact data is returned."""
from fastapi import Depends,Header


def install(app,write_db,current_user):
    @app.get('/account/navigation-counts')
    def counts(user=Depends(current_user),authorization:str|None=Header(default=None)):
        with write_db(user,authorization,('klient','rolnik')) as con:
            favorites=con.execute('SELECT COUNT(*) AS n FROM account_favorites WHERE user_id=?',(user['id'],)).fetchone()['n']
            cart=con.execute('SELECT COUNT(*) AS n FROM saved_cart_items WHERE buyer_id=?',(user['id'],)).fetchone()['n'] if user['role']=='klient' else 0
            orders=con.execute("SELECT COUNT(*) AS n FROM orders WHERE farmer_id=? AND status IN ('oczekuje_na_platnosc_testowa','gotowe_do_odbioru_testowo','w_drodze_testowo')",(user['id'],)).fetchone()['n'] if user['role']=='rolnik' else 0
            return {'favorites_count':favorites,'cart_count':cart,'current_orders_count':orders}
