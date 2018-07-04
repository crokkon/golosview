from beem import Steem
from beem.account import Account
from beem.comment import Comment
from beem.amount import Amount
from beem.utils import parse_time, reputation_to_score
import config
import math
import traceback

class GVAccount(object):

    def __init__(self, username : str):
        self.steem = Steem(node=config.NODE)
        self.account = Account(username, steem_instance=self.steem)
        self.opcount = self.account.virtual_op_count()
        self.pages = math.ceil(self.opcount / config.OPS_PER_PAGE)

    def operations(self, page : int) -> list:
        ops = []
        start = self.opcount - (page - 1) * config.OPS_PER_PAGE
        stop = max(0, start - config.OPS_PER_PAGE)
        for op in self.account.history_reverse(start=start, stop=stop,
                                               use_block_num=False):
            ops.append(op)
        return ops

    def parse(self):
        acc_info = dict(self.account)
        acc_info['voting_power'] = "%.2f%%" % \
                                   (self.account.get_voting_power())
        acc_info['reputation'] = "%.1f" % \
                                 self.account.get_reputation()
        own_sp = self.account.get_steem_power(onlyOwnSP=True)
        acc_info['sp'] = "%.1f GOLOS" % (own_sp)

        avatar_url = "https://api.adorable.io/avatars/200/%s.png" % \
                     (acc_info['name'])
        try:
            profile = self.account.profile
            if 'profile_image' in profile:
                avatar_url = "https://imgp.golos.io/0x0/" + \
                             profile['profile_image']
        except:
            pass

        acc_info['avatar_url'] = avatar_url

        for key in ['created']:
            acc_info[key] = acc_info[key].strftime(config.DATE_FMT)
        return acc_info


class GVComment(object):

    def __init__(self, identifier : str):
        self.steem = Steem(node=config.NODE)
        self.comment = Comment(identifier, steem_instance=self.steem)

    def parse(self):
        comment_info = dict(self.comment)
        rep = comment_info['author_reputation']
        repstr = "%s (%.1f)" % (rep, reputation_to_score(rep))
        comment_info['author_reputation'] = repstr
        total_weight = int(comment_info['total_vote_weight'])
        for vote in comment_info['active_votes']:
            vote['time'] = vote['time'].strftime(config.DATE_FMT)
            vote['reputation'] = "%.1f" % \
                                 (reputation_to_score(vote['reputation']))
            vote['percent'] = "%.2f%%" % (int(vote['percent']) / 100)
            vote['rshares'] = "%.2f bn" % (int(vote['rshares']) / 1e9)
            weight = int(vote['weight'])
            vote['weight'] = "%.2f tn" % (weight/1e12)
            if total_weight:
                rel_weight = weight * 100 / total_weight
                vote['weight'] += " (%.2f%%)" % (rel_weight)

        for key in ['created']:
            comment_info[key] = comment_info[key].strftime(config.DATE_FMT)

        payout = Amount(comment_info['pending_payout_value']) + \
                 Amount(comment_info['total_payout_value']) + \
                 Amount(comment_info['curator_payout_value'])
        comment_info['payout'] = "%s" % (payout)

        return comment_info
