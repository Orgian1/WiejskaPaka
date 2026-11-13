"""Stable catalog taxonomy; additive classification preserves all legacy product data."""
from fastapi import HTTPException

DEFINITIONS = [
 ('vegetables','Warzywa',[('potatoes','Ziemniaki'),('tomatoes','Pomidory'),('cucumbers','Ogórki'),('carrots','Marchew'),('onions','Cebula'),('cabbage','Kapusta')]),
 ('fruit','Owoce',[('apples','Jabłka'),('pears','Gruszki'),('plums','Śliwki'),('strawberries','Truskawki'),('raspberries','Maliny'),('blueberries','Borówki')]),
 ('honey','Miody',[('multifloral','Wielokwiatowy'),('linden','Lipowy'),('rapeseed','Rzepakowy'),('buckwheat','Gryczany'),('honeydew','Spadziowy')]),
 ('preserves','Przetwory',[('jams','Dżemy'),('confitures','Konfitury'),('fermented','Kiszonki'),('pickled','Marynaty'),('sauces','Sosy')]),
 ('dairy','Nabiał',[('milk','Mleko'),('cheese','Sery'),('curd','Twarogi'),('yogurt','Jogurty'),('butter','Masło')]),
 ('meat','Mięso',[('pork','Wieprzowina'),('beef','Wołowina'),('poultry','Drób'),('sausages','Wędliny')]),
 ('eggs','Jaja',[('chicken','Kurze'),('quail','Przepiórcze'),('duck','Kacze')]),
 ('bakery','Pieczywo',[('bread','Chleb'),('rolls','Bułki'),('cakes','Ciasta')]),
 ('fish','Ryby',[('fresh','Świeże'),('smoked','Wędzone'),('preserved','Przetwory rybne')]),
 ('grains','Zboża i mąki',[('grains','Zboża'),('flour','Mąki'),('groats','Kasze'),('flakes','Płatki')]),
 ('herbs','Zioła i przyprawy',[('fresh','Świeże zioła'),('dried','Suszone zioła'),('spices','Przyprawy')]),
 ('mushrooms','Grzyby',[('fresh','Świeże'),('dried','Suszone'),('preserved','Przetwory grzybowe')]),
 ('nuts-seeds','Orzechy i nasiona',[('nuts','Orzechy'),('kernels','Pestki'),('seeds','Nasiona')]),
 ('drinks','Soki i napoje',[('juice','Soki'),('syrup','Syropy'),('soft-drinks','Napoje bezalkoholowe')]),
 ('plants','Sadzonki i rośliny',[('vegetables','Sadzonki warzyw'),('fruit','Sadzonki owocowe'),('potted-herbs','Zioła w doniczkach'),('flowers','Kwiaty')]),
 ('other','Pozostałe',[]),
]
CATEGORIES=[{'id':cid,'label':label,'subcategories':[{'id':cid+'-'+sid,'label':text} for sid,text in subs]+[{'id':cid+'-other','label':'Produkty niesklasyfikowane' if cid=='other' else 'Inne'}]} for cid,label,subs in DEFINITIONS]
PAIRS={(c['id'],s['id']) for c in CATEGORIES for s in c['subcategories']}
# Whole names only. Never infer from fragments, mixed offers or marketing text.
EXACT_NAMES={}
for category in CATEGORIES[:2]:
 for sub in category['subcategories']:
  if not sub['id'].endswith('-other'):EXACT_NAMES[sub['label'].lower()]=(category['id'],sub['id'])
EXACT_NAMES.update({'mleko':('dairy','dairy-milk'),'masło':('dairy','dairy-butter'),'chleb':('bakery','bakery-bread'),
 'miód lipowy':('honey','honey-linden'),'miód wielokwiatowy':('honey','honey-multifloral'),'miód gryczany':('honey','honey-buckwheat')})

