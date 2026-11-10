"""Money in integer grosze only; half-up for positive monetary allocations."""
def split_75_20_5(grosze: int) -> tuple[int,int,int]:
    if type(grosze) is not int or grosze < 0:
        raise ValueError('Kwota musi być nieujemną liczbą całkowitą groszy')
    # Largest remainder: deterministic tie priority customer, farmer, platform.
    weights=(75,20,5)
    amounts=[grosze*w//100 for w in weights]
    remainder=grosze-sum(amounts)
    ranks=sorted(range(3),key=lambda i:(-((grosze*weights[i])%100),i))
    for i in ranks[:remainder]:
        amounts[i]+=1
    return tuple(amounts)

def full_refund(grosze:int)->int:
    if type(grosze) is not int or grosze<0:
        raise ValueError('Nieprawidłowa kwota')
    return grosze
