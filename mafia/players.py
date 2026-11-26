import random

class Bot:
    def __init__(self, rng, partner_protection=0.85):
        self.rng = rng
        self.partner_protection = partner_protection #saved on self so protectPartner can read it later

    def protectPartner(self, view, target):
        #takes the target the bot already picked, returns the FINAL target
        if not view.is_impostor: #innocents have no partner to protect
            return target

        if target != view.partner: #if the target is not my partner, I don't need to protect them, just return the target
            return target

        #from here: I'm an impostor and my target IS my partner
        if self.rng.random() < self.partner_protection: #true ~85% of the time -> protect
            others = [p for p in view.public.alive if p != view.id and p != view.partner]
            if others: #guard: if nobody else is alive, choice([]) would crash
                return self.rng.choice(others) #redirect to someone who is neither me nor my partner
        return target #the ~15% case (or no one else to vote for): vote for the partner anyway

    def accuse(self, view):
        #default: don't accuse anyone
        return None

class RandomBot(Bot):
    def vote(self, view):
        #pick someone at random from the living players to vote, never pick self
        candidates = [p for p in view.public.alive if p != view.id] #list comprehension, for each player in the alive list, if they are not me, add them to the candidates list
        target = self.rng.choice(candidates) #from our seeded random generator, pick one of the candidates at random
        return self.protectPartner(view, target) #let the base class maybe redirect it
    
    def accuse(self, view):
        if self.rng.random() < 0.5:
            candidates = [p for p in view.public.alive if p != view.id]
            return self.rng.choice(candidates)
        return None

class NaiveBot(Bot):
    def vote(self, view):
        #1. count how many times each living player was accused, ignore self
        #right now, acussations is a list of tuples (round, accuser, target), we have to turn the list into a dictionary key = player, value = times they were accused
        counts = {}
        accusation_count =  view.public.accusations
        for _, _, target in accusation_count: #break down tuples to get target only
            if target in view.public.alive and target != view.id: #if target is alive and not self count it
                if target in counts:
                    counts[target] +=1
                else:
                    counts[target] = 1
        #3.return whoever has the most accusations, if there is a tie, pick one at random
        #4.if no one has been accused, pick someone at random
        if not counts:
            candidates = [p for p in view.public.alive if p != view.id]
            return self.protectPartner(view, self.rng.choice(candidates))

        top = max(counts.values())
        leaders = [player for player, count in counts.items() if count == top] #list comprehension, loops over our dictionaries items which gives player,count pairs
        #If one player leads, leaders has one item. If there's a tie, it has several. Either way, self.rng.choice(leaders) picks one at random. When there's only one item, choice just returns it, so you don't need a separate tie case.
        return self.protectPartner(view, self.rng.choice(leaders))
    
    def accuse(self, view):
        return self.bote(view)
    
class BandwagonerBot(Bot):
#same as naive bot, but counts votes instead of accusations
    def vote(self, view):
        counts = {}
        last_round = view.public.round - 1
        for round_num, _, target in view.public.votes:
            if round_num != last_round:
                continue
            if target in view.public.alive and target != view.id:
                if target in counts:
                    counts[target] += 1
                else:
                    counts[target] = 1
        if not counts:
            candidates = [p for p in view.public.alive if p != view.id]
            return self.protectPartner(view, self.rng.choice(candidates))

        top = max(counts.values())
        leaders = [player for player, count in counts.items() if count == top]
        return self.protectPartner(view, self.rng.choice(leaders))

class GrudgeHolderBot(Bot):
    """Votes for whoever has accused ME the most."""
    def vote(self, view):
        counts = {}
        for _, accuser, target in view.public.accusations:
            if target != view.id:            # only accusations aimed at me
                continue
            if accuser in view.public.alive and accuser != view.id:
                if accuser in counts:
                    counts[accuser] += 1
                else:
                    counts[accuser] = 1

        if not counts:
            candidates = [p for p in view.public.alive if p != view.id]
            return self.protectPartner(view, self.rng.choice(candidates))

        top = max(counts.values())
        leaders = [player for player, count in counts.items() if count == top]
        return self.protectPartner(view, self.rng.choice(leaders))

    def accuse(self, view):
        return self.vote(view)

class QuietBot(Bot):
    """Votes at random; never accuses. accuse() is inherited -> None."""
    def vote(self, view):
        candidates = [p for p in view.public.alive if p != view.id]
        return self.protectPartner(view, self.rng.choice(candidates))