SAFE_ALIASES={
 'vegetables-potatoes':['ziemniak','ziemniaki demonstracyjne'],'vegetables-tomatoes':['pomidor'],'vegetables-cucumbers':['ogórek'],'vegetables-carrots':['marchewka','marchew demonstracyjna'],
 'fruit-apples':['jabłko'],'fruit-pears':['gruszka'],'fruit-plums':['śliwka'],'fruit-strawberries':['truskawka'],'fruit-raspberries':['malina'],'fruit-blueberries':['borówka'],
 'honey-rapeseed':['miód rzepakowy'],'honey-honeydew':['miód spadziowy'],
 'preserves-jams':['dżem','dżemy'],'preserves-confitures':['konfitury'],'preserves-fermented':['kiszonki'],'preserves-pickled':['marynaty'],'preserves-sauces':['sosy'],
 'dairy-cheese':['ser','sery'],'dairy-curd':['twaróg','twarogi'],'dairy-yogurt':['jogurt','jogurty'],
 'meat-pork':['wieprzowina'],'meat-beef':['wołowina'],'meat-poultry':['drób'],'meat-sausages':['wędliny'],
 'eggs-chicken':['jaja kurze'],'eggs-quail':['jaja przepiórcze'],'eggs-duck':['jaja kacze'],
 'bakery-rolls':['bułki'],'bakery-cakes':['ciasta'],
 'fish-fresh':['ryby świeże'],'fish-smoked':['ryby wędzone'],'fish-preserved':['przetwory rybne'],
 'grains-grains':['zboża'],'grains-flour':['mąka','mąki'],'grains-groats':['kasze'],'grains-flakes':['płatki owsiane'],
 'herbs-fresh':['świeże zioła'],'herbs-dried':['suszone zioła'],'herbs-spices':['przyprawy'],
 'mushrooms-fresh':['grzyby świeże'],'mushrooms-dried':['grzyby suszone'],'mushrooms-preserved':['przetwory grzybowe'],
 'nuts-seeds-nuts':['orzechy włoskie','orzechy laskowe'],'nuts-seeds-kernels':['pestki dyni'],'nuts-seeds-seeds':['nasiona chia'],
 'drinks-juice':['soki'],'drinks-syrup':['syropy'],'drinks-soft-drinks':['napoje bezalkoholowe'],
 'plants-vegetables':['sadzonki warzyw'],'plants-fruit':['sadzonki owocowe'],'plants-potted-herbs':['zioła w doniczkach'],'plants-flowers':['kwiaty'],
}
for category in CATEGORIES:
    for sub in category['subcategories']:
        for name in SAFE_ALIASES.get(sub['id'],[]):EXACT_NAMES[name]=(category['id'],sub['id'])


def validate_pair(category,subcategory):
    if (category,subcategory) not in PAIRS:raise HTTPException(422,'Wybierz podkategorię należącą do wybranej kategorii')


def inferred(name):return EXACT_NAMES.get(name.strip().lower(),('other','other-other'))


def schema_sql(postgres=False):
    number='BIGINT' if postgres else 'INTEGER'
    statements=[f'''CREATE TABLE IF NOT EXISTS product_categories(id TEXT PRIMARY KEY,label TEXT NOT NULL,position INTEGER NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS product_subcategories(id TEXT PRIMARY KEY,category_id TEXT NOT NULL REFERENCES product_categories(id),label TEXT NOT NULL,position INTEGER NOT NULL,UNIQUE(id,category_id));
CREATE TABLE IF NOT EXISTS product_classifications(product_id {number} PRIMARY KEY REFERENCES products(id),category_id TEXT NOT NULL REFERENCES product_categories(id),subcategory_id TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',FOREIGN KEY(subcategory_id,category_id) REFERENCES product_subcategories(id,category_id));
CREATE INDEX IF NOT EXISTS product_classification_category ON product_classifications(category_id,subcategory_id,product_id);''']
    def quote(s):return "'"+s.replace("'","''")+"'"
    for i,c in enumerate(CATEGORIES):
        statements.append(f"INSERT INTO product_categories VALUES({quote(c['id'])},{quote(c['label'])},{i}) ON CONFLICT(id) DO NOTHING;")
        for j,s in enumerate(c['subcategories']):statements.append(f"INSERT INTO product_subcategories VALUES({quote(s['id'])},{quote(c['id'])},{quote(s['label'])},{j}) ON CONFLICT(id) DO NOTHING;")
    cases=lambda pos:'CASE LOWER(TRIM(name)) '+''.join('WHEN '+quote(name)+' THEN '+quote(pair[pos])+' ' for name,pair in EXACT_NAMES.items())+'ELSE '+quote(('other','other-other')[pos])+' END'
    statements.append('INSERT INTO product_classifications(product_id,category_id,subcategory_id) SELECT id,'+cases(0)+','+cases(1)+' FROM products WHERE id NOT IN (SELECT product_id FROM product_classifications);')
    return '\n'.join(statements)


def save(con,pid,category,subcategory,description=''):
    validate_pair(category,subcategory)
    con.execute('''INSERT INTO product_classifications(product_id,category_id,subcategory_id,description) VALUES(?,?,?,?)
      ON CONFLICT(product_id) DO UPDATE SET category_id=excluded.category_id,subcategory_id=excluded.subcategory_id,description=excluded.description''',(pid,category,subcategory,description))


def metadata(con,pid):
    row=con.execute('SELECT category_id,subcategory_id,description FROM product_classifications WHERE product_id=?',(pid,)).fetchone()
    return dict(row) if row else {'category_id':'other','subcategory_id':'other-other','description':''}
