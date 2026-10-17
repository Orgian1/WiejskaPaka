"""Local checkout key management. Never prints key bytes; never connects a DB."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.checkout_vault import create_ring,rotate_ring


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('create','rotate'));p.add_argument('--path',type=Path,required=True)
    args=p.parse_args()
    if not args.path.is_absolute() or not args.path.name.endswith('.checkout-key'):
        p.error('Wymagana bezwzględna ścieżka poza projektem, z końcówką .checkout-key')
    root=Path(__file__).resolve().parents[1]
    if args.path.resolve().is_relative_to(root):p.error('Klucz musi znajdować się poza katalogiem projektu')
    if args.action=='create':kid,_=create_ring(args.path)
    else:kid=rotate_ring(args.path)
    print('Klucz przygotowany; identyfikator: '+kid+'. Po rotacji uruchom ponownie aplikację.')


if __name__=='__main__':main()
