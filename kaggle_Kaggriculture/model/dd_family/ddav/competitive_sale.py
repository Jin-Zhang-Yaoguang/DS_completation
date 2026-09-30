"""One-turn cash-difference estimates under possible market order alignments."""
import rules

def sale(item,inventory,quantity,params):
    cash=0
    for _ in range(quantity):
        price=rules.market_price(item,inventory,params);cash+=price
        if price>1:inventory+=1
    return cash,inventory

def joint(item,inventory,own,other,params):
    ours=theirs=0
    for j in range(max(own,other)):
        price=rules.market_price(item,inventory,params)
        if j<own:ours+=price
        if j<other:theirs+=price
        if price>1:inventory+=int(j<own)+int(j<other)
    return ours,theirs

def gains(item,inventory,own,other,consume,params):
    # Holding lets the opponent sell first; all known town consumption occurs
    # after this turn's market. Our next-turn sale is an approximate continuation.
    opp_alone,after=sale(item,inventory,other,params)
    future,_=sale(item,after-consume,own,params)
    delayed=future-opp_alone
    simultaneous=joint(item,inventory,own,other,params)
    ours,after=sale(item,inventory,own,params);theirs,_=sale(item,after,other,params)
    their_first,after=sale(item,inventory,other,params);our_last,_=sale(item,after,own,params)
    return [delayed-(simultaneous[0]-simultaneous[1]),delayed-(ours-theirs),delayed-(our_last-their_first)]
